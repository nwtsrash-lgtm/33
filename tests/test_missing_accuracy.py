# -*- coding: utf-8 -*-
"""
اختبارات دقة كشف المنتجات المفقودة — تحمي الإصلاحات من الانحدار.
تشغيل: pytest tests/test_missing_accuracy.py -q
"""
import os
import sys

import pandas as pd
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import config  # noqa: E402
from utils.missing_match import (  # noqa: E402
    CatalogIndex, miss_bare, ar_skeleton, classify, CONFIRM_TH, REVIEW_TH,
)
from engines.engine import normalize as _normalize, extract_brand_fast, extract_size  # noqa: E402


# كتالوج اختبار صغير (يشمل عربي + إنجليزي + ماركات بإملاء قياسي)
_OUR = [
    "عطر ديور سوفاج او دو بارفيوم 100مل",
    "عطر كاشاريل لو لو أو دو بارفيوم 50مل",
    "عطر ديبتيك دو سون أو دو برفيوم 75 مل",
    "عطر خنجر عمان لاكجري او دو بارفيوم 100مل",
    "Chanel Bleu EDP 100ml",
    "عطر ممنتو موري بيك مي إكستريت دو بارفيوم 100 مل",
]


@pytest.fixture(scope="module")
def idx():
    return CatalogIndex(_OUR)


def _verdict(idx, name: str) -> str:
    bb = miss_bare(name)
    bn = _normalize(extract_brand_fast(name) or "")
    sc, it, sok, sk, sm = idx.best_match(bb, bn, extract_size(name))
    bm = bool(it and bn and it["brand_n"] == bn)
    return classify(sc, sok, bm, sk, sm)


def test_exact_match_not_missing(idx):
    """منتج بنفس الاسم بالضبط ⇒ مملوك (لا يظهر كمفقود)."""
    assert _verdict(idx, "عطر ديور سوفاج او دو بارفيوم 100مل") == "owned"


def test_arabic_english_match(idx):
    """'Dior Sauvage' الإنجليزي = 'ديور سوفاج' العربي ⇒ مملوك (مرادفات normalize_name)."""
    assert miss_bare("Dior Sauvage EDP 100ml") == miss_bare("عطر ديور سوفاج او دو بارفيوم 100مل")
    assert _verdict(idx, "عطر Dior Sauvage 100ml") == "owned"
    # شانيل بلو (عربي) ضد Chanel Bleu (إنجليزي بالكتالوج)
    assert _verdict(idx, "عطر شانيل بلو او دو بارفيوم 100مل") == "owned"


def test_arabic_spelling_variant_owned(idx):
    """نسخة إملائية عربية (كاشريل↔كاشاريل، ديبتك↔ديبتيك، خنجرعمان↔خنجر عمان) ⇒ مملوك.
    هذا السبب الجذري للإيجابيات الكاذبة — يجب أن يلتقطه الحجب بالهيكل العظمي."""
    assert ar_skeleton("كاشاريل") == ar_skeleton("كاشريل")
    assert _verdict(idx, "عطر كاشريل لو لو او دو بارفيوم 50مل") == "owned"
    assert _verdict(idx, "تستر ديبتك دو سن او دي بارفيوم 75مل") == "owned"
    assert _verdict(idx, "عطر خنجرعمان لاكجري او دو برفيوم 100مل") == "owned"


def test_genuine_missing_is_green(idx):
    """منتج لا نملكه إطلاقاً ⇒ مفقود مؤكد (green) — لا يُكبت خطأً."""
    assert _verdict(idx, "عطر توم فورد عود وود او دو بارفيوم 50مل") == "green"
    assert _verdict(idx, "عطر كريد افنتوس او دو بارفيوم 100مل") == "green"


def test_different_size_is_review_not_owned(idx):
    """نفس الاسم بحجم مختلف ⇒ مراجعة (نسخة/حجم محتمل) لا «مملوك» مؤكد."""
    assert _verdict(idx, "عطر ديور سوفاج او دو بارفيوم 50مل") == "review"


def test_same_brand_different_product_not_hidden(idx):
    """منتج مختلف من نفس الماركة (ممنتو موري «واتش مي» ≠ «بيك مي») لا يُخفى (owned).
    حماية من فقدان مفقود حقيقي عبر تطابق الهيكل العظمي الزائف."""
    assert _verdict(idx, "عطر ممنتو موري واتش مي او دو بارفيوم 100مل") != "owned"


def test_thresholds_from_config():
    """العتبات من config — لا أرقام سحرية."""
    assert CONFIRM_TH == float(config.MISSING_CONFIRMED_THRESHOLD)
    assert REVIEW_TH == float(config.MISSING_REVIEW_THRESHOLD)
    assert config.MISSING_BARRIER_THRESHOLD == 85


def test_skeleton_collapses_weak_letters():
    """الهيكل العظمي يزيل الحروف الضعيفة المتغيّرة إملائياً ويُبقي اللاتيني كما هو."""
    assert ar_skeleton("أونغارو") == ar_skeleton("انغارو")
    assert ar_skeleton("dior") == "dior"  # لاتيني بلا تغيير


def test_classify_conservative_on_uncertainty():
    """عند الشك (تشابه متوسط بحجم متوافق) ⇒ review (ظاهر) لا green ولا owned."""
    # 75% بحجم متوافق ⇒ review
    assert classify(75.0, True, False, False, 0.0) == "review"
    # 60% بلا تطابق ماركة/هيكل ⇒ green (مفقود)
    assert classify(60.0, True, False, False, 0.0) == "green"
    # شبيه متوافق الحجم (≥70) موجود ⇒ review حتى لو أعلى تطابق بحجم مختلف
    assert classify(88.0, False, False, False, 72.0) == "review"


def test_no_50k_limit_in_export():
    """إصلاح العطل 4: لا حدّ 50,000 صف في سكربت التصدير (تغطية 100%)."""
    p = os.path.join(_ROOT, "export_missing.py")
    with open(p, encoding="utf-8") as f:
        src = f.read()
    assert "_MAX_COMP_ROWS = 50000" not in src
    assert "no row limit" in src


def test_single_catalog_source_loader():
    """إصلاح العطل 5: موحِّد كتالوج واحد متاح ويُعيد DataFrame."""
    from utils.catalog_loader import load_our_catalog
    df = load_our_catalog()
    assert isinstance(df, pd.DataFrame)  # قد يكون فارغاً في بيئة بلا بيانات — لا يرمي


def test_barrier_uses_normalized_names_and_config_threshold():
    """إصلاح العطل 1: smart_missing_barrier يطبّع الأسماء ويستخدم عتبة config."""
    import inspect
    from engines import engine
    src = inspect.getsource(engine.smart_missing_barrier)
    assert "normalize_name" in src                     # يطبّع لا خام
    assert "MISSING_BARRIER_THRESHOLD" in src           # عتبة موحّدة من config
    assert "threshold: int = 92" not in src             # لا رقم سحري 92
