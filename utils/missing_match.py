# -*- coding: utf-8 -*-
"""
utils/missing_match.py — منطق المطابقة المشترك لكشف المنتجات المفقودة.
=====================================================================
وحدة نقية (بلا Streamlit) تجمع: التطبيع العربي، الهيكل العظمي للحجب، فهرسة
الكتالوج، والمطابقة الضبابية المحجوبة. تُستخدم من:
  • app.py::_compute_missing_from_store (الإنتاج)
  • tests/baseline_missing.py + tests/test_missing_accuracy.py (القياس/الاختبار)
فاستخدام نفس الكود يضمن أن القياس يعكس الإنتاج بدقة (لا انحراف).

السبب الجذري الذي تعالجه (مقيس في tests/PHASE0_MISSING_DIAGNOSIS.md):
  الحجب بتطابق الكلمات الحرفي يفشل عند اختلاف الإملاء العربي
  (كاشاريل↔كاشريل) فلا يُقارَن منتجان نملك أحدهما ⇒ إيجابية كاذبة.
  الحل: حجب بالهيكل العظمي (إزالة الحروف الضعيفة) فتتشارك النسخ الإملائية
  نفس المحجب ⇒ تُقارَن ⇒ تُصفّى بالمطابق الصارم (token_set_ratio @ العتبة).
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from rapidfuzz import fuzz, process as _rf_process

from engines.engine import (
    normalize_name as _normalize_name,
    normalize as _normalize,
    extract_brand_fast as _extract_brand_fast,
    extract_size as _extract_size,
)

# ── عتبات (مصدر واحد) ──────────────────────────────────────────────
try:
    import config as _cfg
    CONFIRM_TH: float = float(getattr(_cfg, "MISSING_CONFIRMED_THRESHOLD", 82))
    REVIEW_TH: float = float(getattr(_cfg, "MISSING_REVIEW_THRESHOLD", 70))
except Exception:  # pragma: no cover - config دائماً متاح في الإنتاج
    CONFIRM_TH, REVIEW_TH = 82.0, 70.0

SIZE_TOL = 8.0  # تسامح فرق الحجم (مل) لاعتبار حجمين متوافقين

# كلمات شائعة تُستبعد من الاسم المجرّد (نفس قائمة app.py التاريخية)
MISS_STOP = set(
    "عطر عينه عينة تستر سامبل ماء او دو دي بارفيوم برفيوم بارفان تواليت توالت "
    "كولونيا كولن مل غرام للرجال للنساء رجالي نسائي".split()
)

_DIAC_RE = re.compile(r"[ً-ْٰـ]")
# الحروف العربية الضعيفة المتغيّرة إملائياً — تُحذف في الهيكل العظمي للحجب فقط
_AR_WEAK = str.maketrans("", "", "اويهءأإآةىؤئ")


def ar_norm(s: str) -> str:
    """تطبيع عربي خفيف: إزالة التشكيل/التطويل وتوحيد الهمزات والتاء والألف المقصورة."""
    s = _DIAC_RE.sub("", str(s))
    return (s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
             .replace("ة", "ه").replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي"))


MISS_STOP_N = {ar_norm(w) for w in MISS_STOP}


def ar_skeleton(tok: str) -> str:
    """هيكل عظمي لكلمة (للحجب فقط، لا للتسجيل): يزيل الحروف العربية الضعيفة المتغيّرة
    إملائياً فتتشارك النسخ نفس المفتاح: كاشاريل/كاشريل→كشرل، ديبتك/ديبتيك→دبتك،
    انغارو/أونغارو→نغر. الكلمات اللاتينية لا تتأثر (تبقى كما هي)."""
    sk = ar_norm(tok).translate(_AR_WEAK)
    return sk if len(sk) >= 2 else ar_norm(tok)


def miss_bare(nm: str) -> str:
    """الاسم المجرّد للمطابقة: تطبيع عربي + تطبيع المحرّك (280+ مرادف) + إزالة
    الكلمات الشائعة/الأرقام/القصيرة. هو الأساس الذي يُحسب عليه token_set_ratio."""
    return " ".join(
        t for t in _normalize_name(ar_norm(nm)).split()
        if ar_norm(t) not in MISS_STOP_N and not re.fullmatch(r"\d+", t) and len(t) >= 2
    )


def miss_toks(bare: str) -> List[str]:
    """كلمات الحجب الحرفية (≥3 أحرف) — أعلى 6."""
    return [t for t in bare.split() if len(t) >= 3][:6]


def skel_toks(bare: str) -> List[str]:
    """كلمات الحجب بالهيكل العظمي (≥3 أحرف بعد التجريد) — أعلى 8.
    أوسع من miss_toks ليلتقط النسخ الإملائية المختلفة. للحجب فقط."""
    out: List[str] = []
    seen: Set[str] = set()
    for t in bare.split():
        sk = ar_skeleton(t)
        if len(sk) >= 3 and sk not in seen:
            seen.add(sk)
            out.append(sk)
        if len(out) >= 8:
            break
    return out


def skel_signature(bare: str) -> frozenset:
    """توقيع هيكلي **كامل** لكل كلمات الاسم (بلا فلتر طول) — للتمييز الدقيق بين
    «نسخة إملائية» و«كلمة مختلفة». مثال: واتش(تش) ≠ بيك(بك) فلا يتساوى التوقيع،
    بينما كاشريل=كاشاريل=(كشرل). يُستخدم لقرار الإخفاء في النطاق 82-90 (skel_exact)."""
    return frozenset(ar_skeleton(t) for t in bare.split() if t)


class CatalogIndex:
    """فهرس منتجاتنا للحجب والمطابقة السريعة. يبني:
      • items: [{bare, brand_n, size, raw}]
      • inv      : كلمة حرفية → فهارس
      • inv_skel : كلمة بالهيكل العظمي → فهارس (يلتقط اختلاف الإملاء)
      • brand_idx: ماركة مطبَّعة → فهارس
    """

    def __init__(self, names: List[str]):
        self.items: List[Dict] = []
        self.inv: Dict[str, Set[int]] = {}
        self.inv_skel: Dict[str, Set[int]] = {}
        self.brand_idx: Dict[str, List[int]] = {}
        for nm in names:
            nm = str(nm)
            bare = miss_bare(nm)
            if not bare:
                continue
            idx = len(self.items)
            brand_n = _normalize(_extract_brand_fast(nm) or "")
            self.items.append({
                "bare": bare, "brand_n": brand_n,
                "size": _extract_size(nm), "raw": nm,
            })
            for t in miss_toks(bare):
                self.inv.setdefault(t, set()).add(idx)
            for t in skel_toks(bare):
                self.inv_skel.setdefault(t, set()).add(idx)
            if brand_n:
                self.brand_idx.setdefault(brand_n, []).append(idx)

    def __len__(self) -> int:
        return len(self.items)

    def block(self, cand_bare: str, cand_brand_n: str = "", cap: int = 800) -> List[int]:
        """مرشّحو المقارنة: اتحاد (كلمات حرفية ∪ كلمات هيكل عظمي ∪ نفس الماركة)."""
        cidx: Set[int] = set()
        for t in miss_toks(cand_bare):
            cidx |= self.inv.get(t, set())
        for t in skel_toks(cand_bare):
            cidx |= self.inv_skel.get(t, set())
        if cand_brand_n:
            cidx.update(self.brand_idx.get(cand_brand_n, []))
        if len(cidx) > cap:
            # محجب واسع جداً (كلمة شائعة) — extractOne سريع لكن نحدّه للأمان
            return list(cidx)[:cap]
        return list(cidx)

    def best_match(self, cand_bare: str, cand_brand_n: str = "",
                   cand_size: float = 0.0) -> Tuple[float, Optional[Dict], bool, bool, float]:
        """أفضل تطابق ضبابي ضمن المحجوبين.
        يُعيد (top_sc, top_item|None, top_size_ok, skel_exact, sizematch_sc):
          • top_sc/top_item: أعلى token_set_ratio وعنصره — أساس قرار الإخفاء (محافظ).
          • top_size_ok    : توافق حجم أعلى تطابق (يميّز المملوك عن وهم subset).
          • skel_exact     : هل أعلى تطابق يشارك كل كلمات الهيكل العظمي؟ (تلميح فقط).
          • sizematch_sc   : أعلى درجة بين المرشّحين **المتوافقين بالحجم** — للمراجعة
                             فقط (تلميح «محتمل مملوك») لا للإخفاء، فلا تُخفي مفقوداً
                             حقيقياً (مشكلة توس‑مان: وهم subset بنفس الحجم بدرجة عالية).
        """
        cidx = self.block(cand_bare, cand_brand_n)
        if not cidx:
            return 0.0, None, True, False, 0.0
        bares = [self.items[i]["bare"] for i in cidx]
        cands = _rf_process.extract(cand_bare, bares, scorer=fuzz.token_set_ratio,
                                    limit=min(8, len(bares)))
        if not cands:
            return 0.0, None, True, False, 0.0

        def _size_ok(j: int) -> bool:
            osz = self.items[cidx[j]]["size"]
            return (not cand_size) or (not osz) or abs(cand_size - osz) <= SIZE_TOL

        # قرار الإخفاء يعتمد على أعلى تطابق فقط (محافظ — لا تفضيل يرفع وهماً للإخفاء)
        _, top_sc, top_pos = cands[0]
        top_item = self.items[cidx[top_pos]]
        top_size_ok = _size_ok(top_pos)
        # skel_exact: توقيع هيكلي كامل (كل الكلمات) — نسخة إملائية حقيقية فقط
        cand_sig = skel_signature(cand_bare)
        skel_exact = bool(cand_sig) and cand_sig == skel_signature(top_item["bare"])
        # أعلى درجة بين المتوافقين بالحجم (للمراجعة فقط)
        sizematch_sc = next((float(s) for (_, s, p) in cands if _size_ok(p)), 0.0)
        return float(top_sc), top_item, top_size_ok, skel_exact, sizematch_sc


# فوق هذه الدرجة = تطابق عالٍ مؤكد يُخفى مباشرة. بين confirm_th وهذه: نُخفي فقط
# إن كان نسخة إملائية (skel_exact)؛ لأن token_set لا يميّز كلمة بإملاء مختلف
# (كاشريل↔كاشاريل ⇒ إخفاء) عن كلمة مختلفة بنفس بادئة الماركة (واتش≠بيك ⇒ لا إخفاء).
HARD_CONFIRM_TH = 90.0


def classify(top_sc: float, top_size_ok: bool, brand_match: bool, skel_exact: bool,
             sizematch_sc: float = 0.0,
             confirm_th: float = CONFIRM_TH, review_min: float = REVIEW_TH,
             hard_confirm: float = HARD_CONFIRM_TH) -> str:
    """قرار ثلاثي محافظ — عند الشك «review» (يبقى ظاهراً، يُحسم) لا «green» ولا حذف:
      • owned  : نملكه فعلاً ⇒ يُخفى من المفقودة.
      • review : محتمل نملكه ⇒ يبقى ظاهراً للتحقق اليدوي/AI.
      • green  : مفقود مؤكد.

    مبدأ السلامة (طلب المستخدم: لا فقدان مفقود حقيقي):
      • الإخفاء على أعلى تطابق + الحجم فقط؛ وفي النطاق 82-90 يُشترط تطابق الهيكل
        العظمي (نسخة إملائية) كي لا يُخفى منتج مختلف يشارك بادئة ماركة طويلة.
      • الهيكل العظمي وتطابق الحجم لمرشّح أقل تشابهاً ⇒ للمراجعة فقط (ظاهر)، لا للإخفاء.
    """
    if top_sc >= confirm_th and top_size_ok:
        if top_sc >= hard_confirm or skel_exact:
            return "owned"                   # ≥90 أو نسخة إملائية + حجم متوافق ⇒ نملكه
        return "review"                      # 82-90 بكلمة مميِّزة مختلفة ⇒ مراجعة (ظاهر) لا إخفاء
    if top_sc >= confirm_th and not top_size_ok:
        return "review"                      # نفس الاسم بحجم مختلف ⇒ نسخة/حجم محتمل
    if sizematch_sc >= review_min:
        return "review"                      # يوجد شبيه متوافق الحجم (≥70) ⇒ محتمل مملوك (ظاهر)
    if top_sc >= review_min and top_size_ok:
        return "review"                      # 70-82 بحجم متوافق ⇒ محتمل نملكه (ظاهر)
    if review_min - 5 <= top_sc < review_min and top_size_ok and (brand_match or skel_exact):
        return "review"                      # 65-70 + (ماركة أو هيكل متطابق) ⇒ محتمل (ظاهر)
    return "green"
