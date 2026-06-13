# -*- coding: utf-8 -*-
"""
أداة قياس دقة كشف المنتجات المفقودة (Baseline / Benchmark).
============================================================
تقيس الواقع الفعلي بلا تنظير:
  • تحمّل المفقودات التي يراها المستخدم الآن (data/missing_cache.pkl).
  • تحمّل كتالوجنا (data/our_catalog_saved.csv).
  • لكل منتج "مفقود مؤكد" (green) تُجري بحثاً ضبابياً **شاملاً بلا حجب**
    مقابل كامل الكتالوج بنفس مُطبِّع المحرك (engine.normalize_name).
  • النتيجة العالية (≥ عتبة) = منتج نملكه فعلاً تسرّب كمفقود = إيجابية كاذبة.

القياس لا يعدّل أي بيانات أو كود إنتاجي — قراءة فقط.
الإخراج: ملخّص ASCII على الكونسول + تقرير UTF-8 مفصّل في tests/baseline_results.txt
"""
import os
import sys
import time

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process as rf_process

# اجعل جذر المشروع قابلاً للاستيراد
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from engines.engine import normalize_name, extract_brand_fast, extract_size  # noqa: E402

DATA = os.path.join(_ROOT, "data")
CACHE = os.path.join(DATA, "missing_cache.pkl")
CATALOG = os.path.join(DATA, "our_catalog_saved.csv")
OUT_TXT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baseline_results.txt")
OUT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "baseline_false_positives.csv")

OWNED_TH = 82.0     # ≥ هذا في بحث شامل = نملكه فعلاً (إيجابية كاذبة مؤكدة)
SUSPECT_TH = 70.0   # 70-82 = مشبوه (محتمل نملكه)


def _find_name_col(df):
    for c in df.columns:
        cl = str(c).lower()
        if any(k in str(c) for k in ("اسم", "المنتج")) or any(k in cl for k in ("name", "product")):
            return c
    return df.columns[0]


