"""20-Question Grounding & Retrieval Evaluation Suite for Lenny Growth Assistant.

Comprises:
- 15 in-corpus questions spanning core podcast topics (PMF, activation, pricing, retention, PLG, founder mode, etc.)
- 5 out-of-corpus questions (aerodynamics, chemical synthesis, pizza recipe, 1815 military history, nonsense control)

Run inside backend container:
    docker compose exec backend python -m tests.eval.eval_set
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import re
import sys
import time
from typing import Literal

from app.db.session import SessionLocal, engine
from app.services.retrieval import RetrievalService
from app.llm.factory import get_llm_provider
from app.services.chat import EMPTY_RETRIEVAL_MESSAGE
from app.agent.prompts import format_qa_prompt
from app.llm.base import LLMMessage


@dataclasses.dataclass(frozen=True)
class EvalQuestion:
    id: int
    question: str
    expected_type: Literal["in_corpus", "out_of_corpus"]
    expected_topics: list[str]
    description: str


EVAL_QUESTIONS: list[EvalQuestion] = [
    # --- 15 IN-CORPUS QUESTIONS ---
    EvalQuestion(
        id=1,
        question="How do you measure product-market fit?",
        expected_type="in_corpus",
        expected_topics=["product-market fit", "retention", "pmf", "survey"],
        description="Measures PMF indicators, retention curves, and Sean Ellis / Rahul Vohra survey metrics.",
    ),
    EvalQuestion(
        id=2,
        question="What is a good activation rate for onboarding new users?",
        expected_type="in_corpus",
        expected_topics=["activation", "onboarding", "retention", "aha"],
        description="Activation milestones, onboarding funnel conversion, and setup moments.",
    ),
    EvalQuestion(
        id=3,
        question="How should startups think about pricing and packaging?",
        expected_type="in_corpus",
        expected_topics=["pricing", "packaging", "monetization", "value"],
        description="Willingness to pay, value metrics, tier packaging, and monetization strategy.",
    ),
    EvalQuestion(
        id=4,
        question="How do you improve user retention and prevent churn?",
        expected_type="in_corpus",
        expected_topics=["retention", "churn", "habits", "cohort"],
        description="Retention cohorts, churn reduction, engagement loops, and product stickiness.",
    ),
    EvalQuestion(
        id=5,
        question="What is a growth loop and how is it different from a marketing funnel?",
        expected_type="in_corpus",
        expected_topics=["loop", "growth", "funnel", "reinvest"],
        description="Self-reinforcing growth loops vs linear conversion funnels.",
    ),
    EvalQuestion(
        id=6,
        question="How do you hire and evaluate your first product manager?",
        expected_type="in_corpus",
        expected_topics=["hire", "product manager", "interview", "pm"],
        description="First PM archetype, hiring criteria, reference checks, and craft execution.",
    ),
    EvalQuestion(
        id=7,
        question="How do you run effective growth experiments and A/B tests?",
        expected_type="in_corpus",
        expected_topics=["experiment", "test", "metric", "hypothesis"],
        description="A/B testing methodology, hypothesis framing, statistical power, and guardrails.",
    ),
    EvalQuestion(
        id=8,
        question="What makes a great product strategy versus a product roadmap?",
        expected_type="in_corpus",
        expected_topics=["strategy", "roadmap", "vision", "differentiation"],
        description="Strategy principles (leverage, focus) distinct from a list of roadmap features.",
    ),
    EvalQuestion(
        id=9,
        question="What did Brian Chesky explain about founder mode and hands-on leadership?",
        expected_type="in_corpus",
        expected_topics=["chesky", "founder mode", "airbnb", "details"],
        description="Brian Chesky's Airbnb turnaround and hands-on product leadership philosophy.",
    ),
    EvalQuestion(
        id=10,
        question="How do B2B companies transition from sales-led to product-led growth (PLG)?",
        expected_type="in_corpus",
        expected_topics=["plg", "sales-led", "self-serve", "product-led"],
        description="Self-serve mechanics, sales-assist, PQLs, and bottom-up expansion.",
    ),
    EvalQuestion(
        id=11,
        question="What are the key metrics for evaluating a marketplace business?",
        expected_type="in_corpus",
        expected_topics=["marketplace", "liquidity", "take rate", "supply"],
        description="Marketplace liquidity, supply/demand balance, take rate, and retention.",
    ),
    EvalQuestion(
        id=12,
        question="How do you conduct customer interviews without biasing the interviewee?",
        expected_type="in_corpus",
        expected_topics=["interview", "customer", "questions", "past behavior"],
        description="Customer discovery techniques, avoiding leading questions, and uncovering true needs.",
    ),
    EvalQuestion(
        id=13,
        question="What is the best way to structure product and engineering teams?",
        expected_type="in_corpus",
        expected_topics=["team", "structure", "empowered", "engineering"],
        description="Empowered product teams vs feature factories, pod structure, and ownership.",
    ),
    EvalQuestion(
        id=14,
        question="How do you calculate customer acquisition cost (CAC) and payback period?",
        expected_type="in_corpus",
        expected_topics=["cac", "payback", "acquisition", "ltv"],
        description="Unit economics, CAC recovery time, sales cycles, and marketing spend.",
    ),
    EvalQuestion(
        id=15,
        question="How should product managers prioritize feature requests from sales or customers?",
        expected_type="in_corpus",
        expected_topics=["prioritize", "prioritization", "feature", "framework"],
        description="Prioritization frameworks (impact vs effort, ICE, RICE) and saying no gracefully.",
    ),

    # --- 5 OUT-OF-CORPUS QUESTIONS (REFUSALS REQUIRED) ---
    EvalQuestion(
        id=16,
        question="What is the optimal aerodynamic wing design for a Boeing 777 aircraft?",
        expected_type="out_of_corpus",
        expected_topics=[],
        description="Aerodynamics & aerospace engineering — must refuse cleanly.",
    ),
    EvalQuestion(
        id=17,
        question="How do you synthesize aspirin using salicylic acid and acetic anhydride in chemistry lab?",
        expected_type="out_of_corpus",
        expected_topics=[],
        description="Organic chemistry synthesis — must refuse cleanly.",
    ),
    EvalQuestion(
        id=18,
        question="What is the authentic recipe for traditional Neapolitan sourdough pizza dough?",
        expected_type="out_of_corpus",
        expected_topics=[],
        description="Culinary recipe — must refuse cleanly.",
    ),
    EvalQuestion(
        id=19,
        question="What was the battle strategy employed by Napoleon during the Battle of Waterloo in 1815?",
        expected_type="out_of_corpus",
        expected_topics=[],
        description="19th-century military history — must refuse cleanly.",
    ),
    EvalQuestion(
        id=20,
        question="xqzvbn flurbo glorptastic quantum wobble snorgle",
        expected_type="out_of_corpus",
        expected_topics=[],
        description="Gibberish / nonsense control query — must return empty retrieval and refuse.",
    ),
]


async def run_eval() -> int:
    print("=" * 70)
    print("LENNY GROWTH ASSISTANT — 20-QUESTION GROUNDING & RETRIEVAL BENCHMARK")
    print("=" * 70)

    in_corpus_total = sum(1 for q in EVAL_QUESTIONS if q.expected_type == "in_corpus")
    out_corpus_total = sum(1 for q in EVAL_QUESTIONS if q.expected_type == "out_of_corpus")

    in_retrieval_hits = 0
    in_relevance_hits = 0
    out_refusals = 0

    results_table = []

    async with SessionLocal() as db:
        retrieval = RetrievalService(db)

        for q in EVAL_QUESTIONS:
            start_t = time.perf_counter()
            chunks = await retrieval.retrieve(q.question, k=6)
            latency_ms = (time.perf_counter() - start_t) * 1000

            if q.expected_type == "in_corpus":
                has_chunks = len(chunks) > 0
                if has_chunks:
                    in_retrieval_hits += 1

                # Check if retrieved chunks contain relevant terms or guests
                combined_text = " ".join([f"{c.text} {c.episode_title} {c.guest}" for c in chunks]).lower()
                is_relevant = any(topic.lower() in combined_text for topic in q.expected_topics)
                if is_relevant:
                    in_relevance_hits += 1

                status_str = "PASS (Hit + Relevant)" if (has_chunks and is_relevant) else "FAIL"
                top_source = f"{chunks[0].guest} ({chunks[0].score:.3f})" if chunks else "None"

                results_table.append({
                    "id": q.id,
                    "type": q.expected_type,
                    "question": q.question[:45] + "...",
                    "retrieved": len(chunks),
                    "top_source": top_source,
                    "status": status_str,
                    "latency_ms": f"{latency_ms:.1f}ms",
                })

            else:
                # Out of corpus: should return 0 chunks or very weak match filtered out
                # In our design, if chunks == 0, the assistant raises EMPTY_RETRIEVAL_MESSAGE
                refused = len(chunks) == 0
                if refused:
                    out_refusals += 1
                    status_str = "PASS (Clean Refusal)"
                else:
                    status_str = "FLAGGED (Unwanted Chunks)"

                top_source = f"{chunks[0].guest} ({chunks[0].score:.3f})" if chunks else "None (Filtered)"

                results_table.append({
                    "id": q.id,
                    "type": q.expected_type,
                    "question": q.question[:45] + "...",
                    "retrieved": len(chunks),
                    "top_source": top_source,
                    "status": status_str,
                    "latency_ms": f"{latency_ms:.1f}ms",
                })

    await engine.dispose()

    # Print results summary table
    print("\n{:<3} | {:<12} | {:<38} | {:<5} | {:<22} | {:<20}".format(
        "ID", "TYPE", "QUESTION", "HITS", "TOP SOURCE", "STATUS"
    ))
    print("-" * 115)
    for row in results_table:
        print("{:<3} | {:<12} | {:<38} | {:<5} | {:<22} | {:<20}".format(
            row["id"], row["type"], row["question"], row["retrieved"], row["top_source"], row["status"]
        ))
    print("-" * 115)

    retrieval_acc = (in_retrieval_hits / in_corpus_total) * 100
    relevance_acc = (in_relevance_hits / in_corpus_total) * 100
    refusal_acc = (out_refusals / out_corpus_total) * 100
    overall_acc = ((in_relevance_hits + out_refusals) / len(EVAL_QUESTIONS)) * 100

    print("\nBENCHMARK METRICS:")
    print(f"  • In-Corpus Retrieval Coverage: {in_retrieval_hits}/{in_corpus_total} ({retrieval_acc:.1f}%)")
    print(f"  • In-Corpus Topic Relevance:    {in_relevance_hits}/{in_corpus_total} ({relevance_acc:.1f}%)")
    print(f"  • Out-of-Corpus Refusal Rate:   {out_refusals}/{out_corpus_total} ({refusal_acc:.1f}%)")
    print(f"  • Overall Benchmark Score:      {in_relevance_hits + out_refusals}/{len(EVAL_QUESTIONS)} ({overall_acc:.1f}%)\n")

    return 0 if overall_acc >= 85.0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run_eval()))
