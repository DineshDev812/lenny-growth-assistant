from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx

from app.core.cookies import sign_client_id

logging.basicConfig(level=logging.WARNING)

EMPTY_RETRIEVAL_PHRASE = "don't support an answer"
EVAL_DIR = Path(__file__).resolve().parent
QUESTIONS_FILE = EVAL_DIR / "qa_questions.json"
RESULTS_FILE = EVAL_DIR / "results.json"


def percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = int(math.ceil(p / 100.0 * len(sorted_data))) - 1
    return round(sorted_data[max(0, min(idx, len(sorted_data) - 1))], 2)


async def run_evaluation(base_url: str = "http://localhost:8000") -> dict[str, object]:
    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        questions = json.load(f)

    results: list[dict[str, object]] = []
    latencies: list[float] = []

    answerable_count = 0
    answered_count = 0
    unanswerable_count = 0
    abstained_count = 0
    grounded_abstain_count = 0
    general_fallback_count = 0
    answer_kind_total = 0
    valid_citation_answers = 0
    total_distinct_episodes = 0

    print("=" * 115)
    print(f"{'ID':<3} | {'Type':<12} | {'Topic':<15} | {'Outcome':<18} | {'Citations':<10} | {'Lat (ms)':<9} | {'Question'}")
    print("-" * 115)

    for item in questions:
        qid = item["id"]
        q_type = item["type"]
        topic = item["topic"]
        expected_abstain = item["expected_abstain"]
        question_text = item["question"]
        context_q = item.get("context_question")

        # Use a fresh client_id per evaluation session to avoid rate limits and isolate state
        client_uuid = uuid4()
        client_cookie = sign_client_id(client_uuid)
        cookies = {"client_id": client_cookie}

        async with httpx.AsyncClient(base_url=base_url, cookies=cookies, timeout=120.0) as client:
            # 1. Create a fresh session
            sess_res = await client.post("/api/sessions", json={"title": f"Eval {qid}"})
            if sess_res.status_code != 201:
                print(f"Error creating session for Q{qid}: HTTP {sess_res.status_code}")
                continue
            session_id = sess_res.json()["id"]

            t0 = time.perf_counter()
            try:
                # 2. If follow-up, send prior context turn first
                if context_q:
                    await client.post(
                        f"/api/sessions/{session_id}/messages",
                        json={"content": context_q},
                        timeout=180.0,
                    )

                # 3. Send evaluated question and measure latency
                msg_res = await client.post(
                    f"/api/sessions/{session_id}/messages",
                    json={"content": question_text},
                    timeout=180.0,
                )
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                latencies.append(elapsed_ms)

                if msg_res.status_code != 201:
                    print(f"{qid:<3} | {q_type:<12} | {topic:<15} | HTTP {msg_res.status_code:<5} | N/A        | {elapsed_ms:<9.1f} | {question_text[:40]}")
                    continue

                data = msg_res.json()
                assistant_msg = data.get("assistant_message", {})
                content = assistant_msg.get("content", "")
                sources = assistant_msg.get("sources", [])
                kind = assistant_msg.get("kind", "answer")
            except Exception as exc:
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                latencies.append(elapsed_ms)
                print(f"{qid:<3} | {q_type:<12} | {topic:<15} | TIMEOUT    | N/A        | {elapsed_ms:<9.1f} | {question_text[:40]}")
                continue

            # Analysis
            is_empty_refusal = EMPTY_RETRIEVAL_PHRASE in content.lower()
            is_abstain = (kind == "abstain") or is_empty_refusal
            is_general = (kind == "general")
            is_answer = (kind == "answer")

            cited_nums = set(re.findall(r"\[[sS](\d+)\]", content))
            source_nums = {str(s.get("id", "")).upper().lstrip("S") for s in sources}
            has_valid_citations = bool(cited_nums) and cited_nums.issubset(source_nums)

            distinct_episodes = len({s.get("episode_id") for s in sources}) if is_answer else 0

            # Citation validity must ONLY be computed over kind "answer"
            if is_answer:
                answer_kind_total += 1
                if has_valid_citations and cited_nums:
                    valid_citation_answers += 1

            if expected_abstain:
                unanswerable_count += 1
                # For "unanswerable" questions, count PASS if message kind is "abstain" OR "general" with zero sources/citations
                if is_abstain and len(sources) == 0 and len(cited_nums) == 0:
                    abstained_count += 1
                    grounded_abstain_count += 1
                    outcome = "ABSTAIN (PASS)"
                elif is_general and len(sources) == 0 and len(cited_nums) == 0:
                    abstained_count += 1
                    general_fallback_count += 1
                    outcome = "GEN FALLBACK (PASS)"
                else:
                    outcome = "UNEXPECTED (FAIL)"
            else:
                answerable_count += 1
                # For answerable questions count only kind "answer" with >=1 valid citation as a pass
                if is_answer and has_valid_citations and len(cited_nums) >= 1:
                    answered_count += 1
                    total_distinct_episodes += distinct_episodes
                    outcome = "ANSWERED (PASS)"
                elif is_abstain:
                    outcome = "ABSTAIN (FAIL)"
                else:
                    outcome = f"{kind.upper()} (FAIL)"

            cit_summary = f"{len(cited_nums)} cited" if is_answer else "0 cited"

            short_q = (question_text[:40] + "...") if len(question_text) > 40 else question_text
            print(f"{qid:<3} | {q_type:<12} | {topic:<15} | {outcome:<18} | {cit_summary:<10} | {elapsed_ms:<9.1f} | {short_q}")

            results.append({
                "id": qid,
                "type": q_type,
                "topic": topic,
                "question": question_text,
                "context_question": context_q,
                "expected_abstain": expected_abstain,
                "kind": kind,
                "is_abstain": is_abstain,
                "citations_count": len(cited_nums),
                "citations_valid": has_valid_citations if is_answer else True,
                "distinct_episodes": distinct_episodes,
                "latency_ms": elapsed_ms,
                "response_snippet": content[:200],
            })

    # Summary Metrics
    answer_rate = round((answered_count / answerable_count) * 100, 1) if answerable_count else 0.0
    abstain_precision = round((abstained_count / unanswerable_count) * 100, 1) if unanswerable_count else 0.0
    citation_validity = round((valid_citation_answers / answer_kind_total) * 100, 1) if answer_kind_total else 0.0
    avg_coverage = round(total_distinct_episodes / answered_count, 2) if answered_count else 0.0
    p50_latency = percentile(latencies, 50)
    p90_latency = percentile(latencies, 90)

    print("=" * 115)
    print("EVALUATION SUMMARY:")
    print(f"  • Total Questions:       {len(questions)}")
    print(f"  • Answer Rate:           {answer_rate}% ({answered_count}/{answerable_count} answered)")
    print(f"  • Abstain Precision:     {abstain_precision}% ({abstained_count}/{unanswerable_count} passed)")
    print(f"    - Grounded Abstain:    {grounded_abstain_count}")
    print(f"    - General Fallback:    {general_fallback_count}")
    print(f"  • Citation Validity:     {citation_validity}% ({valid_citation_answers}/{answer_kind_total} validated over kind='answer')")
    print(f"  • Source Coverage:       {avg_coverage} episodes / answer")
    print(f"  • Latency P50:           {p50_latency} ms")
    print(f"  • Latency P90:           {p90_latency} ms")
    print("=" * 115)

    summary = {
        "total_questions": len(questions),
        "answerable_count": answerable_count,
        "answered_count": answered_count,
        "answer_rate_pct": answer_rate,
        "unanswerable_count": unanswerable_count,
        "abstained_count": abstained_count,
        "grounded_abstain_count": grounded_abstain_count,
        "general_fallback_count": general_fallback_count,
        "abstain_precision_pct": abstain_precision,
        "answer_kind_total": answer_kind_total,
        "valid_citation_answers": valid_citation_answers,
        "citation_validity_pct": citation_validity,
        "avg_source_coverage": avg_coverage,
        "latency_p50_ms": p50_latency,
        "latency_p90_ms": p90_latency,
        "details": results,
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Results saved to {RESULTS_FILE}")
    return summary


def main() -> int:
    summary = asyncio.run(run_evaluation())
    if summary["answer_rate_pct"] >= 45.0 and summary["abstain_precision_pct"] >= 75.0:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