def main():
    t0 = time.time()
    lines = []

    def emit(s=""):
        lines.append(s)

    # ── تحميل المفقودات المعروضة حالياً ──
    if not os.path.exists(CACHE):
        print("ERROR: missing_cache.pkl not found — run the app once to populate it.")
        return
    miss = pd.read_pickle(CACHE)
    emit("=" * 70)
    emit("BASELINE: دقة كشف المنتجات المفقودة")
    emit("=" * 70)
    emit(f"إجمالي المفقودات المعروضة الآن : {len(miss):,}")
    conf_col = "مستوى_الثقة"
    if conf_col in miss.columns:
        vc = miss[conf_col].value_counts(dropna=False)
        for k, v in vc.items():
            emit(f"   - {k}: {v:,}")
    comp_col = "منتج_المنافس"
    if comp_col not in miss.columns:
        emit("ERROR: عمود منتج_المنافس غير موجود")
        _write(lines)
        return

    # ── تحميل الكتالوج ──
    cat = pd.read_csv(CATALOG, dtype=str, keep_default_na=False)
    ncol = _find_name_col(cat)
    emit(f"عمود اسم منتجاتنا            : {ncol!r}")
    emit(f"عدد منتجاتنا (الكتالوج)       : {len(cat):,}")

    # بناء أسماء الكتالوج المطبَّعة (نفس مُطبِّع المحرك) + الماركة
    cat_raw = [str(x) for x in cat[ncol].tolist() if str(x).strip()]
    cat_bare = []
    cat_keep_raw = []
    for r in cat_raw:
        b = normalize_name(r)
        if b:
            cat_bare.append(b)
            cat_keep_raw.append(r)
    emit(f"أسماء الكتالوج المطبَّعة       : {len(cat_bare):,}")
    emit("")

    # ── البحث الشامل بلا حجب لكل صف green ──
    if conf_col in miss.columns:
        green = miss[miss[conf_col] == "green"].copy()
    else:
        green = miss.copy()
    emit(f"عدد المفقود المؤكد (green) المفحوص: {len(green):,}")

    comp_names = [str(x) for x in green[comp_col].tolist()]
    comp_bare = [normalize_name(x) for x in comp_names]

    # أحجام الكتالوج (لحارس الحجم — يميّز المنتج المملوك الحقيقي عن وهم token_set)
    cat_size = np.array([extract_size(r) for r in cat_keep_raw], dtype=np.float32)

    def _toks3(b):
        return {t for t in b.split() if len(t) >= 3}

    cat_toks3 = [_toks3(b) for b in cat_bare]

    # cdist على دفعات لضبط الذاكرة
    best_scores = np.zeros(len(comp_bare), dtype=np.float32)
    best_idx = np.full(len(comp_bare), -1, dtype=np.int64)
    CHUNK = 2000
    for s in range(0, len(comp_bare), CHUNK):
        e = min(s + CHUNK, len(comp_bare))
        sub = comp_bare[s:e]
        # مصفوفة (sub × catalog) من token_set_ratio
        mat = rf_process.cdist(
            sub, cat_bare, scorer=fuzz.token_set_ratio,
            dtype=np.uint8, workers=-1,
        )
        amax = mat.argmax(axis=1)
        amx = mat.max(axis=1)
        best_scores[s:e] = amx
        best_idx[s:e] = amax
        print(f"  ...فُحص {e:,}/{len(comp_bare):,}", flush=True)

    # حارس الحجم + علم فشل الحجب لكل صف
    comp_size = np.array([extract_size(x) for x in comp_names], dtype=np.float32)
    size_ok = np.zeros(len(comp_bare), dtype=bool)
    block_miss = np.zeros(len(comp_bare), dtype=bool)
    for i in range(len(comp_bare)):
        j = int(best_idx[i])
        if j < 0:
            continue
        cs, os_ = comp_size[i], cat_size[j]
        size_ok[i] = (cs <= 0) or (os_ <= 0) or (abs(cs - os_) <= 8.0)
        # هل كان سيُقارَن في المسار الحيّ؟ (يشترك بكلمة ≥3 أحرف)
        block_miss[i] = len(_toks3(comp_bare[i]) & cat_toks3[j]) == 0

    # ── توزيع الدرجات ──
    def bucket(arr):
        b = {"0-30": 0, "30-50": 0, "50-70": 0, "70-82": 0, "82-90": 0, "90-100": 0}
        for v in arr:
            if v < 30: b["0-30"] += 1
            elif v < 50: b["30-50"] += 1
            elif v < 70: b["50-70"] += 1
            elif v < 82: b["70-82"] += 1
            elif v < 90: b["82-90"] += 1
            else: b["90-100"] += 1
        return b

    emit("")
    emit("توزيع أعلى درجة تشابه (بحث شامل) للمفقود المؤكد مقابل كتالوجنا:")
    for k, v in bucket(best_scores).items():
        emit(f"   {k:>7} : {v:,}")

    n_owned = int((best_scores >= OWNED_TH).sum())
    n_suspect = int(((best_scores >= SUSPECT_TH) & (best_scores < OWNED_TH)).sum())
    # FP صارمة: تشابه عالٍ + حجم متوافق = منتج مملوك حقيقي (ليس وهم token_set)
    fp_strict_mask = (best_scores >= OWNED_TH) & size_ok
    n_fp_strict = int(fp_strict_mask.sum())
    n_fp_blockmiss = int((fp_strict_mask & block_miss).sum())
    susp_size_mask = (best_scores >= SUSPECT_TH) & (best_scores < OWNED_TH) & size_ok
    n_susp_size = int(susp_size_mask.sum())
    n_susp_blockmiss = int((susp_size_mask & block_miss).sum())
    emit("")
    emit("=" * 70)
    emit("الخلاصة (ما الذي يُضخّم العدد):")
    emit(f"  ≥{OWNED_TH:.0f}% تشابه (خام)                         : {n_owned:,}"
         f"  ({100*n_owned/max(1,len(green)):.1f}% من green)")
    emit(f"  ≥{OWNED_TH:.0f}% + حجم متوافق = مملوك مؤكد (FP صارمة) : {n_fp_strict:,}"
         f"  (منها {n_fp_blockmiss:,} بسبب فشل الحجب)")
    emit(f"  70-82% (خام)                               : {n_suspect:,}")
    emit(f"  70-82% + حجم متوافق = مشبوه قوي             : {n_susp_size:,}"
         f"  (منها {n_susp_blockmiss:,} بسبب فشل الحجب)")
    emit("=" * 70)

    # ── حفظ أسوأ المخالفات (green لكن تشابه عالٍ) ──
    susp_rows = []
    order = np.argsort(-best_scores)
    for i in order:
        sc = float(best_scores[i])
        if sc < SUSPECT_TH:
            break
        j = int(best_idx[i])
        susp_rows.append({
            "منتج_المنافس": comp_names[i],
            "أقرب_منتج_لدينا": cat_keep_raw[j] if 0 <= j < len(cat_keep_raw) else "",
            "درجة_التشابه_الشاملة": round(sc, 1),
            "حجم_متوافق": bool(size_ok[i]),
            "فشل_الحجب": bool(block_miss[i]),
            "درجة_المسجّلة": green.iloc[i].get("درجة_التشابه", "") if "درجة_التشابه" in green.columns else "",
            "الماركة": green.iloc[i].get("الماركة", "") if "الماركة" in green.columns else "",
        })
    if susp_rows:
        pd.DataFrame(susp_rows).to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
        emit("")
        emit(f"حُفظت {len(susp_rows):,} حالة مشبوهة في: {os.path.basename(OUT_CSV)}")
        emit("")
        emit("أعلى 25 إيجابية كاذبة محتملة (green لكن نملك شبيهاً قوياً):")
        for r in susp_rows[:25]:
            emit(f"  [{r['درجة_التشابه_الشاملة']:>5}%] {r['منتج_المنافس'][:48]:<48}"
                 f" ≈ {r['أقرب_منتج_لدينا'][:48]}")

    emit("")
    emit(f"زمن القياس: {time.time()-t0:.1f}s")
    _write(lines)

    # ملخّص ASCII للكونسول (تفادياً لمشاكل ترميز العربية)
    print("\n==== BASELINE SUMMARY (ASCII) ====")
    print(f"total_missing_shown : {len(miss)}")
    print(f"green_confirmed     : {len(green)}")
    print(f"raw_ge_82           : {n_owned}")
    print(f"FP_strict(>=82+size): {n_fp_strict}   (block_miss={n_fp_blockmiss})")
    print(f"suspect_raw_70_82   : {n_suspect}")
    print(f"suspect_size_70_82  : {n_susp_size}   (block_miss={n_susp_blockmiss})")
    print(f"report  -> {OUT_TXT}")
    print(f"offenders -> {OUT_CSV}")
    print(f"elapsed: {time.time()-t0:.1f}s")


def _write(lines):
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
