from datetime import date

from app.services.transcript_parser import (
    format_timestamp,
    parse_transcript,
    parse_turns,
    slug_to_name,
    split_frontmatter,
    timestamp_to_seconds,
)

FULL = """---
guest: Jane Doe
title: "Growth: the loops"
youtube_url: https://www.youtube.com/watch?v=abc123
video_id: abc123
publish_date: 2023-05-01
description: A chat about loops.
keywords: [loops, growth]
---

Lenny (00:00:05): Welcome.

Jane Doe (00:01:10): Thanks for having me.
We continue on a second line.
"""


def test_full_frontmatter_is_parsed() -> None:
    parsed = parse_transcript(FULL, "jane-doe")
    assert parsed.guest == "Jane Doe"
    assert parsed.title == "Growth: the loops"
    assert parsed.youtube_url == "https://www.youtube.com/watch?v=abc123"
    assert parsed.video_id == "abc123"
    assert parsed.publish_date == date(2023, 5, 1)
    assert parsed.description == "A chat about loops."
    assert parsed.keywords == ["loops", "growth"]
    assert parsed.warnings == []


def test_turns_have_speaker_seconds_and_joined_lines() -> None:
    parsed = parse_transcript(FULL, "jane-doe")
    assert [(t.speaker, t.start_seconds) for t in parsed.turns] == [("Lenny", 5), ("Jane Doe", 70)]
    assert parsed.turns[1].text == "Thanks for having me. We continue on a second line."


def test_only_guest_and_keywords_uses_fallbacks() -> None:
    raw = "---\nguest: Tess Teaser\nkeywords: [hiring]\n---\nTess Teaser (00:00:03): Hello.\n"
    parsed = parse_transcript(raw, "tess-teaser")
    assert parsed.guest == "Tess Teaser"
    assert parsed.title == "Tess Teaser"
    assert parsed.youtube_url is None
    assert parsed.publish_date is None
    assert parsed.keywords == ["hiring"]
    assert len(parsed.turns) == 1
    assert any("title" in warning for warning in parsed.warnings)


def test_missing_frontmatter_derives_guest_from_slug() -> None:
    raw = "Nora Nofront (00:00:00): Hi there.\n\nLenny (01:05:30): Question?\n"
    parsed = parse_transcript(raw, "nora-nofront")
    assert parsed.guest == "Nora Nofront"
    assert parsed.title == "Nora Nofront"
    assert [t.start_seconds for t in parsed.turns] == [0, 3930]
    assert any("frontmatter" in warning for warning in parsed.warnings)


def test_invalid_yaml_falls_back_to_line_parsing() -> None:
    raw = '---\nguest: Bad Yaml\ntitle: "unclosed quote\nkeywords: [a, b\n---\nBad Yaml (00:00:01): Hi.\n'
    parsed = parse_transcript(raw, "bad-yaml")
    assert parsed.guest == "Bad Yaml"
    assert len(parsed.turns) == 1
    assert any("YAML" in warning for warning in parsed.warnings)


def test_youtube_url_is_built_from_video_id_when_missing() -> None:
    raw = "---\nguest: A\nvideo_id: xyz789\n---\nA (00:00:01): Hi.\n"
    assert parse_transcript(raw, "a").youtube_url == "https://www.youtube.com/watch?v=xyz789"


def test_unparseable_date_becomes_none() -> None:
    raw = "---\nguest: A\npublish_date: sometime soon\n---\nA (00:00:01): Hi.\n"
    assert parse_transcript(raw, "a").publish_date is None


def test_body_without_timestamps_is_one_block() -> None:
    parsed = parse_transcript("---\nguest: A\n---\nJust some prose with no speakers.\n", "a")
    assert len(parsed.turns) == 1
    assert parsed.turns[0].speaker is None
    assert parsed.turns[0].start_seconds is None


def test_empty_input_does_not_raise() -> None:
    parsed = parse_transcript("", "empty-one")
    assert parsed.turns == []
    assert parsed.guest == "Empty One"


def test_mm_ss_timestamps_and_helpers() -> None:
    assert timestamp_to_seconds("01:02") == 62
    assert timestamp_to_seconds("1:02:03") == 3723
    assert format_timestamp(3723) == "01:02:03"
    assert format_timestamp(None) is None
    assert slug_to_name("noah-weiss") == "Noah Weiss"
    assert parse_turns("Bob (05:00): Hi")[0].start_seconds == 300


def test_split_frontmatter_without_block() -> None:
    meta, body, warnings = split_frontmatter("no frontmatter here")
    assert meta == {}
    assert body == "no frontmatter here"
    assert warnings
