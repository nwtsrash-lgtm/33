"""
Phase 6 — matching tests.

Locks the golden normalizer used for the live missing-products decision:

  • app._miss_bare — the inline golden normalizer (app.py ~657). The single
    matcher for the live missing/dedup decision (CLAUDE.md).
  • utils.salla_shamel_export._bare_match — a HAND-SYNCED copy used by the
    export dedup gate; it must stay byte-identical to _miss_bare (constraint:
    "زامنهما عند أي تغيير"). This test fails loudly if the two ever drift.
  • engines.engine.normalize_name — synonym + noise normalization.
  • app._ar_skeleton / app._skel_toks — Arabic skeleton blocking that catches
    spelling variants (كاشريل ↔ كاشاريل) the literal-word blocker misses.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make repo root importable regardless of how pytest is invoked.
_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

import app  # noqa: E402  (heavy import: Streamlit bare mode — verified to work)
from engines.engine import normalize_name  # noqa: E402
from utils.salla_shamel_export import _bare_match  # noqa: E402


# Representative competitor/catalog names: Arabic, Latin, mixed, with stop
# words, sizes, digits, gender markers, testers/samples, and spelling variants.
_NAMES = [
    "عطر شانيل بلو او دو بارفيوم 100 مل للرجال",
    "Chanel Bleu EDP 100ml",
    "ديور سوفاج او دو تواليت 100مل",
    "Dior Sauvage EDT 100 ml للجنسين",
    "عطر كريد افنتوس 120 مل",
    "Creed Aventus 120ml رجالي",
    "تستر توم فورد عود وود 50 مل",
    "Tom Ford Oud Wood 50ml sample",
    "عطر كاشريل انايس انايس",
    "عطر كاشاريل انايس انايس",
    "نارسيسو رودريغيز فور هير او دو بارفيوم",
    "Narciso Rodriguez For Her EDP 90 مل نسائي",
    "212 VIP Men 100ml",                 # 212 = product number, must survive size strip
    "كارولينا هيريرا 212 رجالي",
    "Versace Eros EDT",
    "فيرزاتشي ايروس",
    "عطر 100 مل",                         # only noise/size/digits → empty bare
    "ml مل عطر",                          # only stops → empty
    "",
    "   ",
]


@pytest.mark.parametrize("name", _NAMES)
def test_bare_match_is_byte_identical_to_miss_bare(name):
    """The export dedup gate's _bare_match is a hand-synced copy of the live
    _miss_bare. They must produce identical output for every input, otherwise
    the export gate and the live missing path disagree."""
    assert app._miss_bare(name) == _bare_match(name)


def test_miss_bare_strips_stops_sizes_and_short_tokens():
    assert app._miss_bare("عطر شانيل بلو او دو بارفيوم 100 مل للرجال") == "chanel bleu"


def test_miss_bare_drops_pure_digits_and_size():
    out = app._miss_bare("Creed Aventus 120 مل").split()
    assert "creed" in out and "aventus" in out
    assert "120" not in out


def test_miss_bare_empty_on_only_noise():
    assert app._miss_bare("عطر 100 مل") == ""
    assert app._miss_bare("") == ""
    assert app._miss_bare("   ") == ""


def test_normalize_name_removes_noise_and_unifies_hamza():
    out = normalize_name("عطر أيسينشيال بيرفيوم 100مل للجنسين")
    # noise words (عطر/بيرفيوم/للجنسين) and the size token removed; hamza أ→ا
    assert "عطر" not in out
    assert "بيرفيوم" not in out
    assert "100" not in out
    assert "أ" not in out


def test_normalize_name_non_string_is_empty():
    assert normalize_name(None) == ""
    assert normalize_name(123) == ""


def test_ar_skeleton_collapses_spelling_variants():
    # كاشريل and كاشاريل differ only by a weak letter → identical skeleton.
    assert app._ar_skeleton("كاشريل") == app._ar_skeleton("كاشاريل")


def test_skel_toks_share_blocking_token_for_variants():
    a = set(app._skel_toks(app._miss_bare("عطر كاشريل انايس")))
    b = set(app._skel_toks(app._miss_bare("عطر كاشاريل انايس")))
    assert a & b  # ≥1 shared skeleton token → blocking catches both spellings
