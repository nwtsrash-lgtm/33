# -*- coding: utf-8 -*-
"""
utils/catalog_loader.py — مصدر واحد للحقيقة لكتالوج متجرنا.
==========================================================
كان الكتالوج يُحمَّل من مصادر مختلفة (CSV في مسار التطبيق، جدول our_catalog في DB
في سكربت التصدير) وقد يتباينان (مثلاً 7,863 في CSV مقابل 7,795 في DB) ⇒ نتائج
مفقودات مختلفة. هذا المحمِّل يوحّدهما:
  • يفضّل CSV (our_catalog_saved.csv) لأنه عادةً الأحدث/الأكمل (يُحدَّث من الواجهة).
  • يسقط إلى جدول DB our_catalog عند غياب CSV.
  • يسجّل تحذيراً عند اختلاف العددين بشكل ملحوظ، لتنبيه المستخدم.
كل مكان يحتاج كتالوجنا ينبغي أن يستدعي load_our_catalog() بدل القراءة المباشرة.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import pandas as pd

log = logging.getLogger(__name__)


def _data_dir() -> str:
    return os.environ.get("DATA_DIR", "data")


def _csv_path() -> str:
    return os.path.join(_data_dir(), "our_catalog_saved.csv")


def _read_csv() -> Optional[pd.DataFrame]:
    p = _csv_path()
    if not os.path.exists(p):
        return None
    try:
        return pd.read_csv(p, dtype=str, keep_default_na=False)
    except Exception as e:
        log.warning("catalog_loader: CSV read failed: %s", e)
        return None


def _read_db() -> Optional[pd.DataFrame]:
    try:
        from utils.db_manager import get_db
        conn = get_db()
        try:
            return pd.read_sql("SELECT * FROM our_catalog", conn)
        finally:
            conn.close()
    except Exception as e:
        log.warning("catalog_loader: DB read failed: %s", e)
        return None


def load_our_catalog(prefer: str = "csv") -> pd.DataFrame:
    """يُعيد كتالوج متجرنا من المصدر الموحَّد (CSV افتراضياً، DB احتياطياً).
    يسجّل تحذيراً عند تباين ملحوظ بين المصدرين. يُعيد DataFrame (قد يكون فارغاً)."""
    csv_df = _read_csv()
    db_df = _read_db()

    n_csv = len(csv_df) if csv_df is not None else 0
    n_db = len(db_df) if db_df is not None else 0
    if n_csv and n_db and abs(n_csv - n_db) > max(20, 0.02 * max(n_csv, n_db)):
        log.warning("catalog_loader: تباين بين مصدري الكتالوج — CSV=%d, DB=%d "
                    "(يُستخدم %s). وحّد المصدرين لتفادي اختلاف نتائج المفقودات.",
                    n_csv, n_db, prefer.upper())

    primary, fallback = (csv_df, db_df) if prefer == "csv" else (db_df, csv_df)
    if primary is not None and not primary.empty:
        return primary
    if fallback is not None and not fallback.empty:
        return fallback
    return pd.DataFrame()
