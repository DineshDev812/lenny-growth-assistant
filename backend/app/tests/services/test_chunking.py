import random

from app.services.chunking import chunk_turns, estimate_tokens
from app.services.transcript_parser import Turn


def _words(rng: random.Random, count: int) -> str:
    return " ".join(f"w{rng.randint(1, 9999)}" for _ in range(count))


def _sentences(rng: random.Random, count: int) -> str:
    parts: list[str] = []
    remaining = count
    while remaining > 0:
        size = min(remaining, rng.randint(5, 25))
        parts.append(_words(rng, size) + ".")
        remaining -= size
    return " ".join(parts)


def _long_dialogue(seed: int = 7, turns: int = 120) -> list[Turn]:
    rng = random.Random(seed)
    return [
        Turn("Alice Smith" if i % 2 else "Bob", i * 30, _sentences(rng, rng.randint(3, 700)))
        for i in range(turns)
    ]


def test_empty_input_gives_no_chunks() -> None:
    assert chunk_turns([]) == []
    assert chunk_turns([Turn("A", 0, "   ")]) == []


def test_short_dialogue_is_one_chunk_with_first_timestamp() -> None:
    chunks = chunk_turns([Turn("Lenny", 5, "Hello there."), Turn("Guest", 20, "Hi Lenny.")])
    assert len(chunks) == 1
    assert chunks[0].start_seconds == 5
    assert chunks[0].speaker == "Lenny"
    assert "Lenny: Hello there." in chunks[0].text
    assert "Guest: Hi Lenny." in chunks[0].text


def test_chunks_respect_size_bounds() -> None:
    chunks = chunk_turns(_long_dialogue())
    assert len(chunks) > 10
    assert max(chunk.token_count for chunk in chunks) <= 500
    # all but the last chunk should be reasonably full (about 400-500 tokens)
    assert min(chunk.token_count for chunk in chunks[:-1]) >= 380


def test_chunk_indexes_are_sequential_and_starts_never_go_backwards() -> None:
    chunks = chunk_turns(_long_dialogue(seed=3))
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    starts = [chunk.start_seconds for chunk in chunks]
    assert all(start is not None for start in starts)
    assert starts == sorted(starts)  # type: ignore[type-var]


def test_consecutive_chunks_overlap() -> None:
    chunks = chunk_turns(_long_dialogue(seed=11))
    for previous, current in zip(chunks, chunks[1:]):
        first_piece = current.text.split("\n\n")[0].split(": ", 1)[-1]
        assert first_piece[:40] in previous.text


def test_overlap_can_be_disabled() -> None:
    chunks = chunk_turns(_long_dialogue(seed=5), overlap_tokens=0)
    for previous, current in zip(chunks, chunks[1:]):
        first_piece = current.text.split("\n\n")[0].split(": ", 1)[-1]
        assert first_piece[:40] not in previous.text


def test_single_huge_turn_is_split_and_keeps_its_timestamp() -> None:
    rng = random.Random(1)
    chunks = chunk_turns([Turn("Guest", 125, _sentences(rng, 3000))])
    assert len(chunks) > 3
    assert all(chunk.start_seconds == 125 for chunk in chunks)
    assert max(chunk.token_count for chunk in chunks) <= 500


def test_one_giant_sentence_without_punctuation_is_still_split() -> None:
    rng = random.Random(2)
    chunks = chunk_turns([Turn(None, None, _words(rng, 2500))])
    assert len(chunks) > 3
    assert max(chunk.token_count for chunk in chunks) <= 500


def test_estimate_tokens() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("one two three") >= 3
