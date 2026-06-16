"""
Phase 6 — AI failure / degradation tests (no network).

The AI is an assistant, never a final judge: on failure or ambiguity the
product must fall to "review", never be deleted, and only confident results
may be cached. These tests pin that contract with monkeypatched providers:

  • engine._ai_batch — when ALL providers are down it must NOT stall: it falls
    back to fuzzy score (≥82 → take the first candidate, else → no match), and
    the fallback path writes nothing to the cache.
  • ai_engine.ai_verify_dedup — AI failure → {match:False, confidence:0}
    (review, not delete); only a successful, parsed result is cached
    (success-only); a cache hit short-circuits without calling the AI.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make repo root importable regardless of how pytest is invoked.
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

import engines.engine as engine_mod      # noqa: E402
import engines.ai_engine as ai_mod       # noqa: E402


def _force_providers_down(monkeypatch):
    """No Gemini keys, no OpenRouter key → _ai_batch reaches the fuzzy fallback."""
    monkeypatch.setattr(engine_mod, "GEMINI_API_KEYS", [])
    monkeypatch.setattr(engine_mod, "OPENROUTER_API_KEY", "")


def _isolate_cache(monkeypatch, cached=None):
    """Force the cache to miss (or return ``cached``) and record every write."""
    writes: list = []
    monkeypatch.setattr(engine_mod, "_cget", lambda k: cached)
    monkeypatch.setattr(engine_mod, "_cset", lambda k, v: writes.append((k, v)))
    return writes


# ── engine._ai_batch fuzzy fallback (all providers down) ───────────────────

def test_ai_batch_empty_returns_empty():
    assert engine_mod._ai_batch([]) == []


def test_ai_batch_fallback_high_score_takes_first(monkeypatch):
    _force_providers_down(monkeypatch)
    _isolate_cache(monkeypatch)
    batch = [{"our": "A", "price": 100, "candidates": [{"name": "A", "score": 90}]}]
    assert engine_mod._ai_batch(batch) == [0]


def test_ai_batch_fallback_low_score_is_no_match(monkeypatch):
    _force_providers_down(monkeypatch)
    _isolate_cache(monkeypatch)
    batch = [{"our": "A", "price": 100, "candidates": [{"name": "B", "score": 70}]}]
    assert engine_mod._ai_batch(batch) == [-1]


def test_ai_batch_fallback_threshold_is_82(monkeypatch):
    _force_providers_down(monkeypatch)
    _isolate_cache(monkeypatch)
    at = [{"our": "A", "price": 1, "candidates": [{"name": "A", "score": 82}]}]
    below = [{"our": "A", "price": 1, "candidates": [{"name": "A", "score": 81}]}]
    assert engine_mod._ai_batch(at) == [0]
    assert engine_mod._ai_batch(below) == [-1]


def test_ai_batch_fallback_no_candidates_is_no_match(monkeypatch):
    _force_providers_down(monkeypatch)
    _isolate_cache(monkeypatch)
    assert engine_mod._ai_batch([{"our": "A", "price": 1, "candidates": []}]) == [-1]


def test_ai_batch_fallback_does_not_cache(monkeypatch):
    _force_providers_down(monkeypatch)
    writes = _isolate_cache(monkeypatch)
    engine_mod._ai_batch([{"our": "A", "price": 1, "candidates": [{"name": "A", "score": 95}]}])
    assert writes == []   # fuzzy fallback is never persisted to the cache


# ── ai_engine.ai_verify_dedup ──────────────────────────────────────────────

def test_dedup_missing_data_is_review():
    out = ai_mod.ai_verify_dedup("", [])
    assert out["match"] is False
    assert out["confidence"] == 0


def test_dedup_ai_failure_is_review_and_not_cached(monkeypatch):
    writes = _isolate_cache(monkeypatch)
    monkeypatch.setattr(ai_mod, "call_ai", lambda *a, **k: {"success": False})
    out = ai_mod.ai_verify_dedup("Tom Ford Oud", [{"name": "Creed Aventus", "score": 75}])
    assert out["match"] is False
    assert out["confidence"] == 0
    assert writes == []   # failure is NOT cached (success-only)


def test_dedup_success_is_matched_and_cached(monkeypatch):
    writes = _isolate_cache(monkeypatch)
    monkeypatch.setattr(ai_mod, "call_ai", lambda *a, **k: {
        "success": True,
        "response": '{"match": true, "matched_index": 1, "confidence": 95, "reason": "same"}',
    })
    out = ai_mod.ai_verify_dedup(
        "Creed Aventus 100ml", [{"name": "Creed Aventus EDP 100ml", "score": 88}]
    )
    assert out["match"] is True
    assert out["matched_name"] == "Creed Aventus EDP 100ml"
    assert out["confidence"] == 95
    assert len(writes) == 1   # confident result IS cached


def test_dedup_cache_hit_short_circuits_ai(monkeypatch):
    cached = {"match": True, "matched_name": "X", "confidence": 77, "reason": "cached"}
    _isolate_cache(monkeypatch, cached=cached)
    calls = {"n": 0}

    def _boom(*a, **k):
        calls["n"] += 1
        return {"success": False}

    monkeypatch.setattr(ai_mod, "call_ai", _boom)
    out = ai_mod.ai_verify_dedup(
        "Creed Aventus 100ml", [{"name": "Creed Aventus EDP 100ml", "score": 88}]
    )
    assert out == cached
    assert calls["n"] == 0   # cache hit → AI never called
