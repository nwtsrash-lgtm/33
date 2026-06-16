"""
Phase 6 — export + dedup tests (utils.salla_shamel_export).

Covers two Phase-6 areas at once:

  • عدم التكرار (dedup): verify_truly_missing separates products already in the
    catalog (direct text OR fuzzy ≥ threshold, normalized with the SHARED
    _bare_match = app._miss_bare) from the genuinely missing ones.
  • التصدير (export): build_salla_shamel_dataframe produces the exact 40-column
    Salla contract, excludes catalog duplicates, and the mandatory quality gate
    drops rows lacking a real image / valid mahwous description (no junk pushed
    to the store).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# Make repo root importable regardless of how pytest is invoked.
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from utils.salla_shamel_export import (  # noqa: E402
    verify_truly_missing,
    build_salla_shamel_dataframe,
    SALLA_SHAMEL_COLUMNS,
    _bare_match,
)

# A real-looking image URL (passes is_real_image_url) and a description that
# carries a mahwous marker (passes is_mahwous_description) so export rows
# survive the quality gate.
_VALID_IMG = "https://cdn.salla.sa/uploads/sample-product.jpg"
_VALID_DESC = (
    "<p>هذا عطر مهووس فاخر يفتح بنفحات حمضية منعشة من البرغموت ثم قلب من "
    "الورد والياسمين وقاعدة خشبية دافئة من خشب الصندل والعنبر تدوم طويلاً "
    "على البشرة بثبات عالٍ وفوحان ملحوظ.</p>"
)


def _catalog():
    return pd.DataFrame({"اسم المنتج": [
        "Dior Sauvage EDP 100ml",
        "Chanel Bleu EDT 100ml",
    ]})


# ── dedup: verify_truly_missing ────────────────────────────────────────────

def test_dedup_direct_text_match_is_found_in_catalog():
    miss = pd.DataFrame({"اسم المنتج": ["Dior Sauvage EDT 100 ml"]})  # bare == catalog
    truly, found = verify_truly_missing(miss, _catalog())
    assert truly.empty
    assert found["اسم المنتج"].tolist() == ["Dior Sauvage EDT 100 ml"]


def test_dedup_fuzzy_subset_match_is_found():
    miss = pd.DataFrame({"اسم المنتج": ["Chanel Bleu Paris 100ml"]})  # superset of catalog tokens
    truly, found = verify_truly_missing(miss, _catalog())
    assert truly.empty
    assert len(found) == 1


def test_dedup_unrelated_is_truly_missing():
    miss = pd.DataFrame({"اسم المنتج": ["Tom Ford Oud Wood 50ml"]})
    truly, found = verify_truly_missing(miss, _catalog())
    assert found.empty
    assert truly["اسم المنتج"].tolist() == ["Tom Ford Oud Wood 50ml"]


def test_dedup_uses_shared_bare_match_normalizer():
    # The catalog entry and the competitor name normalize to the same bare form
    # only because _bare_match (= app._miss_bare) strips عطر/او دو بارفيوم/مل…
    name = "عطر Dior Sauvage او دو بارفيوم 100 مل للرجال"
    assert _bare_match(name) == _bare_match("Dior Sauvage EDP 100ml")
    truly, found = verify_truly_missing(pd.DataFrame({"اسم المنتج": [name]}), _catalog())
    assert truly.empty and len(found) == 1


def test_dedup_empty_catalog_keeps_everything_missing():
    miss = pd.DataFrame({"اسم المنتج": ["Dior Sauvage EDP 100ml", "X Y Z"]})
    truly, found = verify_truly_missing(miss, pd.DataFrame())
    assert len(truly) == 2 and found.empty


# ── export: build_salla_shamel_dataframe ───────────────────────────────────

def test_export_always_has_40_salla_columns():
    miss = pd.DataFrame({"اسم المنتج": ["whatever"]})
    sdf, _ = build_salla_shamel_dataframe(miss, _catalog(), verify_missing=True)
    assert list(sdf.columns) == SALLA_SHAMEL_COLUMNS
    assert len(SALLA_SHAMEL_COLUMNS) == 40


def test_export_excludes_catalog_duplicate():
    miss = pd.DataFrame({
        "اسم المنتج": ["Dior Sauvage EDT 100 ml", "Tom Ford Oud Wood 50ml"],
        "صورة المنتج": [_VALID_IMG, _VALID_IMG],
        "السعر": [500, 900],
        "وصف_AI": [_VALID_DESC, _VALID_DESC],
    })
    sdf, found = build_salla_shamel_dataframe(miss, _catalog(), verify_missing=True)
    assert sdf["أسم المنتج"].tolist() == ["Tom Ford Oud Wood 50ml"]   # dup dropped
    assert found["اسم المنتج"].tolist() == ["Dior Sauvage EDT 100 ml"]


def test_export_quality_gate_rejects_row_without_real_image():
    miss = pd.DataFrame({
        "اسم المنتج": ["Tom Ford Oud Wood 50ml"],
        "السعر": [900],
        "وصف_AI": [_VALID_DESC],            # valid desc but NO image
    })
    sdf, _ = build_salla_shamel_dataframe(miss, _catalog(), verify_missing=True)
    assert sdf.empty                        # no junk exported


def test_export_builds_valid_row_for_real_missing():
    miss = pd.DataFrame({
        "اسم المنتج": ["Tom Ford Oud Wood 50ml"],
        "صورة المنتج": [_VALID_IMG],
        "السعر": [900],
        "وصف_AI": [_VALID_DESC],
    })
    sdf, _ = build_salla_shamel_dataframe(miss, _catalog(), verify_missing=True)
    assert len(sdf) == 1
    row = sdf.iloc[0]
    assert row["أسم المنتج"] == "Tom Ford Oud Wood 50ml"
    assert str(row["سعر المنتج"]) == "900.0"
    assert row["رمز المنتج sku"]            # SKU never empty
    assert row["النوع "] == "منتج"
