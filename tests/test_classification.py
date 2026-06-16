"""
Phase 6 — classification tests.

Exercises the triage in engines.missing_products_engine.detect_missing with
``use_ai=False`` (fully deterministic — no network) plus the structural guard:

  • score ≥ EXISTS_THRESHOLD (85) AND structural match → confirmed exists
    (NOT returned as missing).
  • score < UNCERTAIN_LOWER (70)               → sure_missing.
  • name matches but size/brand differ         → structural mismatch → kept as
    "uncertain" (never silently dropped — Zero Data Drop).

These lock the band thresholds and the "same name, different size ⇒ not the
same product" rule that prevents owned products leaking into the missing list
(and vice-versa).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# Make repo root importable regardless of how pytest is invoked.
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from engines.missing_products_engine import (  # noqa: E402
    detect_missing,
    _normalize,
    _structural_match,
    EXISTS_THRESHOLD,
    UNCERTAIN_LOWER,
)


def _catalog():
    df = pd.DataFrame({
        "أسم المنتج": [
            "Dior Sauvage EDP 100ml",
            "Chanel Bleu EDT 100ml",
            "Creed Aventus 100ml",
        ],
        "سعر المنتج": [550, 600, 1200],
    })
    df["_norm"] = df["أسم المنتج"].apply(_normalize)
    return df[df["_norm"].str.len() > 0].reset_index(drop=True)


def _comp(rows):
    df = pd.DataFrame(rows)
    df["_norm"] = df["اسم_المنتج"].apply(_normalize)
    return df


def _detect(rows):
    return detect_missing(_comp(rows), _catalog(), use_ai=False)


# ── Band thresholds are sane ───────────────────────────────────────────────

def test_band_thresholds_ordered():
    assert UNCERTAIN_LOWER < EXISTS_THRESHOLD == 85.0
    assert UNCERTAIN_LOWER == 70.0


# ── End-to-end classification (AI off) ─────────────────────────────────────

def test_exact_catalog_match_is_not_missing():
    out = _detect([
        {"اسم_المنتج": "Dior Sauvage EDP 100ml", "السعر": 540,
         "الرابط": "u1", "الصورة": "", "المنافس": "c1"},
    ])
    assert [m.name for m in out] == []   # confirmed exists → not missing


def test_unrelated_product_is_sure_missing():
    out = _detect([
        {"اسم_المنتج": "Tom Ford Oud Wood 50ml", "السعر": 900,
         "الرابط": "u2", "الصورة": "", "المنافس": "c2"},
    ])
    assert len(out) == 1
    assert out[0].name == "Tom Ford Oud Wood 50ml"
    assert out[0].confidence == "sure_missing"


def test_same_name_different_size_is_uncertain_not_dropped():
    # Name matches Dior Sauvage in the catalog (score ≥ 85) but the size
    # differs (50ml vs 100ml) → structural mismatch → kept as uncertain.
    out = _detect([
        {"اسم_المنتج": "Dior Sauvage EDP 50ml", "السعر": 500,
         "الرابط": "u3", "الصورة": "", "المنافس": "c3"},
    ])
    assert len(out) == 1
    assert out[0].confidence == "uncertain"


def test_mixed_batch_keeps_only_real_candidates():
    out = _detect([
        {"اسم_المنتج": "Dior Sauvage EDP 100ml", "السعر": 540,
         "الرابط": "u1", "الصورة": "", "المنافس": "c1"},   # exists
        {"اسم_المنتج": "Tom Ford Oud Wood 50ml", "السعر": 900,
         "الرابط": "u2", "الصورة": "", "المنافس": "c2"},   # sure missing
        {"اسم_المنتج": "Dior Sauvage EDP 50ml", "السعر": 500,
         "الرابط": "u3", "الصورة": "", "المنافس": "c3"},   # uncertain
    ])
    names = sorted(m.name for m in out)
    assert names == ["Dior Sauvage EDP 50ml", "Tom Ford Oud Wood 50ml"]


def test_duplicate_competitor_rows_collapse_keeping_higher_price():
    out = _detect([
        {"اسم_المنتج": "Tom Ford Oud Wood 50ml", "السعر": 700,
         "الرابط": "u1", "الصورة": "", "المنافس": "c1"},
        {"اسم_المنتج": "Tom Ford Oud Wood 50ml", "السعر": 950,
         "الرابط": "u2", "الصورة": "", "المنافس": "c2"},
    ])
    assert len(out) == 1                 # same product → one missing row
    assert out[0].price == 950.0         # keeps the higher competitor price


# ── Structural guard unit tests ────────────────────────────────────────────

def test_structural_match_same_size_different_concentration():
    # 100ml == 100ml, same brand → same product (concentration is not a blocker)
    assert _structural_match("Dior Sauvage EDP 100ml", "Dior Sauvage EDT 100ml")


def test_structural_match_rejects_different_size():
    assert not _structural_match("Dior Sauvage 50ml", "Dior Sauvage 100ml")


def test_structural_match_unjudgeable_is_true():
    # No size and no resolvable brand → cannot prove different → treat as match.
    assert _structural_match("سوفاج", "سوفاج")
