# -*- coding: utf-8 -*-
"""
إعادة حساب المفقودات end-to-end بالكود الجديد — يحاكي app.py::_compute_missing_from_store
عبر نفس وحدة المطابقة (utils/missing_match) فلا انحراف عن الإنتاج.
يطبع التوزيع الجديد (owned/review/green) ويقيس الإيجابيات الكاذبة المتبقية بنفس
منهج baseline (بحث شامل بلا حجب). قراءة فقط — لا يعدّل أي بيانات.
"""
import os
import sys
import time

import numpy as np
import pandas as pd
from rapidfuzz import fuzz, process as rf_process

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from engines.engine import (  # noqa: E402
    is_sample, is_tester, classify_product, extract_size,
    normalize, extract_brand_fast, enrich_known_brands, normalize_name,
)
from engines.competitor_intelligence import CompetitorIntelligence  # noqa: E402
from utils.missing_match import CatalogIndex, miss_bare, classify  # noqa: E402

DATA = os.path.join(_ROOT, "data")
CATALOG = os.path.join(DATA, "our_catalog_saved.csv")
DB = os.path.join(DATA, "pricing_v18.db")

_BAD = ('deodorant', 'hair_mist', 'body_mist', 'body_lotion',
        'soap', 'shower_gel', 'after_shave', 'rejected', 'other')
_SETW = ('مجموعة', 'مجموعه', 'طقم', 'gift set', 'gift box', 'set ')


def _is_non_perfume(nm, pr):
    if classify_product(nm) in _BAD:
        return True
    low = nm.lower()
    if any(w in low for w in _SETW):
        return True
    if pr > 0 and (pr < 20 or pr > 15000):
        return True
    if len(nm.strip()) < 8:
        return True
    sz = extract_size(nm)
    if not sz or sz <= 0 or sz < 10.0:
        return True
    return False


def main():
    t0 = time.time()
    cat = pd.read_csv(CATALOG, dtype=str, keep_default_na=False)
    ncol = next((c for c in cat.columns if any(k in str(c) for k in ("اسم", "المنتج"))
                 or any(k in str(c).lower() for k in ("name", "product"))), cat.columns[0])
    try:
        enrich_known_brands(db_path=DB)
    except Exception:
        pass
    ci = CompetitorIntelligence(db_path=DB)
    prods, total = ci.find_missing_products(cat, page=0, per_page=1000000)
    print(f"candidates_from_CI : {total}")

    # دمج بالاسم المجرّد
    cand = {}
    for p in prods:
        bb = miss_bare(p.get("product_name", ""))
        if not bb:
            continue
        pr = float(p.get("min_price", 0) or 0)
        ex = cand.get(bb)
        if ex is None or pr < ex[1]:
            cand[bb] = (p, pr)

    idx = CatalogIndex(cat[ncol].dropna().astype(str).tolist())
    print(f"catalog_indexed    : {len(idx)}")

    owned = review = green = drop_np = 0
    green_names = []
    audit_new_owned = []   # owned اعتمد على الهيكل العظمي عند 70-82 (كبت جديد — للتدقيق)
    for bb, (p, pr) in cand.items():
        nm = str(p.get("product_name", "") or "")
        if _is_non_perfume(nm, float(pr or 0)):
            drop_np += 1
            continue
        cbn = normalize(extract_brand_fast(nm) or extract_brand_fast(str(p.get("brand", "") or "")) or "")
        csz = extract_size(nm)
        sc, it, sok, sk, smsc = idx.best_match(bb, cbn, csz)
        bm = bool(it and cbn and it["brand_n"] == cbn)
        v = classify(sc, sok, bm, sk, smsc)
        if v == "owned":
            owned += 1
            # الكبت الجديد المحتمل الخطر: أُخفي بسبب skel_exact رغم درجة < 82
            if sk and sc < 82 and it is not None:
                audit_new_owned.append((round(sc, 1), nm, it["raw"]))
        elif v == "review":
            review += 1
        else:
            green += 1
            green_names.append(nm)
    # تدقيق الكبت الجديد (الأخطر على فقدان مفقود حقيقي)
    print(f"\nnew_owned_via_skeleton(<82): {len(audit_new_owned)}")
    audit_new_owned.sort()
    pd.DataFrame(audit_new_owned, columns=["score", "hidden_competitor", "matched_ours"]).to_csv(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_new_owned.csv"),
        index=False, encoding="utf-8-sig")

    print("\n==== RECOMPUTE (NEW CODE) ====")
    print(f"after_name_merge   : {len(cand)}")
    print(f"dropped_non_perfume: {drop_np}")
    print(f"owned(hidden)      : {owned}")
    print(f"review             : {review}")
    print(f"green(confirmed)   : {green}")
    print(f"total_shown(g+r)   : {green + review}")

    # قياس FP المتبقية على green الجديد (بحث شامل بلا حجب + حارس الحجم)
    cat_keep, cat_bare, _csz = [], [], []
    for r in cat[ncol].dropna().astype(str).tolist():
        b = normalize_name(r)
        if b:
            cat_keep.append(r)
            cat_bare.append(b)
            _csz.append(extract_size(r))
    cat_size = np.array(_csz, dtype=np.float32)
    gb = [normalize_name(x) for x in green_names]
    gsz = np.array([extract_size(x) for x in green_names], dtype=np.float32)
    best = np.zeros(len(gb), dtype=np.float32)
    bidx = np.full(len(gb), -1, dtype=np.int64)
    for s in range(0, len(gb), 2000):
        e = min(s + 2000, len(gb))
        mat = rf_process.cdist(gb[s:e], cat_bare, scorer=fuzz.token_set_ratio, dtype=np.uint8, workers=-1)
        best[s:e] = mat.max(axis=1)
        bidx[s:e] = mat.argmax(axis=1)
    size_ok = np.array([(gsz[i] <= 0) or (cat_size[bidx[i]] <= 0) or abs(gsz[i] - cat_size[bidx[i]]) <= 8.0
                        if bidx[i] >= 0 else True for i in range(len(gb))])
    fp_strict = int(((best >= 82) & size_ok).sum())
    susp = int(((best >= 70) & (best < 82) & size_ok).sum())
    print(f"\nleftover_FP_strict(>=82+size) : {fp_strict}   (was 124)")
    print(f"leftover_suspect(70-82+size)  : {susp}   (was 1592)")
    # عيّنة الـ FP المتبقية في green (للتمييز: مملوك حقيقي vs وهم token_set subset)
    fp_mask = (best >= 82) & size_ok
    fp_rows = [(round(float(best[i]), 1), green_names[i], cat_keep[int(bidx[i])])
               for i in range(len(gb)) if fp_mask[i]]
    fp_rows.sort(reverse=True)
    pd.DataFrame(fp_rows, columns=["score", "still_green_competitor", "closest_ours"]).to_csv(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "leftover_green_fp.csv"),
        index=False, encoding="utf-8-sig")
    print(f"elapsed: {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()
