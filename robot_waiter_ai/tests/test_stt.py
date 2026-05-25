"""
tests/test_stt.py — Unit tests for speech/stt.py and related helpers.

These are pure logic tests:
  - No faster-whisper installation required.
  - No WhisperModel is ever constructed.
  - No audio files are read from disk.
  - No network access.

Run with:  pytest robot_waiter_ai/tests/test_stt.py -v
"""
from __future__ import annotations

import asyncio
from http import HTTPStatus
from pathlib import Path

import pytest

from robot_waiter_ai.demo.voice_web_demo import handle_transcribe_request
from robot_waiter_ai.inference.menu_context_builder import _extract_menu_item_names
from robot_waiter_ai.speech.stt import SpeechToText, _PROMPT_MAX_CHARS

pytestmark = pytest.mark.unit

# Absolute path to the real menu.yaml — mirrors convention in other test files.
_MENU_PATH = Path(__file__).resolve().parents[1] / "data" / "menu.yaml"

# ---------------------------------------------------------------------------
# Expected result-dict keys for every transcribe() response.
# ---------------------------------------------------------------------------
_REQUIRED_KEYS = {"text", "segments", "language", "language_probability", "low_confidence"}


# ===========================================================================
# 1. Empty audio → fast path, no model loading
# ===========================================================================

def test_empty_audio_returns_early():
    """transcribe(b"") must return the fast-path sentinel without loading the model."""
    stt = SpeechToText()

    result = asyncio.run(stt.transcribe(b""))

    # All five keys must be present.
    missing = _REQUIRED_KEYS - set(result.keys())
    assert not missing, f"Result dict is missing keys: {missing}"

    # Fast-path semantics.
    assert result["text"] == "", (
        f"Expected empty text for empty audio, got: {result['text']!r}"
    )
    assert result["low_confidence"] is True, (
        "Expected low_confidence=True for empty audio"
    )
    assert result["segments"] == [], (
        "Expected empty segments list for empty audio"
    )

    # CRITICAL: the model must NOT have been loaded.
    assert stt._model is None, (
        "WhisperModel was loaded despite empty-audio fast path — "
        "this blocks the event loop and wastes memory on startup."
    )


# ===========================================================================
# 2. build_initial_prompt — long input must not cut mid-word
# ===========================================================================

def test_build_initial_prompt_no_mid_word_cut():
    """Truncation must always land on a complete word, never inside one."""
    # 50 distinct names each exactly 10 ASCII chars.
    # Joined: 50*10 + 49*2 = 598 chars — well over _PROMPT_MAX_CHARS.
    names = [f"MenuItem{i:02d}" for i in range(50)]

    result = SpeechToText.build_initial_prompt(names)

    assert len(result) <= _PROMPT_MAX_CHARS, (
        f"Prompt exceeds cap: {len(result)} > {_PROMPT_MAX_CHARS}"
    )

    # The result is a comma-separated list.  Every item must be exactly one
    # of the original 10-char names — i.e. no item was cut in half.
    items = result.split(", ")
    name_set = set(names)
    for item in items:
        assert item in name_set, (
            f"Item {item!r} is not a complete name — likely a mid-word cut. "
            f"Full result: {result!r}"
        )

    # No trailing comma or whitespace artefacts.
    assert not result.endswith(","), f"Result ends with comma: {result!r}"
    assert not result.endswith(", "), f"Result ends with ', ': {result!r}"


# ===========================================================================
# 3. build_initial_prompt — empty input
# ===========================================================================

def test_build_initial_prompt_empty_input():
    """An empty name list must produce an empty string, not crash."""
    result = SpeechToText.build_initial_prompt([])

    assert result == "", f"Expected empty string, got: {result!r}"


# ===========================================================================
# 4. build_initial_prompt — deduplication
# ===========================================================================

def test_build_initial_prompt_deduplicates():
    """Duplicate names must appear exactly once in the output."""
    names = ["döner", "döner", "ayran"]

    result = SpeechToText.build_initial_prompt(names)

    items = result.split(", ")
    counts = {item: items.count(item) for item in items}

    assert counts.get("döner", 0) == 1, (
        f"'döner' appears {counts.get('döner', 0)} times; expected 1. "
        f"Full result: {result!r}"
    )
    assert counts.get("ayran", 0) == 1, (
        f"'ayran' appears {counts.get('ayran', 0)} times; expected 1. "
        f"Full result: {result!r}"
    )
    # Total item count must be 2 (deduped), not 3.
    assert len(items) == 2, (
        f"Expected 2 items after deduplication, got {len(items)}: {items}"
    )


# ===========================================================================
# 5. _extract_menu_item_names — real menu.yaml
# ===========================================================================

def test_extract_menu_item_names_returns_list():
    """Must return a non-empty flat list of non-empty strings from the real menu."""
    result = _extract_menu_item_names(_MENU_PATH)

    assert isinstance(result, list), f"Expected list, got {type(result).__name__}"
    assert len(result) > 0, "Got empty list — menu.yaml may not have been read."

    for i, item in enumerate(result):
        assert isinstance(item, str) and item, (
            f"Item at index {i} is not a non-empty string: {item!r}"
        )

    # Spot-check: the first menu item's name must be present.
    assert "Mercimek Çorbası" in result, (
        f"'Mercimek Çorbası' missing from extracted names. Got: {result}"
    )

    # Spot-check: at least one alias must be present (proves alias extraction works).
    assert "mercimek" in result, (
        f"Alias 'mercimek' missing — alias extraction may be broken. Got: {result}"
    )


# ===========================================================================
# 6. handle_transcribe_request — empty body
# ===========================================================================

def test_handle_transcribe_request_empty_body():
    """Empty audio body must not raise and must return a well-formed response."""
    stt = SpeechToText()

    # Must not raise under any circumstances.
    status_code, payload = handle_transcribe_request(
        b"",
        stt=stt,
        use_vad=False,
        initial_prompt="",
    )

    # The empty-bytes fast path fires inside stt.transcribe() and returns a
    # valid (non-error) result, so we expect 200 OK with text == "".
    assert status_code == HTTPStatus.OK, (
        f"Expected 200 OK for empty body, got {status_code}. Payload: {payload}"
    )
    assert "error" not in payload, (
        f"Unexpected error key in payload: {payload}"
    )
    assert payload.get("text") == "", (
        f"Expected empty text, got: {payload.get('text')!r}"
    )
    assert payload.get("low_confidence") is True, (
        "Expected low_confidence=True for empty-body transcription"
    )
    # Model must still be None — no model loading for empty audio.
    assert stt._model is None, (
        "WhisperModel was loaded for an empty audio body — fast path did not fire."
    )
