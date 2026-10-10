"""Quick retrieval sanity check against the REAL ingested data.

Run inside the backend container after ingestion has finished:

    docker compose exec backend python -m tests.eval.retrieval_check

Prints the top episode (plus score and a deep link) for about ten growth questions, and one
nonsense control query that should return nothing. Read the output and judge relevance yourself;
use the printed scores to tune RETRIEVAL_MIN_SCORE if needed.
"""

from __future__ import annotations

import asyncio
import sys
import textwrap

from app.db.session import SessionLocal, engine
from app.services.retrieval import RetrievalService

QUESTIONS: list[str] = [
    "How do you measure product-market fit?",
    "What is a good activation rate for onboarding new users?",
    "How should startups think about pricing and packaging?",
    "How do you improve user retention?",
    "What is a growth loop and how do you build one?",
    "How do you hire your first product manager?",
    "How do you run effective growth experiments?",
    "What makes a great product strategy?",
    "How do you decide what to build next on a roadmap?",
    "How should founders think about fundraising?",
]
CONTROL_NONSENSE = "xqzvbn flurbo glorptastic"


async def main() -> int:
    answered = 0
    async with SessionLocal() as db:
        service = RetrievalService(db)
        for question in [*QUESTIONS, CONTROL_NONSENSE]:
            results = await service.retrieve(question, k=6)
            print(f"\nQ: {question}")
            if not results:
                print("   -> no results")
                continue
            if question != CONTROL_NONSENSE:
                answered += 1
            top = results[0]
            print(f"   -> {top.episode_title}  [{top.guest}]  score={top.score:.3f}  at {top.start_timestamp}")
            print(f"      {top.youtube_deep_link or top.youtube_url or '(no link)'}")
            print(textwrap.indent(textwrap.shorten(top.text, width=220, placeholder=" ..."), "      "))
            others = sorted({r.episode_title for r in results[1:] if r.episode_title != top.episode_title})
            if others:
                print(f"      also: {'; '.join(others[:3])}")
    await engine.dispose()
    print(f"\n{answered}/{len(QUESTIONS)} questions returned results.")
    return 0 if answered else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
