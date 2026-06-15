"""
app.py - نظام التسعير الذكي مهووس v26.0
# SYSTEM STATUS: LOCKED & AUTONOMOUS — Fire and Forget Mode
✅ معالجة خلفية مع حفظ تلقائي
✅ جداول مقارنة بصرية في كل الأقسام
✅ أزرار AI + قرارات لكل منتج
✅ بحث أسعار السوق والمنافسين
✅ بحث mahwous.com للمنتجات المفقودة
✅ تحديث تلقائي للأسعار عند إعادة رفع المنافس
✅ تصدير Make لكل منتج وللمجموعات
✅ Gemini Chat مباشر
✅ فلاتر ذكية في كل قسم
✅ تاريخ جميل لكل العمليات
✅ محرك أتمتة ذكي مع قواعد تسعير قابلة للتخصيص (v26.0)
✅ لوحة تحكم الأتمتة متصلة بالتنقل (v26.0)
✅ محرك كشط غير متزامن (Async Scraper + Detached Process)
✅ فحص ذاتي عند الإقلاع (Health Check)
"""
import os as _os_early
import html as _html_mod
import sys as _sys_early

# ── حارس إصدار Python (حرج) ─────────────────────────────────────────
# Streamlit غير متوافق مع Python 3.14: يفشل عند خدمة الملفات الثابتة
# (TypeError: cannot create weak reference to 'NoneType' في anyio/asyncio)
# ويظهر «Internal Server Error» في المتصفح. شغّل دائماً على Python 3.11.
if _sys_early.version_info[:2] >= (3, 14):
    _v = ".".join(map(str, _sys_early.version_info[:3]))
    _msg = (
        "\n" + "=" * 70 + "\n"
        f"❌ إصدار Python غير مدعوم: {_v}\n"
        "   هذا التطبيق يتطلب Python 3.11 (Streamlit لا يعمل على 3.14+).\n"
        "   شغّله عبر:\n"
        '   & "C:\\Users\\Hp\\AppData\\Local\\Programs\\Python\\Python311\\python.exe"'
        " -m streamlit run app.py --server.port 8501\n"
        "   أو انقر run_app.bat\n"
        + "=" * 70 + "\n"
    )
    print(_msg, file=_sys_early.stderr, flush=True)
    raise SystemExit(_msg)
elif _sys_early.version_info[:2] != (3, 11):
    _v = ".".join(map(str, _sys_early.version_info[:3]))
    print(
        f"⚠️  تحذير: يُنصح بتشغيل هذا التطبيق على Python 3.11 (الحالي: {_v}).",
        file=_sys_early.stderr, flush=True,
    )

_os_early.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
_os_early.environ.setdefault("MKL_NUM_THREADS", "1")
_os_early.environ.setdefault("OMP_NUM_THREADS", "1")
_os_early.environ.setdefault("OPENBLAS_MAIN_FREE", "1")

import nest_asyncio
nest_asyncio.apply()

import concurrent.futures
import threading

import html
import json
import re
from urllib.parse import urlparse
import streamlit as st
import pandas as pd
import time
import uuid
from functools import partial
from datetime import datetime

try:
    from streamlit.runtime.scriptrunner import add_script_run_ctx
except ImportError:
    try:
        from streamlit.scriptrunner import add_script_run_ctx
    except ImportError:
        def add_script_run_ctx(t): return t

from config import *

# ── تجاوز SECTIONS لإضافة مصنع المنتجات وإعادة الترتيب (v26.0 UI Update) ──
SECTIONS = [
    "✨ مصنع المنتجات",
    "📊 لوحة التحكم",
    "🔴 سعر أعلى",
    "🟢 سعر أقل",
    "✅ موافق عليها",
    "🔍 منتجات مفقودة",
    "⚪ المستبعدة",
    "✅ تمت المعالجة",
    "🕷️ كشط المنافسين",
    "⚙️ الإعدادات",
]
from styles import (get_styles, vs_card, comp_strip, miss_card, miss_card_v2,
                    get_sidebar_toggle_js, lazy_img_tag, linked_product_title,
                    render_kpi_row, render_active_filter_chips_html,
                    render_changes_table, render_excluded_table,
                    render_precise_stats)
from engines.mahwous_core import validate_export_product_dataframe
from engines.engine import (read_file, run_full_analysis, find_missing_products,
                             smart_missing_barrier, prepare_missing_for_upload,
                             extract_brand, extract_size, extract_type, is_sample,
                             resolve_catalog_columns, detect_input_columns,
                             apply_user_column_map,
                             _first_image_url_from_row)
from engines.ai_engine import (call_ai, verify_match, analyze_product,
                                bulk_verify, suggest_price,
                                search_market_price, search_mahwous,
                                check_duplicate, ai_verify_dedup,
                                fetch_fragrantica_info, fetch_product_images,
                                generate_mahwous_description, _parse_seo_json_block,
                                reclassify_review_items, ai_deep_analysis,
                                generate_seo_description, generate_action_summary)
from engines.analysis_job_runner import run_analysis_background_job as _run_analysis_background
from engines.reconciliation_engine import (
    failed_rows_to_csv_bytes,
    failed_rows_to_xlsx_bytes,
    merge_reconciliation_into_audit,
    reconcile_competitor_upload,
)
from engines.file_reader import load_competitor_csv_for_matching
from engines.automation import (AutomationEngine, ScheduledSearchManager,
                                 auto_push_decisions, auto_process_review_items,
                                 log_automation_decision, get_automation_log,
                                 get_automation_stats)
from utils.helpers import (apply_filters, get_filter_options, export_to_excel,
                            export_multiple_sheets, parse_pasted_text,
                            safe_float, format_price, format_diff,
                            fetch_og_image_url, favicon_url_for_site,
                            fetch_page_title_from_url)
from utils.make_helper import (send_price_updates, send_new_products,
                                send_missing_products, send_single_product,
                                verify_webhook_connection, export_to_make_format,
                                send_batch_smart)
from utils.salla_shamel_export import (
    export_to_salla_shamel,
    export_to_salla_shamel_csv,
    verify_truly_missing,
    merge_competitor_uploads,
    SALLA_SHAMEL_COLUMNS,
)
from utils.product_analyzer import analyze_product_inline, render_analysis_result
from utils.filter_ui import (render_sidebar_filters, apply_global_filters,
                              get_active_filter_summary)
from utils.data_helpers import (safe_results_for_json, restore_results_from_json,
                                merge_missing_products_dataframes,
                                merge_price_analysis_dataframes,
                                ts_badge, decision_badge,
                                row_media_urls_from_analysis,
                                our_product_url_from_row,
                                competitor_product_url_from_row)
from utils.db_manager import (init_db, get_db, log_event, log_decision,
                               log_analysis, get_events, get_decisions,
                               get_analysis_history, upsert_price_history,
                               get_price_history, get_price_changes,
                               save_job_progress, get_job_progress, get_last_job,
                               any_running_job, release_stale_running_jobs,
                               save_hidden_product, get_hidden_product_keys,
                               init_db_v26, upsert_our_catalog, upsert_comp_catalog,
                               save_processed, get_processed, undo_processed,
                               get_processed_keys, migrate_db_v26,
                               upsert_competitor_products, get_competitor_products_df,
                               get_competitor_store_stats, init_competitor_store,
                               get_processed_hydration_sets, bulk_revert_processed,
                               # Task 3.3 — Soft Delete
                               soft_delete_product, get_soft_deleted_product_keys,
                               restore_soft_deleted_product, ensure_is_deleted_column,
                               apply_soft_deletes_to_df,
                               # Task 3.5 — Inline Edit
                               update_product_data, get_product_overrides, delete_product_override,
                               # Task 3.6 — Force Link
                               force_link_product, get_force_links, delete_force_link)

# ── استيراد صفحات الدمج (مع try/except لضمان عدم توقف التطبيق) ────────────
try:
    import pages.magic_factory as _magic_factory_mod
except Exception as _mf_import_err:
    _magic_factory_mod = None

_scraper_advanced_mod = None
_scraper_advanced_import_error = None


def _get_scraper_advanced_module():
    """
    تحميل كسول لأدوات الكشط المتقدمة.
    مهم جداً لنسخة Streamlit Cloud لأن تنفيذ أوامر واجهة عند الاستيراد المبكر
    قد يؤدي إلى رندر جزئي أو شاشة فارغة قبل اكتمال الصفحة الرئيسية.
    """
    global _scraper_advanced_mod, _scraper_advanced_import_error
    if _scraper_advanced_mod is not None:
        return _scraper_advanced_mod
    if _scraper_advanced_import_error is not None:
        return None
    try:
        import importlib
        _scraper_advanced_mod = importlib.import_module("pages.scraper_advanced")
        return _scraper_advanced_mod
    except Exception as _sa_import_err:
        _scraper_advanced_import_error = _sa_import_err
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def _cached_thumb_from_product_url(page_url: str) -> str:
    """صورة معاينة من صفحة المنتج عندما لا يوجد عمود صورة في الجدول المحفوظ."""
    u = (page_url or "").strip()
    if not u.startswith("http"):
        return ""
    og = fetch_og_image_url(u)
    if og:
        return og
    return favicon_url_for_site(u)


@st.cache_data(ttl=86400, show_spinner=False)
def _cached_title_from_product_url(page_url: str) -> str:
    """عنوان المنتج من og:title / <title> عندما يكون الاسم مخزّناً كرابط."""
    return fetch_page_title_from_url(page_url) or ""


def _norm_dup_text(s: str) -> str:
    """تطبيع اسم المنتج لمقارنة تكرار محلية أدق."""
    t = str(s or "").strip().lower()
    t = re.sub(r"(eau de parfum|eau de toilette|parfum|edp|edt|for men|for women)", " ", t, flags=re.I)
    t = re.sub(r"(للرجال|للنساء|رجالي|نسائي|او دي بارفان|او دو بارفان|او دي تواليت)", " ", t)
    t = re.sub(r"[^0-9a-z\u0600-\u06FF\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _dup_similarity(a: str, b: str) -> float:
    aa = set(_norm_dup_text(a).split())
    bb = set(_norm_dup_text(b).split())
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / max(len(aa), len(bb))


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict | None = None, run_id: str = "pre-fix") -> None:
    # region agent log
    try:
        payload = {
            "sessionId": "aea738",
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
        }
        with open("debug-aea738.log", "a", encoding="utf-8") as _fh:
            _fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # endregion


# ── إعداد الصفحة ──────────────────────────
st.set_page_config(page_title=APP_TITLE, page_icon=APP_ICON,
                   layout="wide", initial_sidebar_state="expanded")
st.markdown(get_styles(), unsafe_allow_html=True)
# إخفاء روابط التنقل التلقائية (app, magic factory, scraper advanced) من أعلى الشريط الجانبي
st.markdown("<style>[data-testid='stSidebarNav'] {display: none;}</style>", unsafe_allow_html=True)
st.markdown(get_sidebar_toggle_js(), unsafe_allow_html=True)
_debug_log("H1", "app.py:set_page_config", "App bootstrap reached", {"app_title": APP_TITLE})

# ── فحص ذاتي عند الإقلاع (يعمل مرة واحدة فقط لكل جلسة) ────────────────
if "health_check_done" not in st.session_state:
    try:
        from utils.health_check import run_system_diagnostics
        _hc = run_system_diagnostics()
        st.session_state["health_check_done"] = True
        st.session_state["health_status"] = {
            "ok": _hc.ok,
            "warnings": _hc.warnings,
            "errors":   _hc.errors,
            "details":  _hc.details,
        }
    except Exception as _hce:
        st.session_state["health_check_done"] = True
        st.session_state["health_status"] = {
            "ok": True, "warnings": [], "errors": [], "details": {}
        }

# ── تشغيل خيط المجدول التلقائي (مرة واحدة عند أول تشغيل للبيئة) ─────────
if "scheduler_started" not in st.session_state:
    try:
        from scrapers.scheduler import start_scheduler_thread
        start_scheduler_thread()
        st.session_state["scheduler_started"] = True
    except Exception:
        st.session_state["scheduler_started"] = False

# أخطاء حرجة فقط تُعرض عالمياً (مثل DB تالفة) — التحذيرات تُعرض في الشريط الجانبي
_hs = st.session_state.get("health_status", {})
for _hc_err in _hs.get("errors", []):
    st.error(f"⚠️ فحص النظام: {_hc_err}")
try:
    if "_db_ready" not in st.session_state:
        init_db()
        init_db_v26()
        migrate_db_v26()  # v26.0 — ترحيل آمن (idempotent)
        init_competitor_store()
        # تحميل المنافسين تلقائياً من JSON عند أول تشغيل (ذاكرة جديدة)
        from utils.db_manager import register_competitors_from_json
        register_competitors_from_json()
        st.session_state["_db_ready"] = True
except Exception as e:
    st.error(f"Database Initialization Error: {e}")

# ── Session State ─────────────────────────
_defaults = {
    "results": None, "missing_df": None, "analysis_df": None,
    "job_id": None, "job_running": False,
    "decisions_pending": {},   # {product_name: action}
    "our_df": None, "comp_dfs": None,  # حفظ الملفات للمنتجات المفقودة
    "hidden_products": set(),  # منتجات أُرسلت لـ Make أو أُزيلت
    "nav_flash": None,    # رسالة انتقال سريعة من أزرار لوحة التحكم
    "last_audit_stats": None,  # عدادات تدقيق من run_full_analysis
    "reconciliation_report": None,
    "reconciliation_failed_csv": None,
    "_action_toast": None, # رسالة نجاح/فشل Callback تُعرض كـ toast
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v
st.session_state.setdefault("processed_price_skus", set())  # FIX: Smart Workflow & AI Tracking
st.session_state.setdefault("processed_missing_urls", set())  # FIX: Smart Workflow & AI Tracking
# FIX: Relaxed Constraints — التراكم دائم افتراضياً لحماية النتائج السابقة من الفقد.
st.session_state.setdefault("dash_accumulate_results", True)

# ── مسار حفظ الكتالوج التلقائي ──
import os as _os_cat
_OUR_CATALOG_PATH = _os_cat.path.join(_os_cat.environ.get("DATA_DIR", "data"), "our_catalog_saved.csv")


@st.cache_data(show_spinner=False)
def _load_our_catalog_cached(path: str, _mtime: float) -> pd.DataFrame:
    """تحميل كتالوجنا مرة واحدة (مُخبّأ) + إسقاط الأعمدة الضخمة غير اللازمة.

    عمود «رابط المنتج» في الملف المحفوظ يحوي وصف HTML تالفاً (~206MB!) لا روابط؛
    إسقاطه + أعمدة المتغيّرات [1]/[2]/[3] يقلّص الكتالوج من ~226MB إلى ~20MB،
    فيخفّ session_state بشدة (إقلاع أسرع + نقل أخف + تفاعل أسرع). _mtime يُبطل
    الكاش تلقائياً عند تغيّر الملف.
    """
    # تجاهل الأعمدة الضخمة عند القراءة نفسها (usecols) — يخفّض ذروة الذاكرة وزمن القراءة
    def _keep(col):
        c = str(col)
        return not (c == "رابط المنتج" or c.startswith("["))
    try:
        _df = pd.read_csv(path, encoding="utf-8-sig", usecols=_keep)
    except Exception:
        # fallback: اقرأ الكل ثم أسقط (لو فشل usecols لأي سبب)
        _df = pd.read_csv(path, encoding="utf-8-sig")
        _df = _df.drop(columns=[c for c in _df.columns
                                if c == "رابط المنتج" or str(c).startswith("[")],
                       errors="ignore")
    return _df


@st.cache_data(show_spinner=False)
def load_our_descriptions(_mtime: float = 0.0) -> dict:
    """أوصاف مهووس الحقيقية لمنتجاتنا — تُحمَّل عند الطلب فقط (مُخبّأة، خارج session_state).

    ⚠️ مكان البيانات: عمود «رابط المنتج» في our_catalog_saved.csv يحوي فعلياً
    وصف HTML بأسلوب مهووس (لا روابط) — وهو ثقيل (~206MB) لذا أُسقط من الكتالوج
    في الجلسة. هذه الدالة تستعيده عند الحاجة فقط:
      • ملف تصدير المفقودات (شرط 3): أسلوب الوصف المرجعي.
      • تدريب/توجيه الـAI لتوليد أوصاف بنفس أسلوب مهووس لاحقاً.

    يُعيد dict: {الاسم_المطبّع: وصف_HTML} (مفتاحان: «المنتج» و«اسم المنتج»).
    """
    import os as _d_os
    from engines.engine import normalize_name as _nn
    _path = _d_os.path.join(_d_os.environ.get("DATA_DIR", "data"), "our_catalog_saved.csv")
    if not _d_os.path.exists(_path):
        return {}
    _desc_col = "رابط المنتج"
    try:
        _cols = pd.read_csv(_path, encoding="utf-8-sig", nrows=0).columns.tolist()
    except Exception:
        return {}
    _name_cols = [c for c in ("المنتج", "اسم المنتج") if c in _cols]
    if _desc_col not in _cols or not _name_cols:
        return {}
    try:
        _d = pd.read_csv(_path, encoding="utf-8-sig", usecols=_name_cols + [_desc_col])
    except Exception:
        return {}
    _out: dict = {}
    for _, _r in _d.iterrows():
        _desc = str(_r.get(_desc_col, "") or "").strip()
        if not _desc or "<" not in _desc:   # وصف HTML فعلي فقط
            continue
        for _nc in _name_cols:
            _nm = str(_r.get(_nc, "") or "").strip()
            if _nm:
                _out.setdefault(_nn(_nm), _desc)
    return _out


# ── تحميل الكتالوج المحفوظ تلقائياً (مُخبّأ + رشيق) ──
if st.session_state.get("our_df") is None and _os_cat.path.exists(_OUR_CATALOG_PATH):
    try:
        _saved_cat = _load_our_catalog_cached(_OUR_CATALOG_PATH, _os_cat.path.getmtime(_OUR_CATALOG_PATH))
        if _saved_cat is not None and not _saved_cat.empty:
            st.session_state.our_df = _saved_cat
    except Exception:
        pass

# تحميل المنتجات المخفية من قاعدة البيانات — مرة واحدة فقط عند بدء الجلسة.
# ⚡ نُقل استعلام DB داخل الحارس: _db_hidden كان يُستعلَم كل rerun ثم يُهمَل
# (لا يُستخدم خارج هذه الكتلة)، فالنقل يحفظ السلوك تماماً ويزيل استعلاماً لكل تفاعل.
if "_hidden_hydrated" not in st.session_state:
    _db_hidden = get_hidden_product_keys()
    st.session_state.hidden_products = st.session_state.hidden_products | _db_hidden
    st.session_state["_hidden_hydrated"] = True

# ── Phase 1: ترطيب حالة المعالجة من DB لتستمر عبر إعادة التشغيل ──
# يُنفَّذ مرة واحدة فقط (أول rerun بعد بدء الجلسة)
if not st.session_state.get("_processed_hydrated"):
    _hp_ids, _hp_urls, _hp_price_map = get_processed_hydration_sets()
    st.session_state["processed_price_skus"] |= _hp_ids
    st.session_state["processed_missing_urls"] |= _hp_urls
    st.session_state["_processed_price_map"] = _hp_price_map  # {pid: last_sent_price}
    st.session_state["_processed_hydrated"] = True
else:
    st.session_state.setdefault("_processed_price_map", {})

# تنقل من أزرار لوحة التحكم — يُطبَّق هنا قبل `st.radio(..., key="main_nav")` في الشريط الجانبي
# (Streamlit يمنع تعيين st.session_state.main_nav بعد إنشاء الودجت في نفس التشغيل)
_nav_apply = st.session_state.pop("_nav_pending", None)
if _nav_apply and _nav_apply in SECTIONS:
    st.session_state.main_nav = _nav_apply

# ════════════════════════════════════════════════
#  دوال المعالجة — يجب تعريفها قبل استخدامها
# ════════════════════════════════════════════════
# «الإرجاع الذكي»: إعادة منتج مُعالَج (مُرسَل لـ Make) إلى قسمه السابق عند انخفاض سعر
# المنافس تحت آخر سعر أرسلتَه. مطفأ افتراضياً (طلب المستخدم): المُعالَج يبقى في «تمت
# المعالجة» ولا يعود. فعّله (True) فقط إن أردت إعادة التقييم التلقائي عند هبوط المنافس.
_REEVAL_PROCESSED_ON_PRICE_DROP = False


def _split_results(df):
    """تقسيم نتائج التحليل على الأقسام بأمان تام."""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        empty = pd.DataFrame()
        return {
            "price_raise": empty.copy(),
            "price_lower": empty.copy(),
            "approved": empty.copy(),
            "review": empty.copy(),
            "excluded": empty.copy(),
            "all": empty.copy(),
        }

    work = df.copy()
    if "القرار" not in work.columns:
        work["القرار"] = ""
    work["القرار"] = work["القرار"].fillna("").astype(str).str.strip()

    # ── Phase 1: Smart Reversion ─────────────────────────────────
    # Vectorized check: for each processed product in the new results,
    # if the competitor price has dropped below our last-sent price → revert it.
    # O(N) via set lookup + pandas vectorized isin/merge — no row-level loops.
    _price_map = st.session_state.get("_processed_price_map", {})
    _proc_skus = st.session_state.get("processed_price_skus", set())
    if (_REEVAL_PROCESSED_ON_PRICE_DROP and _price_map and _proc_skus
            and "معرف_المنتج" in work.columns and "سعر_المنافس" in work.columns):
        _pid_col = work["معرف_المنتج"].astype(str).str.strip()
        _is_processed = _pid_col.isin(_proc_skus)
        if _is_processed.any():
            _processed_slice = work.loc[_is_processed].copy()
            # Map each processed product_id → the price we last sent to Make
            _processed_slice["_last_sent_price"] = _processed_slice["معرف_المنتج"].astype(str).str.strip().map(_price_map).fillna(0.0)
            _processed_slice["_comp_price_now"] = pd.to_numeric(_processed_slice["سعر_المنافس"], errors="coerce").fillna(0.0)
            # Reversion condition: competitor dropped price BELOW what we last sent
            _revert_mask = (
                (_processed_slice["_last_sent_price"] > 0)
                & (_processed_slice["_comp_price_now"] > 0)
                & (_processed_slice["_comp_price_now"] < _processed_slice["_last_sent_price"])
            )
            _revert_pids = set(_processed_slice.loc[_revert_mask, "معرف_المنتج"].astype(str).str.strip().tolist())
            if _revert_pids:
                # Remove from session tracking sets
                st.session_state["processed_price_skus"] -= _revert_pids
                for _rpid in _revert_pids:
                    st.session_state.get("_processed_price_map", {}).pop(_rpid, None)
                # Remove from session hidden_products (keys matching the pid)
                _keys_to_unhide = {
                    k for k in st.session_state.get("hidden_products", set())
                    if any(k.endswith(f"_{pid}") or pid in k for pid in _revert_pids)
                }
                st.session_state["hidden_products"] -= _keys_to_unhide
                # Bulk revert from persistent DB (single query, O(N) set ops)
                _all_proc_keys = get_processed_keys()
                _db_keys_to_revert = [
                    pk for pk in _all_proc_keys
                    if any(pid in pk for pid in _revert_pids)
                ]
                if _db_keys_to_revert:
                    bulk_revert_processed(_db_keys_to_revert)
                # FIX (cond.8): المنافس هبط تحت سعرنا المُرسَل ⇒ صار أرخص منّا ⇒
                # نحن الآن «أعلى» ⇒ يجب أن يعود المنتج إلى قسم «🔴 سعر أعلى»
                # (حيث يتّخذ المستخدم إجراء خفض سعرنا)، لا «سعر أقل».
                _revert_idx = _processed_slice.loc[_revert_mask].index
                work.loc[_revert_idx, "القرار"] = "🔴 سعر أعلى — مراجعة تلقائية (Smart Reversion)"
                # Toast notification (consumed once)
                st.session_state["_action_toast"] = (
                    "warning",
                    f"⚠️ Smart Reversion: أُعيد {len(_revert_pids)} منتج إلى '🔴 سعر أعلى' "
                    "بسبب انخفاض سعر المنافس تحت سعرك المُرسَل"
                )
    # ── End Smart Reversion ───────────────────────────────────────

    def _contains(txt):
        try:
            return work["القرار"].str.contains(txt, na=False, regex=False)
        except Exception:
            return pd.Series([False] * len(work), index=work.index)

    # ── v33: Safety Net — أي منتج بقرار غير معروف يذهب لـ "مستبعد" بدل الضياع ──
    # v34: تصنيف حصري — كل منتج يذهب لقسم واحد فقط
    _dec = work["القرار"].fillna("").str.strip()
    price_raise = work[_dec.str.startswith("🔴")]
    price_lower = work[_dec.str.startswith("🟢") | _dec.str.contains("سعر أقل", na=False, regex=False)]
    approved    = work[_dec.str.startswith("✅")]
    review      = work[_dec.str.startswith("⚠️") | _dec.str.startswith("🔍")]
    excluded    = work[_dec.str.startswith("⚪")]

    # جمع كل المنتجات المُوزَّعة
    _distributed_idx = set()
    for _sec_df in [price_raise, price_lower, approved, review, excluded]:
        _distributed_idx.update(_sec_df.index.tolist())

    # المنتجات التي لم تُوزَّع على أي قسم (قرار فارغ/غير معروف)
    _orphan_mask = ~work.index.isin(_distributed_idx)
    _orphans = work[_orphan_mask]
    if not _orphans.empty:
        # ألحقها بـ "مستبعد" لمنع فقدان البيانات
        excluded = pd.concat([excluded, _orphans], ignore_index=False)

    result = {
        "price_raise": price_raise.reset_index(drop=True),
        "price_lower": price_lower.reset_index(drop=True),
        "approved":    approved.reset_index(drop=True),
        "review":      review.reset_index(drop=True),
        "excluded":    excluded.reset_index(drop=True),
        "all":         work.reset_index(drop=True),
    }

    # ── مؤشر الشفافية: تحقق أن لا منتج ضاع ──
    _total_in = len(work)
    _total_out = sum(len(result[k]) for k in result if k != "all")
    if _total_out < _total_in:
        try:
            st.toast(f"⚠️ تحذير: {_total_in - _total_out} منتج لم يُوزَّع!", icon="⚠️")
        except Exception:
            pass

    return result


def _auto_resolve_review(results: dict) -> dict:
    """
    حسم سلة review آلياً عبر reclassify_review_items (دفعات 30).
    - أعلى/أقل/موافق → يوزّع على السلال الأربع
    - مفقود / تحت المراجعة / فشل AI → excluded (سجل داخلي)
    النتيجة: صفر صفوف في review.
    """
    import logging as _log_resolve
    review_df = results.get("review", pd.DataFrame())
    if review_df.empty:
        return results

    total_review = len(review_df)
    resolved_to_raise = 0
    resolved_to_lower = 0
    resolved_to_approved = 0
    resolved_to_excluded = 0

    # v34: محاولة تحليل AI أولاً (أكثر دقة)
    try:
        from engines.ai_engine import auto_resolve_review_v2
        ai_results = auto_resolve_review_v2(review_df, batch_size=5)
        if ai_results:
            for idx, ai_res in ai_results.items():
                if idx in review_df.index and ai_res.get("confidence", 0) >= 75:
                    row = review_df.loc[idx].copy()
                    dec = ai_res["decision"]
                    if "أعلى" in dec or dec.startswith("🔴"):
                        row["القرار"] = f"🔴 سعر أعلى (AI {ai_res['confidence']}%)"
                        results["price_raise"] = pd.concat(
                            [results["price_raise"], row.to_frame().T], ignore_index=True)
                        resolved_to_raise += 1
                    elif "أقل" in dec or dec.startswith("🟢"):
                        row["القرار"] = f"🟢 سعر أقل (AI {ai_res['confidence']}%)"
                        results["price_lower"] = pd.concat(
                            [results["price_lower"], row.to_frame().T], ignore_index=True)
                        resolved_to_lower += 1
                    elif "موافق" in dec or dec.startswith("✅"):
                        row["القرار"] = f"✅ موافق (AI {ai_res['confidence']}%)"
                        results["approved"] = pd.concat(
                            [results["approved"], row.to_frame().T], ignore_index=True)
                        resolved_to_approved += 1
                    elif "مستبعد" in dec or dec.startswith("⚪"):
                        row["القرار"] = f"⚪ مستبعد (AI: {ai_res['reason'][:50]})"
                        results["excluded"] = pd.concat(
                            [results["excluded"], row.to_frame().T], ignore_index=True)
                        resolved_to_excluded += 1
                    # إزالة من review
                    review_df = review_df.drop(idx)
    except Exception as e:
        import logging
        logging.warning(f"auto_resolve_review_v2 failed: {e}")

    # تحديث الإجمالي بعد حسم AI (المتبقي يُمرّر للحسم بالدفعات)
    total_review = len(review_df)
    if review_df.empty:
        results["review"] = pd.DataFrame()
        results["all"] = pd.concat([
            results.get("price_raise", pd.DataFrame()),
            results.get("price_lower", pd.DataFrame()),
            results.get("approved", pd.DataFrame()),
            results.get("review", pd.DataFrame()),
            results.get("excluded", pd.DataFrame()),
        ], ignore_index=True)
        _log_resolve.info(
            "AUTO_RESOLVE_REVIEW (AI only): raise=%d, lower=%d, approved=%d, excluded=%d",
            resolved_to_raise, resolved_to_lower, resolved_to_approved, resolved_to_excluded,
        )
        return results

    BATCH_SIZE = 30
    all_rows = review_df.reset_index(drop=True)

    for batch_start in range(0, total_review, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_review)
        batch_df = all_rows.iloc[batch_start:batch_end]

        # بناء قائمة المدخلات بصيغة reclassify_review_items
        batch_items = []
        for _, row in batch_df.iterrows():
            batch_items.append({
                "our": str(row.get("المنتج", "")),
                "comp": str(row.get("منتج_المنافس", "")),
                "our_price": float(row.get("السعر", 0) or 0),
                "comp_price": float(row.get("سعر_المنافس", 0) or 0),
            })

        # استدعاء AI بالدفعة
        try:
            rc_results = reclassify_review_items(batch_items)
        except Exception:
            rc_results = []

        # بناء خريطة idx → section من نتائج AI
        resolved_map = {}  # idx (1-based) → section string
        for rc in rc_results:
            try:
                idx = int(rc.get("idx", 0) or 0)
            except Exception:
                idx = 0
            if 1 <= idx <= len(batch_items):
                resolved_map[idx] = rc.get("section", "")

        # توزيع كل صف في الدفعة
        for local_i, (_, row) in enumerate(batch_df.iterrows()):
            ai_section = resolved_map.get(local_i + 1, "")
            row_copy = row.copy()

            if "أعلى" in ai_section:
                row_copy["القرار"] = "🔴 سعر أعلى"
                results["price_raise"] = pd.concat(
                    [results["price_raise"], row_copy.to_frame().T], ignore_index=True)
                resolved_to_raise += 1
            elif "أقل" in ai_section:
                row_copy["القرار"] = "🟢 سعر أقل"
                results["price_lower"] = pd.concat(
                    [results["price_lower"], row_copy.to_frame().T], ignore_index=True)
                resolved_to_lower += 1
            elif "موافق" in ai_section:
                row_copy["القرار"] = "✅ موافق"
                results["approved"] = pd.concat(
                    [results["approved"], row_copy.to_frame().T], ignore_index=True)
                resolved_to_approved += 1
            else:
                # مفقود / تحت المراجعة / فشل AI / أي شيء آخر → excluded
                row_copy["القرار"] = "⚪ مستبعد — حسم آلي: ليس نفس المنتج"
                results["excluded"] = pd.concat(
                    [results["excluded"], row_copy.to_frame().T], ignore_index=True)
                resolved_to_excluded += 1

    # إفراغ سلة review
    results["review"] = pd.DataFrame()

    # تحديث all بعد إعادة التوزيع
    results["all"] = pd.concat([
        results.get("price_raise", pd.DataFrame()),
        results.get("price_lower", pd.DataFrame()),
        results.get("approved", pd.DataFrame()),
        results.get("review", pd.DataFrame()),
        results.get("excluded", pd.DataFrame()),
    ], ignore_index=True)

    _log_resolve.info(
        "AUTO_RESOLVE_REVIEW: total=%d → raise=%d, lower=%d, approved=%d, excluded=%d",
        total_review, resolved_to_raise, resolved_to_lower,
        resolved_to_approved, resolved_to_excluded,
    )
    return results


def _reconciliation_check(results: dict) -> dict:
    """
    تحقّق حفظ البيانات:
    1. gap: len(all) == sum(price_raise + price_lower + approved + excluded + review)
    2. duplicate: لا تكرار بين الأقسام السعرية والمفقود
    3. consistency: عدد excluded يساوي عدد missing
    """
    import logging as _log_rc
    all_count = len(results.get("all", pd.DataFrame()))
    bucket_counts = {
        "price_raise": len(results.get("price_raise", pd.DataFrame())),
        "price_lower": len(results.get("price_lower", pd.DataFrame())),
        "approved": len(results.get("approved", pd.DataFrame())),
        "excluded": len(results.get("excluded", pd.DataFrame())),
        "review": len(results.get("review", pd.DataFrame())),
    }
    sum_buckets = sum(bucket_counts.values())
    gap = all_count - sum_buckets

    # ── شرط عدم التكرار: لا منتج منافس في قسم سعري وفي مفقود معاً ──
    duplicate_count = 0
    duplicate_details = []
    try:
        # جمع معرّفات المنافسين في الأقسام السعرية
        price_dfs = []
        for k in ("price_raise", "price_lower", "approved"):
            _df = results.get(k, pd.DataFrame())
            if isinstance(_df, pd.DataFrame) and not _df.empty:
                price_dfs.append(_df)
        if price_dfs:
            price_all = pd.concat(price_dfs, ignore_index=True)
        else:
            price_all = pd.DataFrame()

        missing_df = results.get("missing", pd.DataFrame())

        if not price_all.empty and isinstance(missing_df, pd.DataFrame) and not missing_df.empty:
            # بناء مجموعة مفاتيح للأقسام السعرية (اسم المنافس المطبّع)
            price_keys = set()
            if "منتج_المنافس" in price_all.columns:
                price_keys = set(
                    price_all["منتج_المنافس"].fillna("").astype(str)
                    .str.strip().str.lower()
                    .loc[lambda s: (s != "") & (s != "nan") & (~s.str.startswith("❌"))]
                    .tolist()
                )

            # مفاتيح المفقودات
            missing_keys = set()
            if "منتج_المنافس" in missing_df.columns:
                missing_keys = set(
                    missing_df["منتج_المنافس"].fillna("").astype(str)
                    .str.strip().str.lower()
                    .loc[lambda s: (s != "") & (s != "nan")]
                    .tolist()
                )

            overlap = price_keys & missing_keys
            duplicate_count = len(overlap)
            if overlap:
                duplicate_details = sorted(list(overlap))[:10]
                _log_rc.warning(
                    "DUPLICATE_CHECK: %d competitor products in both price sections AND missing: %s",
                    duplicate_count, duplicate_details[:5],
                )
    except Exception as _dup_err:
        _log_rc.warning("DUPLICATE_CHECK error: %s", _dup_err)

    # ── شرط اتساق المصدرين: excluded (أيتام) vs missing count ──
    # excluded يحتوي المفقود (missing) + ما حُسم آلياً من review كمستبعد،
    # لذا الشرط الصحيح: excluded_count >= missing_count (وليس المساواة).
    excluded_count = bucket_counts["excluded"]
    missing_count = len(results.get("missing", pd.DataFrame()))
    sources_consistent = (excluded_count >= missing_count)

    check = {
        "all_count": all_count,
        "sum_buckets": sum_buckets,
        "gap": gap,
        "gap_ok": gap == 0,
        "bucket_counts": bucket_counts,
        "duplicate_count": duplicate_count,
        "duplicate_details": duplicate_details,
        "duplicate_ok": duplicate_count == 0,
        "excluded_count": excluded_count,
        "missing_count": missing_count,
        "sources_consistent": sources_consistent,
    }

    if gap != 0:
        _log_rc.warning("DATA_CONSERVATION gap=%d: all=%d, sum=%d, buckets=%s",
                        gap, all_count, sum_buckets, bucket_counts)
    else:
        _log_rc.info("DATA_CONSERVATION OK: all=%d == sum=%d", all_count, sum_buckets)

    return check



_MISS_STOP = set(
    "عطر عينه عينة تستر سامبل ماء او دو دي بارفيوم برفيوم بارفان تواليت توالت "
    "كولونيا كولن مل غرام للرجال للنساء رجالي نسائي".split()
)


def _miss_bare(nm: str) -> str:
    """اسم مجرّد للمطابقة: تطبيع + إزالة الكلمات الشائعة/الأرقام/القصيرة."""
    import re as _re
    from engines.engine import normalize_name as _nn
    return " ".join(
        t for t in _nn(str(nm)).split()
        if t not in _MISS_STOP and not _re.fullmatch(r"\d+", t) and len(t) >= 2
    )


def _miss_toks(bare: str) -> list:
    """أهم 4 كلمات دالّة (≥4 أحرف) للحجب (blocking)."""
    return [t for t in bare.split() if len(t) >= 4][:4]


# هيكل عظمي عربي للحجب — يلتقط النسخ الإملائية المختلفة لنفس المنتج
# (كاشريل↔كاشاريل، ديبتك↔ديبتيك، خنجرعمان↔خنجر عمان) التي يفوتها الحجب بالكلمات
# الحرفية فتظهر كمفقودة وهي مملوكة. للحجب فقط — قرار الإخفاء يبقى على token_set + الحجم.
_MISS_AR_WEAK = str.maketrans("", "", "اويهءأإآةىؤئ")


def _ar_skeleton(tok: str) -> str:
    """يزيل الحروف العربية الضعيفة المتغيّرة إملائياً من الكلمة (اللاتيني يبقى كما هو)."""
    sk = str(tok).translate(_MISS_AR_WEAK)
    return sk if len(sk) >= 2 else str(tok)


def _skel_toks(bare: str) -> list:
    """كلمات الحجب بالهيكل العظمي (≥3 أحرف بعد التجريد) — أعلى 6."""
    _out = []
    for _t in bare.split():
        _sk = _ar_skeleton(_t)
        if len(_sk) >= 3 and _sk not in _out:
            _out.append(_sk)
        if len(_out) >= 6:
            break
    return _out


# ═══ v33: حماية التوافق الخلفي للمفقودات ═══
def _ensure_competitor_details(df: pd.DataFrame) -> pd.DataFrame:
    """
    يضمن وجود عمود تفاصيل_المنافسين — يبنيه من الأعمدة القديمة إذا لم يكن موجوداً.
    يُستدعى مرة واحدة بعد كل تحميل لـ missing_df.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return df
    # ── حالة 1: العمود موجود لكن كنص JSON (تحميل من cache/DB) ──
    if "تفاصيل_المنافسين" in df.columns:
        _nn = df["تفاصيل_المنافسين"].dropna()
        _sample = _nn.iloc[0] if not _nn.empty else None
        if isinstance(_sample, str):
            import json as _json_compat
            def _parse_details(x):
                if isinstance(x, list):
                    return x
                if isinstance(x, str) and x.strip().startswith("["):
                    try:
                        return _json_compat.loads(x)
                    except Exception:
                        return []
                return []
            df["تفاصيل_المنافسين"] = df["تفاصيل_المنافسين"].apply(_parse_details)
        # حساب العدد إذا مفقود
        if "عدد_المنافسين" not in df.columns:
            df["عدد_المنافسين"] = df["تفاصيل_المنافسين"].apply(
                lambda x: len(x) if isinstance(x, list) else 1
            )
        return df
    # ── حالة 2: عمود غير موجود (بيانات قديمة) → بناء من الأعمدة الموجودة ──
    def _build_from_old(row):
        base = [{
            "المنافس":    str(row.get("المنافس", "") or ""),
            "اسم_المنتج": str(row.get("منتج_المنافس", "") or ""),
            "السعر":      float(row.get("سعر_المنافس", 0) or 0),
            "الصورة":     str(row.get("صورة_المنافس", "") or ""),
            "الرابط":     str(row.get("رابط_المنافس", "") or ""),
            "الحجم":      str(row.get("الحجم", "") or ""),
            "النوع":      str(row.get("النوع", "") or ""),
            "المعرف":     str(row.get("معرف_المنافس", "") or ""),
        }]
        return base
    df["تفاصيل_المنافسين"] = df.apply(_build_from_old, axis=1)
    df["عدد_المنافسين"] = 1
    # حساب أعمدة السعر المساعدة
    if "أقل_سعر" not in df.columns:
        df["أقل_سعر"] = pd.to_numeric(df.get("سعر_المنافس", 0), errors="coerce").fillna(0)
        df["أعلى_سعر"] = df["أقل_سعر"]
        df["متوسط_السعر"] = df["أقل_سعر"]
    return df


def _clean_for_export(df: pd.DataFrame) -> pd.DataFrame:
    """يحذف الأعمدة غير القابلة للتسلسل قبل التصدير."""
    if not isinstance(df, pd.DataFrame):
        return df
    _drop = ["تفاصيل_المنافسين", "درجة_الأولوية", "مستوى_الأولوية",
             "أقل_سعر", "أعلى_سعر", "متوسط_السعر", "عدد_المنافسين"]
    return df.drop(columns=[c for c in _drop if c in df.columns], errors="ignore")


@st.cache_data(show_spinner=False, ttl=1800)
def _compute_missing_from_store(_our_sig: str = "") -> pd.DataFrame:
    """يحسب المنتجات المفقودة الحقيقية من المخزن الدائم (مستقل عن الوظيفة الهشّة).

    خط أنابيب الدقة (يصحّح تضخّم البصمة وإيجابياتها الكاذبة):
      1) مرشّحون سريعون: CompetitorIntelligence.find_missing_products (بصمة O(1)).
      2) إزالة تكرار المتاجر: دمج بالاسم المجرّد (يطوي التستر/الحجم/الصياغة)،
         مع تتبّع أرخص سعر + عدد المتاجر.
      3) طبقة تحقّق ضبابية محجوبة بالكلمات (token-blocking عبر فهرس مقلوب):
         كل مرشّح يُقارَن ضبابياً فقط مع منتجاتنا التي تشترك معه بكلمة دالّة.
         إن وُجد تشابه ≥ العتبة ⇒ نملكه باسم مختلف ⇒ ليس مفقوداً.
      ⇒ النتيجة: مفقودات فريدة حقيقية (لا تضخّم البصمة)، في ثوانٍ معدودة.

    _our_sig: توقيع للكاش فقط. يُعيد DataFrame بمخطّط صفحة المفقودة.
    """
    import os as _cm_os
    from rapidfuzz import fuzz as _fz, process as _pr
    _TH = 82  # عتبة «نملكه» (مثبتة بتحقّق عيّنة يدوي: 0 إيجابيات كاذبة)
    # 1) كتالوجنا: من الجلسة إن وُجد، وإلا من الملف المحفوظ
    our_df = st.session_state.get("our_df")
    if not isinstance(our_df, pd.DataFrame) or our_df.empty:
        _cat_path = _cm_os.path.join(_cm_os.environ.get("DATA_DIR", "data"), "our_catalog_saved.csv")
        if not _cm_os.path.exists(_cat_path):
            return pd.DataFrame()
        with open(_cat_path, "rb") as _fh:
            class _NB(io.BytesIO):
                name = "our_catalog_saved.csv"
            _res = read_file(_NB(_fh.read()))
        our_df = _res[0] if isinstance(_res, tuple) else _res
    if not isinstance(our_df, pd.DataFrame) or our_df.empty:
        return pd.DataFrame()
    # مرشّحون من البصمة
    _db = _cm_os.path.join(_cm_os.environ.get("DATA_DIR", "data"), "pricing_v18.db")
    if not _cm_os.path.exists(_db):
        return pd.DataFrame()
    try:
        from engines.competitor_intelligence import CompetitorIntelligence as _CIm
        _ci = _CIm(db_path=_db)
        _prods, _total = _ci.find_missing_products(our_df, page=0, per_page=1000000)
    except Exception:
        return pd.DataFrame()
    if not _prods:
        return pd.DataFrame()
    # عمود اسم منتجاتنا
    _ncol = None
    for _c in our_df.columns:
        if any(k in str(_c) for k in ("اسم", "المنتج", "name", "product")):
            _ncol = _c
            break
    if _ncol is None:
        _ncol = our_df.columns[0]
    # دوال التصنيف/الماركة (إثراء الماركات أولاً لملء العربية قبل استخراج ماركاتنا)
    from engines.engine import (is_sample as _is_sample, is_tester as _is_tester,
                                 classify_product_category as _classify_cat,
                                 extract_brand as _extract_brand, enrich_known_brands as _enrich,
                                 classify_product as _classify_prod, extract_size as _extract_size,
                                 normalize as _normalize, extract_brand_fast as _brand_fast)
    try:
        _enrich(db_path=_db)  # يملأ KNOWN_BRANDS بماركات المنافسين (عربي+إنجليزي)
    except Exception:
        pass
    # فهرس منتجاتنا الغني: عناصر + فهرس مقلوب بالكلمة + فهرس بالماركة (للحجب الموسّع)
    _our_items: list = []          # [{bare, brand_n, size}]
    _inv: dict = {}                # كلمة دالّة → مجموعة فهارس عناصرنا
    _skel_idx: dict = {}           # كلمة بالهيكل العظمي → فهارس (يلتقط اختلاف الإملاء)
    _brand_idx: dict = {}          # ماركة مطبَّعة → قائمة فهارس عناصرنا
    for _onm in our_df[_ncol].dropna().astype(str):
        _ob = _miss_bare(_onm)
        if not _ob:
            continue
        _idx = len(_our_items)
        # حجب بالماركة: نستخدم النسخة السريعة (المرحلة المباشرة) — قانونية ومتّسقة الطرفين
        _br_n = _normalize(_brand_fast(_onm) or "")
        _our_items.append({"bare": _ob, "brand_n": _br_n,
                           "size": _extract_size(_onm), "raw": _onm})
        for _t in _miss_toks(_ob):
            _inv.setdefault(_t, set()).add(_idx)
        for _t in _skel_toks(_ob):
            _skel_idx.setdefault(_t, set()).add(_idx)
        if _br_n:
            _brand_idx.setdefault(_br_n, []).append(_idx)
    # 2) دمج المرشّحين بالاسم المجرّد (إزالة تكرار المتاجر/الحجم/الصياغة)
    _cand: dict = {}
    for p in _prods:
        _bb = _miss_bare(p.get("product_name", ""))
        if not _bb:
            continue
        _price = float(p.get("min_price", 0) or 0)
        _ex = _cand.get(_bb)
        if _ex is None or _price < _ex[1]:
            _cand[_bb] = (p, _price)

    # فلاتر الدقة (نفس منطق find_missing_products) — المسار الحيّ كان يفتقدها
    # فيتسرّب إليه غير العطور/المجموعات/الأسعار المتطرفة.
    _BAD_CLASSES_LIVE = ('deodorant', 'hair_mist', 'body_mist', 'body_lotion',
                         'soap', 'shower_gel', 'after_shave', 'rejected', 'other')
    _SET_WORDS_LIVE = ('مجموعة', 'مجموعه', 'طقم', 'gift set', 'gift box', 'set ')
    _drop_class = _drop_set = _drop_price = _drop_short = 0
    _drop_nosize = _drop_mini = 0
    # عتبة الحجم الأدنى: عطر < 10مل = ميني/عيّنة → ليس منتجاً رئيسياً نفتقده
    _MIN_SIZE_ML = 10.0

    def _is_non_perfume(_nm: str, _pr_val: float) -> bool:
        """يُعيد True إذا وجب استبعاد المنتج (ليس عطراً/مجموعة/سعر متطرف/اسم قصير/بلا حجم/ميني)."""
        nonlocal _drop_class, _drop_set, _drop_price, _drop_short, _drop_nosize, _drop_mini
        if _classify_prod(_nm) in _BAD_CLASSES_LIVE:
            _drop_class += 1
            return True
        _low = _nm.lower()
        if any(w in _low for w in _SET_WORDS_LIVE):
            _drop_set += 1
            return True
        if _pr_val > 0 and (_pr_val < 20 or _pr_val > 15000):
            _drop_price += 1
            return True
        if len(_nm.strip()) < 8:
            _drop_short += 1
            return True
        # ── الإصلاح 1: فلتر الحجم — عطر بلا حجم أو ميني < 10مل لا يدخل المفقودة ──
        _sz = _extract_size(_nm)
        if not _sz or _sz <= 0:
            _drop_nosize += 1
            return True
        if _sz < _MIN_SIZE_ML:
            _drop_mini += 1
            return True
        return False

    def _item_type(nm: str) -> str:
        _l = nm.lower()
        if _is_sample(nm) or "ديكانت" in nm or "تقسيم" in nm:
            return "sample"
        if _is_tester(nm) or "تستر" in nm or "tester" in _l:
            return "tester"
        return "retail"

    # 3) طبقة تحقّق ضبابية: حجب موسّع (كلمات دالّة + ماركة) ثم تصنيف ثلاثي:
    #    ≥82           = نملكه باسم مختلف ⇒ إخفاء (لا إيجابيات كاذبة)
    #    65-82 + ماركة متطابقة + حجم متوافق = «محتمل موجود — مراجعة» (يبقى ظاهراً،
    #                    يُحسم بـ Gemini أو يدوياً — لا نخسر مفقوداً حقيقياً)
    #    غير ذلك       = مفقود مؤكد (green)
    _CONFIRM    = _TH   # 82: عتبة «نملكه»
    _REVIEW_MIN = 65    # عتبة «محتمل موجود»
    _SIZE_TOL   = 8.0   # تسامح فرق الحجم (مل) لاعتبار منتجين نفس الحجم
    _owned = _review = 0
    rows = []
    for _bb, (p, _price) in _cand.items():
        _nm = str(p.get("product_name", "") or "")
        # فلتر العطور أولاً (أرخص من المطابقة الضبابية)
        if _is_non_perfume(_nm, float(_price or 0)):
            continue
        # نفس المُطبِّع السريع المستخدم لكتالوجنا ⇒ ماركة قانونية متّسقة الطرفين
        _c_brand_n = _normalize(_brand_fast(_nm) or _brand_fast(str(p.get("brand", "") or "")) or "")
        _c_size = _extract_size(_nm)
        # حجب موسّع: عناصرنا التي تشترك بكلمة دالّة OR بنفس الماركة
        _cidx: set = set()
        for _t in _miss_toks(_bb):
            _b = _inv.get(_t)
            if _b:
                _cidx |= _b
            if len(_cidx) > 200:
                break
        # حجب إضافي بالهيكل العظمي: يلتقط النسخ الإملائية (كاشريل↔كاشاريل) التي
        # يفوتها الحجب الحرفي فتظهر كمفقودة وهي مملوكة. القرار يبقى على token_set + الحجم.
        for _t in _skel_toks(_bb):
            _b = _skel_idx.get(_t)
            if _b:
                _cidx |= _b
            if len(_cidx) > 300:
                break
        if _c_brand_n:
            _cidx.update(_brand_idx.get(_c_brand_n, [])[:200])
        # أفضل تطابق ضبابي ضمن المحجوبين
        _best_sc = 0.0
        _best_it = None
        if _cidx:
            _cidx_list = list(_cidx)
            _bares = [_our_items[i]["bare"] for i in _cidx_list]
            _m = _pr.extractOne(_bb, _bares, scorer=_fz.token_set_ratio)
            if _m:
                _best_sc = float(_m[1])
                _best_it = _our_items[_cidx_list[_m[2]]]
        # حارس الحجم: token_set_ratio يعطي 100% لأي اسم فرعي (subset) بعد تجريد
        # الاسم، فيُخفي منتجات مختلفة من نفس الماركة. لذا لا نُخفي إلا بحجم متوافق.
        _osz = _best_it["size"] if _best_it else 0
        _size_ok = (not _c_size) or (not _osz) or abs(_c_size - _osz) <= _SIZE_TOL
        # تأكيد صارم للإخفاء: تشابه عالٍ (≥82) + حجم متوافق ⇒ نملكه فعلاً
        if _best_sc >= _CONFIRM and _size_ok:
            _owned += 1
            continue  # نملكه باسم مختلف ⇒ ليس مفقوداً
        # المنطقة الرمادية ⇒ تبقى ظاهرة لحسم AI (لا إخفاء صامت لمفقود حقيقي):
        #   • تشابه عالٍ لكن حجم مختلف (نسخة/حجم مختلف محتمل)، أو
        #   • 65-82% بحجم متوافق — بشرط تطابق الماركة في الحالتين
        # أُسقط اشتراط تطابق الماركة: استخراج الماركة يفشل لأسماء مثل «فان كليف»/«فيرتس»
        # فكانت منتجات نملكها (تشابه 65-82% + حجم متطابق) تُصنّف «مؤكد مفقود» خطأً
        # (فيرتس سيريناد، فان كليف بريشيوس عود...). الآن تذهب لـ«مراجعة» (ظاهرة، لا تُخفى
        # ولا تُؤكَّد مفقودة) ويحسمها زر «🤖 تحقّق AI». الإخفاء (≥82%+حجم) لم يتغيّر.
        _is_review = False
        if (_best_it is not None
                and ((_best_sc >= _CONFIRM and not _size_ok)
                     or (_REVIEW_MIN <= _best_sc < _CONFIRM and _size_ok))):
            _is_review = True
            _review += 1
        _comp_list = p.get("competitors_list") or []
        # «المنافسون»: أسماء كل المتاجر التي تبيع هذا المنتج (بعد الدمج العالمي)
        _comp_names_joined = "، ".join([str(x).strip() for x in _comp_list if str(x).strip()])
        # الماركة: حقل المخزن أولاً، ثم استخراج ذكي — لا نتركها فارغة
        _brand = str(p.get("brand", "") or "").strip()
        if not _brand or _brand.lower() in ("nan", "none", "غير محدد"):
            _brand = _extract_brand(_nm) or ""
        # التصنيف الصحيح
        _cat = str(p.get("category", "") or "").strip() or _classify_cat(_nm)
        rows.append({
            "منتج_المنافس": _nm,
            "سعر_المنافس":  _price,
            "الماركة":      _brand,
            "المنافس":      (_comp_list[0] if _comp_list else "") or f"{p.get('competitor_count', 1)} متجر",
            "المنافسون":    _comp_names_joined,
            "الحجم":        "",
            "النوع":        "",
            "تصنيف_المنتج": _cat,
            "صورة_المنافس": str(p.get("image_url", "") or ""),
            "رابط_المنافس": "",
            "السعر_المقترح": float(p.get("suggested_price", 0) or 0),
            "نوع_متاح":     "",
            # review = محتمل موجود (يحتاج تأكيد) | green = مفقود مؤكد
            "مستوى_الثقة":  "review" if _is_review else "green",
            "درجة_التشابه": round(_best_sc, 1),
            # المنتج المرشّح لدينا (لقسم المراجعة + تحقّق Gemini)
            # أقرب منتج لدينا — يُخزَّن لكل صف (مؤكد + مراجعة) لا للمراجعة فقط، كي يراه
            # المستخدم في البطاقة («🔍 مشابه لدينا: X ٪») ويفرز يدوياً بثقة، ويتيح تحقّق AI.
            "منتج_مطابق_محتمل": (_best_it["raw"] if _best_it else ""),
            "حالة_المراجعة":  "بانتظار التحقق" if _is_review else "",
            "هو_تستر":      _item_type(_nm) == "tester",
            "نوع_السلعة":   _item_type(_nm),   # retail / tester / sample
            "عدد_المنافسين": int(p.get("competitor_count", 1) or 1),
        })
    _n_green = sum(1 for r in rows if r.get("مستوى_الثقة") == "green")
    try:
        print(f"[_compute_missing_from_store] مرشحون={len(_prods)} "
              f"بعد_دمج_الاسم={len(_cand)} "
              f"(مستبعد: غير_عطر={_drop_class} مجموعات={_drop_set} "
              f"سعر_متطرف={_drop_price} اسم_قصير={_drop_short} "
              f"بلا_حجم={_drop_nosize} ميني<10مل={_drop_mini}) "
              f"نملكه_82={_owned} مراجعة_65-82={_review} "
              f"مفقود_مؤكد={_n_green} إجمالي_معروض={len(rows)}")
    except Exception:
        pass
    _df_out = pd.DataFrame(rows)
    # v33: تحويل list[dict] لـ JSON string للتخزين المؤقت (cache-safe)
    import json as _json_cache
    if "تفاصيل_المنافسين" in _df_out.columns:
        _df_out["تفاصيل_المنافسين"] = _df_out["تفاصيل_المنافسين"].apply(
            lambda x: _json_cache.dumps(x, ensure_ascii=False) if isinstance(x, list) else "[]"
        )
    return _df_out


def verify_review_bucket_with_ai(missing_df, batch_size: int = 8, max_items: int = None):
    """الإصلاح 2 (هجين آمن): تحقّق Gemini من قسم «محتمل موجود — مراجعة» (65-82%).

    لكل صف review نعطي Gemini منتج المنافس + المنتج المرشّح لدينا ويقرر:
      • مطابق  ⇒ نملكه ⇒ يُحذف من المفقودة (ويُسجَّل رابط قسري في force_links).
      • غير مطابق ⇒ مفقود حقيقي ⇒ مستوى_الثقة=green («مؤكد مفقود (AI)»).
    يعتمد على engine._ai_batch: تدوير مفاتيح Gemini + OpenRouter + cache + fuzzy fallback.
    عند فشل كل مزوّدات AI: الصف يبقى في المراجعة (لا حذف صامت ⇒ لا نخسر مفقوداً).
    يُعيد: (df_بعد, عدد_مؤكد_موجود, عدد_مؤكد_مفقود).
    """
    if not isinstance(missing_df, pd.DataFrame) or missing_df.empty:
        return missing_df, 0, 0
    if "مستوى_الثقة" not in missing_df.columns:
        return missing_df, 0, 0
    from engines.engine import (_ai_batch, extract_size as _es,
                                extract_type as _et, extract_gender as _eg)
    df = missing_df.copy()
    # عناصر المراجعة أولاً، ثم «المؤكد مفقود» ذو «مشابه لدينا» وتشابه ≥55% (الأعلى أولاً)
    # — لالتقاط «مملوك باسم آخر» (عربي↔إنجليزي) الذي تعجز المطابقة النصية عنه.
    # السلامة: العنصر الأخضر يُزال فقط إن أكّد AI امتلاكه، وإلا يبقى ⇒ لا فقدان مفقود.
    _rev_idx = df.index[df["مستوى_الثقة"] == "review"].tolist()
    if "منتج_مطابق_محتمل" in df.columns and "درجة_التشابه" in df.columns:
        _sim = pd.to_numeric(df["درجة_التشابه"], errors="coerce").fillna(0)
        _gmask = ((df["مستوى_الثقة"] == "green")
                  & (df["منتج_مطابق_محتمل"].astype(str).str.len() > 0)
                  & (_sim >= 55))
        _green_hi = _sim[_gmask].sort_values(ascending=False).index.tolist()
        _rev_idx += [i for i in _green_hi if i not in _rev_idx]
    # حدّ أمان لكل ضغطة (يمنع تعليق الواجهة على آلاف العناصر): افتراضي 150
    _cap = int(max_items) if max_items else 150
    _rev_idx = _rev_idx[:_cap]
    if not _rev_idx:
        return df, 0, 0
    _items = []
    for _i in _rev_idx:
        _comp = str(df.at[_i, "منتج_المنافس"])
        _match = str(df.at[_i, "منتج_مطابق_محتمل"] or "") if "منتج_مطابق_محتمل" in df.columns else ""
        if not _match:
            continue
        _items.append((_i, {
            "our": _comp,
            "price": float(df.at[_i, "سعر_المنافس"] or 0),
            "candidates": [{"name": _match, "size": _es(_match),
                            "type": _et(_match) or "?", "gender": _eg(_match) or "?",
                            "price": 0}],
        }))
    _owned_idx, _miss_idx = [], []
    for _b in range(0, len(_items), batch_size):
        _chunk = _items[_b:_b + batch_size]
        try:
            _res = _ai_batch([_it[1] for _it in _chunk])
        except Exception:
            _res = [-1] * len(_chunk)
        for (_idx, _payload), _r in zip(_chunk, _res):
            if _r is not None and _r >= 0:
                _owned_idx.append((_idx, _payload))
            else:
                _miss_idx.append(_idx)
    # AI أكّد امتلاكنا ⇒ احذف من المفقودة + سجّل رابطاً قسرياً (يربط المنافس ببطاقتنا)
    if _owned_idx:
        try:
            _record_forced_links([
                {"our_name": _p["candidates"][0]["name"], "comp_name": _p["our"]}
                for (_i, _p) in _owned_idx
            ])
        except Exception:
            pass
        df = df.drop(index=[_i for (_i, _p) in _owned_idx])
    # AI نفى ⇒ مفقود مؤكد
    for _idx in _miss_idx:
        if _idx in df.index:
            df.at[_idx, "مستوى_الثقة"] = "green"
            if "حالة_المراجعة" in df.columns:
                df.at[_idx, "حالة_المراجعة"] = "مؤكد مفقود (AI)"
    return df.reset_index(drop=True), len(_owned_idx), len(_miss_idx)


def _record_forced_links(pairs):
    """يسجّل روابط منافس↔منتجنا المؤكدة من AI في force_links حتى تظهر في بطاقات المنتجات."""
    if not pairs:
        return
    import os as _os, sqlite3 as _sq
    from datetime import datetime as _dt
    _db = _os.path.join(_os.environ.get("DATA_DIR", "data"), "pricing_v18.db")
    if not _os.path.exists(_db):
        return
    try:
        conn = _sq.connect(_db)
        conn.executemany(
            "INSERT INTO force_links(our_id, our_name, comp_url, source, created_at) "
            "VALUES(?,?,?,?,?)",
            [("", str(p.get("our_name", "")), str(p.get("comp_name", "")),
              "ai_review", _dt.now().isoformat()) for p in pairs],
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def _annotate_change_status(new_df, prev_df):
    """يَسِم كل صف بـ «حالة_التغيير» مقارنةً بالتحليل السابق (الشرط 11):
    «🆕 جديد» = لم يكن في السابق · «🔄 تغيّر السعر» = سعر المنافس تغيّر · «» = ثابت.
    لا يفقد السابق (يُستدعى قبل الدمج التراكمي)."""
    if not isinstance(new_df, pd.DataFrame) or new_df.empty:
        return new_df
    new_df = new_df.copy()
    _key = "معرف_المنتج" if "معرف_المنتج" in new_df.columns else ("المنتج" if "المنتج" in new_df.columns else None)
    _pc = "سعر_المنافس"
    if (_key is None or not isinstance(prev_df, pd.DataFrame) or prev_df.empty
            or _key not in prev_df.columns):
        # لا سابق ⇒ الكل جديد (إن وُجد سابق فارغ) أو بلا وسم
        new_df["حالة_التغيير"] = "🆕 جديد" if (prev_df is None or getattr(prev_df, "empty", True)) else ""
        return new_df
    _prev_price = {}
    for _, _r in prev_df.iterrows():
        _k = str(_r.get(_key, "")).strip()
        if _k and _k not in ("", "nan", "None"):
            _prev_price[_k] = safe_float(_r.get(_pc, 0)) if _pc in prev_df.columns else 0.0

    def _status(_row):
        _k = str(_row.get(_key, "")).strip()
        if not _k or _k in ("", "nan", "None") or _k not in _prev_price:
            return "🆕 جديد"
        if abs(safe_float(_row.get(_pc, 0)) - _prev_price[_k]) > 0.01:
            return "🔄 تغيّر السعر"
        return ""
    new_df["حالة_التغيير"] = new_df.apply(_status, axis=1)
    return new_df


def _dedup_missing_vs_matched(results: dict) -> dict:
    """
    مصدر حقيقة واحد: أي منتج منافس مطابَق في قسم سعري
    يُزال من قائمة المفقود. المطابقة = المصدر الحاسم.
    """
    import logging as _log_dd
    missing_df = results.get("missing", pd.DataFrame())
    if not isinstance(missing_df, pd.DataFrame) or missing_df.empty:
        return results

    # جمع أسماء المنافسين المطابقين (مطبّعة lowercase)
    matched_keys = set()
    for k in ("price_raise", "price_lower", "approved"):
        df = results.get(k, pd.DataFrame())
        if isinstance(df, pd.DataFrame) and not df.empty and "منتج_المنافس" in df.columns:
            matched_keys.update(
                df["منتج_المنافس"].fillna("").astype(str)
                .str.strip().str.lower()
                .loc[lambda s: (s != "") & (s != "nan") & (~s.str.startswith("❌"))]
                .tolist()
            )

    if not matched_keys:
        return results

    # تصفية المفقود: إزالة أي منتج مطابَق
    col = "منتج_المنافس"
    if col in missing_df.columns:
        miss_keys = missing_df[col].fillna("").astype(str).str.strip().str.lower()
        keep_mask = ~miss_keys.isin(matched_keys)
        removed = int((~keep_mask).sum())
        if removed > 0:
            results["missing"] = missing_df[keep_mask].reset_index(drop=True)
            _log_dd.info(
                "DEDUP_MISSING: removed %d products from missing (already matched in price sections)",
                removed,
            )

    return results


def _dedup_missing_display(df: "pd.DataFrame") -> "tuple":
    """إزالة تكرار العرض فقط (لا يمسّ الإجماليات ولا المنطق).

    يُستخدم حصراً قبل عرض بطاقات المفقودة: يطوي الصفوف المتطابقة بصرياً
    (نفس منتج_المنافس + نفس المنافس + نفس السعر) إلى صف واحد لتفادي
    تكرار نفس البطاقة على المستخدم. يُعيد (df_للعرض, عدد_المطويّ).
    لا يُمرَّر هذا الناتج لأي إرسال/تصدير — العمليات تبقى على الـ df الكامل.
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        return df, 0
    _key_cols = [c for c in ("منتج_المنافس", "المنافس", "سعر_المنافس") if c in df.columns]
    if not _key_cols:
        return df, 0
    _key = (
        df[_key_cols]
        .astype(str)
        .apply(lambda s: s.str.strip().str.lower())
        .agg("§".join, axis=1)
    )
    _mask = ~_key.duplicated(keep="first")
    _removed = int((~_mask).sum())
    if _removed <= 0:
        return df, 0
    return df[_mask], _removed


# ── تحديث حي بدون مكوّنات مخصصة (streamlit-autorefresh يفشل غالباً على السحابة/الوكيل) ───────────────
@st.fragment(run_every=4)
def _render_analysis_job_progress_live() -> None:
    """v31-fix: auto-refresh progress + flag results on completion.
    
    CRITICAL FIX: لا نستدعي _auto_resolve_review هنا (طلبات AI بطيئة تسبب
    timeout/OOM داخل fragment). ولا نستدعي st.rerun() (يسبب حلقة لا نهائية
    داخل fragment). بدلاً من ذلك نُعيّن flag في session_state ليُطبَّق
    في الدورة التالية خارج الـ fragment.
    """
    jid = st.session_state.get("job_id")
    if not jid:
        return
    # ⚡ perf: فحص الحالة خفيف (2.4ms) كل 4 ثوانٍ بدل الثقيل (1155ms على 71MB)
    job = get_job_progress(jid, light=True)
    if not job:
        return
    _st = str(job.get("status", ""))
    # Auto-apply results when job completes — بدون AI ولا rerun
    if _st == "done":
        if st.session_state.get("_applied_job_results_id") == jid:
            return  # تم تطبيقه سابقاً — لا تكرار
        job = get_job_progress(jid)  # heavy: النتائج الكاملة مرة واحدة عند الاكتمال
        if job and job.get("results"):
            try:
                _rs = restore_results_from_json(job["results"])
                _df = pd.DataFrame(_rs)
                _mdf = pd.DataFrame(job.get("missing", [])) if job.get("missing") else pd.DataFrame()
                _sp = _split_results(_df)
                # ⚠️ لا نستدعي _auto_resolve_review هنا — يُؤجَّل للشريط الجانبي
                _sp["missing"] = _mdf
                _sp = _dedup_missing_vs_matched(_sp)
                st.session_state.results = _sp
                st.session_state.analysis_df = _df
            except Exception as _frag_err:
                import logging as _frag_log
                _frag_log.warning("Fragment result apply failed: %s", _frag_err)
        st.session_state.last_audit_stats = (job.get("audit") if job else {}) or {}
        st.session_state.job_running = False
        st.session_state["_applied_job_results_id"] = jid
        # ✅ Flag بدلاً من st.rerun() — يُلتقط خارج الـ fragment
        st.session_state["_fragment_needs_rerun"] = True
        st.balloons()
        return
    if _st != "running":
        st.session_state.job_running = False
        st.session_state["_fragment_needs_rerun"] = True
        return
    tot = max(int(job.get("total") or 0), 1)
    proc = min(int(job.get("processed") or 0), tot)
    pct = proc / tot
    # ⚡ v31: عداد تقدم مفصّل مع الوقت المتبقي والسرعة
    _el = ""
    _eta_str = ""
    _speed_str = ""
    try:
        import time as _tt
        _s0 = st.session_state.get("_analysis_start_time")
        if _s0:
            _sec = _tt.time() - _s0
            _el = f"{int(_sec//60)}:{int(_sec%60):02d}"
            if proc > 0 and _sec > 2:
                _speed = proc / _sec
                _speed_str = f"{_speed:.1f}"
                _remaining = (tot - proc) / _speed if _speed > 0 else 0
                if _remaining > 0:
                    _eta_min = int(_remaining // 60)
                    _eta_sec = int(_remaining % 60)
                    _eta_str = f"{_eta_min}:{_eta_sec:02d}"
    except Exception:
        pass
    # شريط تفصيلي بألوان وإيموجي
    _stage = "\U0001f50d" if pct < 0.3 else ("\u2699\ufe0f" if pct < 0.7 else ("\U0001f680" if pct < 0.95 else "\u2705"))
    _parts = [f"{_stage} تحليل: **{proc:,}**/{tot:,} ({100*pct:.0f}%)"]
    if _el:
        _parts.append(f"\u23f1\ufe0f {_el}")
    if _speed_str:
        _parts.append(f"\u26a1 {_speed_str} منتج/ث")
    if _eta_str:
        _parts.append(f"\u23f3 متبقي: ~{_eta_str}")
    st.progress(min(pct, 0.99))
    st.caption(" | ".join(_parts))

@st.fragment(run_every=3)
def _scraper_main_tab_live_rerun_tick() -> None:
    """إعادة تشغيل السكربت كاملاً كل 3 ث أثناء الكشط؛ يتخطى أول استدعاء فوري لـ st.fragment."""
    k = "_app_scraper_live_tick_n"
    st.session_state[k] = int(st.session_state.get(k, 0)) + 1
    if st.session_state[k] <= 1:
        return
    st.rerun()


def _analysis_mask_for_review_row(adf: pd.DataFrame, row: pd.Series) -> pd.Series:
    """مفتاح مطابقة صف المراجعة مع جدول التحليل الكامل."""
    try:
        oid = str(row.get("معرف_المنتج", "") or "").strip()
        cid = str(row.get("معرف_المنافس", "") or "").strip()
        if oid and oid != "nan" and cid and cid != "nan":
            m = (adf["معرف_المنتج"].astype(str).str.strip() == oid) & (
                adf["معرف_المنافس"].astype(str).str.strip() == cid
            )
            if m.any():
                return m
        n1 = str(row.get("المنتج", "") or "").strip()
        n2 = str(row.get("منتج_المنافس", "") or "").strip()
        return (adf["المنتج"].astype(str).str.strip() == n1) & (
            adf["منتج_المنافس"].astype(str).str.strip() == n2
        )
    except Exception:
        return pd.Series([False] * len(adf))


def _reclassify_section_to_qarar(section: str):
    """يحوّل قيمة section بعد التطبيع في ai_engine إلى نص عمود القرار."""
    if not section:
        return None
    s = str(section)
    if "مراجعة" in s or s.strip() == "⚠️ تحت المراجعة":
        return None
    if "🔵" in s or ("مفقود" in s and "منتجات" not in s):
        return "🔍 منتجات مفقودة"
    if "🔴" in s or "أعلى" in s:
        return "🔴 سعر أعلى"
    if "🟢" in s or "أقل" in s:
        return "🟢 سعر أقل"
    if "✅" in s or "موافق" in s:
        return "✅ موافق"
    return None


def _apply_reclassify_to_analysis(adf: pd.DataFrame, review_df: pd.DataFrame,
                                  rc_results: list, min_conf: float = 75.0):
    """
    يحدّث عمود القرار في analysis_df حسب نتائج reclassify_review_items.
    يعيد (الجدول المحدث، إحصاءات).
    """
    stats = {
        "applied": 0, "skip_conf": 0, "skip_review": 0, "skip_idx": 0,
        "skip_no_row": 0, "skip_no_qarar": 0,
    }
    if adf is None or adf.empty or not rc_results:
        return adf, stats
    out = adf.copy()
    batch = review_df.head(30).reset_index(drop=True)
    nbatch = len(batch)
    for rc in rc_results:
        try:
            conf = float(rc.get("confidence") or 0)
        except Exception:
            conf = 0.0
        if conf < min_conf:
            stats["skip_conf"] += 1
            continue
        sec = rc.get("section", "")
        qarar = _reclassify_section_to_qarar(sec)
        if qarar is None:
            stats["skip_review"] += 1
            continue
        try:
            idx = int(rc.get("idx", 0) or 0)
        except Exception:
            idx = 0
        if idx < 1 or idx > nbatch:
            stats["skip_idx"] += 1
            continue
        row = batch.iloc[idx - 1]
        mask = _analysis_mask_for_review_row(out, row)
        if not mask.any():
            stats["skip_no_row"] += 1
            continue
        out.loc[mask, "القرار"] = qarar
        stats["applied"] += 1
    return out, stats


def _persist_analysis_after_reclassify(adf: pd.DataFrame):
    """يحدّث job_progress إن وُجد job_id وحالة done."""
    jid = st.session_state.get("job_id")
    if not jid:
        return
    try:
        job = get_job_progress(jid)
        if not job or str(job.get("status", "")) != "done":
            return
        miss = job.get("missing") if isinstance(job.get("missing"), list) else []
        save_job_progress(
            jid,
            int(job.get("total") or len(adf)),
            int(job.get("processed") or len(adf)),
            safe_results_for_json(adf.to_dict("records")),
            "done",
            str(job.get("our_file") or ""),
            str(job.get("comp_files") or ""),
            missing=miss,
        )
    except Exception:
        pass


# ── تحميل تلقائي للنتائج المحفوظة عند فتح التطبيق ──
import logging as _restore_log
_restore_log.basicConfig(level=_restore_log.INFO)
_rlog = _restore_log.getLogger("auto_restore")

def _safe_auto_restore():
    """استعادة آخر نتائج تحليل — محمية بالكامل من الأخطاء."""
    try:
        _rlog.info("🔄 [RESTORE] بدء الاستعادة...")
        _rlog.info("🔄 [RESTORE] DATA_DIR = %s", __import__('os').environ.get('DATA_DIR', 'NOT SET'))

        # تنظيف الوظائف المعلقة
        try:
            release_stale_running_jobs(stale_after_seconds=300)
        except Exception:
            pass

        # البحث عن آخر وظيفة مكتملة
        conn = get_db()
        try:
            _job_count = conn.execute("SELECT COUNT(*) FROM job_progress").fetchone()[0]
            _rlog.info("🔄 [RESTORE] إجمالي الوظائف: %d", _job_count)

            _done_row = conn.execute(
                "SELECT job_id, length(results_json) AS _rjlen FROM job_progress "
                "WHERE status IN ('done','stopped') "
                "AND total = processed AND processed > 0 "
                "AND results_json IS NOT NULL AND length(results_json) > 10 "
                "ORDER BY id DESC LIMIT 1"
            ).fetchone()
        finally:
            conn.close()

        if not _done_row:
            _rlog.warning("⚠️ [RESTORE] لا توجد وظيفة مكتملة")
            return

        # 🛡️ حارس الذاكرة: نتائج ضخمة جداً قد تُسبّب OOM على حاويات محدودة الذاكرة
        # (مثل Railway) فتظهر شاشة سوداء. نتخطّى الاستعادة التلقائية لإبقاء التطبيق
        # يفتح، مع علامة للواجهة. الحد قابل للضبط عبر MAX_RESTORE_JSON_BYTES (افتراضي 30MB).
        _max_restore = int(__import__("os").environ.get("MAX_RESTORE_JSON_BYTES", str(50 * 1024 * 1024)))
        _rjlen = _done_row["_rjlen"] or 0
        if _rjlen > _max_restore:
            _rlog.warning(
                "⚠️ [RESTORE] نتائج كبيرة (%.1f MB > الحد %.1f MB) — تخطّي تلقائي لحماية الذاكرة",
                _rjlen / 1048576, _max_restore / 1048576,
            )
            st.session_state["_restore_skipped_big_job"] = _done_row["job_id"]
            return

        job_id = _done_row["job_id"]
        _rlog.info("🔄 [RESTORE] وظيفة: %s", job_id)

        # تحميل النتائج — القسم الثقيل
        _auto_job = get_job_progress(job_id)
        if not _auto_job or not _auto_job.get("results"):
            _rlog.warning("⚠️ [RESTORE] لا توجد نتائج في الوظيفة")
            return

        _rlog.info("✅ [RESTORE] نتائج: %d سجل", len(_auto_job["results"]))

        _auto_records = restore_results_from_json(_auto_job["results"])
        _auto_df = pd.DataFrame(_auto_records)
        if _auto_df.empty:
            _rlog.warning("⚠️ [RESTORE] DataFrame فارغ!")
            return

        _rlog.info("✅ [RESTORE] DataFrame: %d صف", len(_auto_df))

        # المفقودات
        _auto_miss = pd.DataFrame(_auto_job.get("missing", [])) if _auto_job.get("missing") else pd.DataFrame()

        # تقسيم النتائج (سريع، محلي، بلا AI).
        # ⚠️ لا نستدعي _auto_resolve_review هنا: فهو يُطلق نداءات AI متزامنة
        # (auto_resolve_review_v2) كانت تُعلّق التطبيق عند كل فتح جلسة (شاشة سوداء
        # على Railway) وتستهلك حصة AI. الحسم بالـ AI يتم أثناء التحليل الفعلي فقط،
        # لا أثناء الاستعادة السلبية عند فتح التطبيق.
        _auto_r = _split_results(_auto_df)
        _auto_r["missing"] = _auto_miss
        try:
            _auto_r = _dedup_missing_vs_matched(_auto_r)
        except Exception:
            pass

        st.session_state.results     = _auto_r
        st.session_state.analysis_df = _auto_df
        st.session_state.job_id      = _auto_job.get("job_id")
        _rlog.info("🎉 [RESTORE] تمت الاستعادة بنجاح!")

    except Exception as e:
        _rlog.error("❌ [RESTORE] فشل: %s", e, exc_info=True)
        # التطبيق يفتح عادي بدون نتائج — لن يتعطل

if st.session_state.results is None and not st.session_state.job_running:
    _safe_auto_restore()


# ── دوال مساعدة ───────────────────────────
def db_log(page, action, details=""):
    try: log_event(page, action, details)
    except Exception: pass



# ── ⚡ v33: دالة تنقل عامة بأسهم وأرقام صفحات ──────────────────────────
def render_pagination(total_items: int, page_size: int, key_prefix: str) -> tuple:
    """
    شريط تنقل موحّد بأسهم وأرقام صفحات.
    يُعيد (start_idx, end_idx, current_page)
    """
    if total_items <= 0:
        return 0, 0, 1
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    # ── تتبع الصفحة في session_state ──
    pg_key = f"_pg_{key_prefix}"
    if pg_key not in st.session_state:
        st.session_state[pg_key] = 1
    current = int(st.session_state[pg_key])
    current = max(1, min(current, total_pages))

    if total_pages <= 1:
        st.caption(f"عرض {total_items} منتج")
        return 0, total_items, 1

    # ── أزرار التنقل ──
    # حساب أرقام الصفحات المعروضة (max 7)
    if total_pages <= 7:
        pages_to_show = list(range(1, total_pages + 1))
    else:
        pages_to_show = []
        if current <= 4:
            pages_to_show = [1, 2, 3, 4, 5, -1, total_pages]
        elif current >= total_pages - 3:
            pages_to_show = [1, -1, total_pages-4, total_pages-3, total_pages-2, total_pages-1, total_pages]
        else:
            pages_to_show = [1, -1, current-1, current, current+1, -1, total_pages]

    # عدد الأعمدة = سهم + أرقام + سهم + عداد
    n_btns = len(pages_to_show)
    cols = st.columns([1] + [1]*n_btns + [1] + [3])

    # سهم السابقة
    with cols[0]:
        if st.button("◀", key=f"{key_prefix}_prev", disabled=(current <= 1), help="الصفحة السابقة"):
            st.session_state[pg_key] = current - 1
            st.rerun()

    # أرقام الصفحات
    for i, pg in enumerate(pages_to_show):
        with cols[i + 1]:
            if pg == -1:
                st.markdown('<div style="text-align:center;padding:6px;color:#555">…</div>', unsafe_allow_html=True)
            elif pg == current:
                st.markdown(
                    f'<div style="text-align:center;padding:4px 8px;background:#6C63FF;color:white;'
                    f'border-radius:8px;font-weight:700;font-size:.9rem">{pg}</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(str(pg), key=f"{key_prefix}_pg{pg}"):
                    st.session_state[pg_key] = pg
                    st.rerun()

    # سهم التالية
    with cols[n_btns + 1]:
        if st.button("▶", key=f"{key_prefix}_next", disabled=(current >= total_pages), help="الصفحة التالية"):
            st.session_state[pg_key] = current + 1
            st.rerun()

    # عداد
    start = (current - 1) * page_size
    end = min(start + page_size, total_items)
    with cols[n_btns + 2]:
        st.caption(f"عرض {start+1}-{end} من {total_items}")

    return start, end, current


def _calc_priority_score(row):
    """Calculate priority score (0-100) for smart sorting."""
    score = 0
    try:
        diff = abs(float(row.get('الفرق', 0) or 0))
        match_pct = float(row.get('نسبة_التطابق', 0) or 0)
        comp_price = float(row.get('سعر_المنافس', 0) or 0)
        our_price = float(row.get('السعر', 0) or 0)
        # 40 pts: price difference magnitude (bigger diff = higher priority)
        score += min(diff / 5, 40)
        # 30 pts: match confidence (higher match = more reliable)
        score += (match_pct / 100) * 30
        # 20 pts: percentage difference (not just absolute)
        if our_price > 0:
            pct_diff = abs(diff / our_price) * 100
            score += min(pct_diff / 2.5, 20)
        # 10 pts: has competitor price (confirmed competitive data)
        if comp_price > 0:
            score += 10
    except Exception:
        pass
    return round(min(score, 100), 1)



def _effective_column_map(df: pd.DataFrame, key_prefix: str):
    """
    يقرأ اختيارات القوائم المنسدلة (إن وُجدت) وإلا يعود لنتيجة التعرف التلقائي.
    """
    if df is None or df.empty:
        return {"name": None, "price": None, "id_col": None, "img": None, "url": None}
    rc = resolve_catalog_columns(df)
    skip = "— (تخطي)"
    cols = {str(c) for c in df.columns}

    def _one(suffix: str, fallback_raw):
        k = f"{key_prefix}_{suffix}"
        v = st.session_state.get(k)
        fb = str(fallback_raw or "").strip()
        if v is None or v == skip:
            return fb if fb and fb in cols else None
        sv = str(v).strip()
        if sv == skip or sv not in cols:
            return fb if fb and fb in cols else None
        return sv

    return {
        "name": _one("name", rc.get("name")),
        "price": _one("price", rc.get("price")),
        "id_col": _one("id", rc.get("id")),
        "img": _one("img", rc.get("img")),
        "url": _one("url", rc.get("url")),
    }


def _resolve_catalog_columns_relaxed(df: pd.DataFrame) -> dict:
    """
    FIX: Relaxed Constraints — fallback مرن لاختيار أعمدة الاسم/السعر/المعرف
    لضمان حفظ الكتالوج حتى لو فشل التعرف الصارم.
    """
    from engines.engine import resolve_catalog_columns
    base = resolve_catalog_columns(df) if df is not None else {}
    if df is None or df.empty:
        return {"name": None, "price": None, "id": None, "img": None, "url": None}
    cols = list(df.columns)
    out = {
        "name": base.get("name"),
        "price": base.get("price"),
        "id": base.get("id"),
        "img": base.get("img"),
        "url": base.get("url"),
    }
    if not out["name"]:
        text_candidates = []
        for c in cols:
            s = df[c]
            if pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s):
                nn = s.fillna("").astype(str).str.strip()
                score = int((nn != "").sum())
                if score > 0:
                    text_candidates.append((score, c))
        if text_candidates:
            text_candidates.sort(reverse=True)
            out["name"] = text_candidates[0][1]
    if not out["price"]:
        num_candidates = []
        for c in cols:
            s = pd.to_numeric(df[c], errors="coerce")
            score = int(s.notna().sum())
            if score > 0:
                num_candidates.append((score, c))
        if num_candidates:
            num_candidates.sort(reverse=True)
            out["price"] = num_candidates[0][1]
    if not out["id"]:
        for c in cols:
            lc = str(c).strip().lower()
            if any(k in lc for k in ("id", "sku", "معرف", "رقم", "barcode", "باركود")):
                out["id"] = c
                break
        if not out["id"] and out["name"] and out["name"] in cols:
            out["id"] = out["name"]
    return out


def _dashboard_competitor_label(upload_name: str) -> str:
    """اسم عرض للمنافس من اسم الملف (بدون .csv)."""
    n = (upload_name or "").strip()
    if not n:
        return "منافس"
    return n.rsplit(".", 1)[0] if n.lower().endswith(".csv") else n


def _render_column_mapping_expander(df: pd.DataFrame, key_prefix: str):
    """
    تحديد الأعمدة بقوائم منسدلة + معاينة صفوف قابلة للضبط + 5 قيم من عمود واحد.
    """
    if df is None or df.empty:
        st.warning("ملف فارغ أو غير مقروء")
        return
    rc = resolve_catalog_columns(df)
    cols_list = [str(c) for c in df.columns]
    skip = "— (تخطي)"
    options = [skip] + cols_list
    n_total = len(df)

    def _ix(fallback_raw):
        fb = str(fallback_raw or "").strip()
        if fb and fb in options:
            return options.index(fb)
        return 0

    st.caption(f"📊 **{len(cols_list)}** عمود — اضبط الأدوار أو اترك التعرف التلقائي")
    if len(cols_list) <= 4:
        st.caption("أسماء الأعمدة: " + "، ".join(f"«{c}»" for c in cols_list))
    g1, g2 = st.columns(2)
    with g1:
        st.selectbox("🏷️ اسم المنتج", options, index=_ix(rc.get("name")), key=f"{key_prefix}_name")
        st.selectbox("💰 السعر", options, index=_ix(rc.get("price")), key=f"{key_prefix}_price")
        st.selectbox("🔢 المعرف / SKU", options, index=_ix(rc.get("id")), key=f"{key_prefix}_id")
    with g2:
        st.selectbox("🖼️ صورة المنتج", options, index=_ix(rc.get("img")), key=f"{key_prefix}_img")
        st.selectbox("🔗 رابط المنتج", options, index=_ix(rc.get("url")), key=f"{key_prefix}_url")

    st.markdown("**عرض صفوف الملف**")
    pr1, pr2 = st.columns([1, 2])
    with pr1:
        n_preview = st.number_input(
            "عدد الصفوف",
            min_value=1,
            max_value=min(n_total, 500),
            value=min(5, n_total),
            step=1,
            key=f"{key_prefix}_preview_rows",
            help="معاينة من بداية الملف (كل الأعمدة).",
        )
    with pr2:
        st.caption(f"إجمالي الصفوف في الملف: **{n_total}**")
    _n = int(n_preview)
    st.dataframe(
        df.head(_n),
        use_container_width=True,
        height=min(520, 100 + _n * 28 + len(cols_list) * 2),
    )

    st.markdown("**معاينة — 5 قيم من عمود واحد**")
    peek_opts = ["— اختر عموداً —"] + cols_list
    pc = st.selectbox("العمود", peek_opts, key=f"{key_prefix}_peek")
    if pc and not str(pc).startswith("—"):
        try:
            st.dataframe(df[[pc]].head(5), use_container_width=True)
        except Exception:
            st.caption("تعذر عرض هذا العمود.")

    with st.expander("🔧 JSON — تفاصيل التعرف الخام", expanded=False):
        st.json(detect_input_columns(df))


def _validate_uploaded_catalog(df, label: str):
    """حارس أعمدة: اسم + سعر مطلوبان قبل التحليل (بعد read_file + التعرف العميق)."""
    if df is None or df.empty:
        st.error(f"⚠️ ملف فارغ أو غير مقروء: {label}")
        st.stop()
    m = resolve_catalog_columns(df)
    if not m.get("name") or not m.get("price"):
        st.error(
            f"⚠️ فشل التعرف الذكي على الأعمدة المطلوبة (**اسم المنتج** + **سعر**) في: **{label}**"
        )
        st.warning("معاينة خام — أول 10 صفوف:")
        st.dataframe(df.head(10), use_container_width=True)
        st.stop()


def _render_audit_bar(audit_stats: dict):
    """شريط تدقيق Zero Data Loss — يطابق المدخلات مع المخرجات المحاسَبة."""
    if not audit_stats:
        return
    ti = int(audit_stats.get("total_input") or 0)
    pr = int(audit_stats.get("processed") or 0)
    nc = int(audit_stats.get("no_competitor_found") or 0)
    se = int(audit_stats.get("skipped_empty") or 0)
    sk = int(audit_stats.get("skipped_samples") or 0)
    tot = pr + nc + se + sk
    st.markdown(
        f"""
    <div style="display:flex;flex-wrap:wrap;justify-content:space-between;gap:10px;
        background:#2c3e50;color:#fff;padding:15px;border-radius:8px;margin-bottom:16px;">
        <div style="text-align:center;flex:1;min-width:88px;"><strong>📦 إجمالي المدخلات</strong><br>
            <span style="font-size:1.5rem;">{ti}</span></div>
        <div style="text-align:center;flex:1;min-width:88px;"><strong>✅ وُجد منافس</strong><br>
            <span style="font-size:1.5rem;color:#4caf50;">{pr}</span></div>
        <div style="text-align:center;flex:1;min-width:88px;"><strong>⚪ لا منافس</strong><br>
            <span style="font-size:1.5rem;color:#ff9800;">{nc}</span></div>
        <div style="text-align:center;flex:1;min-width:88px;"><strong>👻 صفوف فارغة</strong><br>
            <span style="font-size:1.5rem;color:#9e9e9e;">{se}</span></div>
        <div style="text-align:center;flex:1;min-width:88px;"><strong>🚫 عينة / &lt;10مل</strong><br>
            <span style="font-size:1.5rem;color:#e53935;">{sk}</span></div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    if ti > 0 and tot != ti:
        st.error(
            f"🚨 تحذير تدقيق: المدخلات ({ti}) لا تساوي مجموع الحالات ({tot}) — "
            f"معالج={pr} + بدون منافس={nc} + فارغ={se} + عينة/صغير={sk}."
        )


def _render_reconciliation_dashboard(audit_stats: dict):
    """لوحة محاسبة صفوف ملفات المنافسين (مدخلات = متطابق + جديد + تالف)."""
    if not audit_stats:
        return
    rec = audit_stats.get("reconciliation")
    if not rec:
        return
    x = int(rec.get("total_read") or 0)
    y = int(rec.get("matched") or 0)
    z = int(rec.get("new_ready") or 0)
    w = int(rec.get("corrupted") or 0)

    # ── التحقق البرمجي من معادلة المحاسبة (إلزامي): إجمالي = متطابق + جديد + تالف ──
    _balance_sum = y + z + w
    _balance_ok = (_balance_sum == x) if x > 0 else True

    st.markdown("##### 📊 محاسبة رفع المنافسين (Reconciliation)")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🟢 إجمالي تمت قراءته", x)
    c2.metric("🔵 متطابق وتمت معالجته", y)
    c3.metric("🟡 منتجات جديدة (جاهزة للتصدير لسلة)", z)
    c4.metric("🔴 سجلات تالفة", w)

    if not _balance_ok:
        _gap = x - _balance_sum
        st.error(
            f"🚨 **انتهاك معادلة المحاسبة** — "
            f"المدخل ({x}) ≠ مجموع المخرجات ({_balance_sum}) | "
            f"متطابق={y} + جديد={z} + تالف={w} | فجوة={_gap:+d}\n\n"
            "يعني هذا وجود صفوف لم تُصنَّف — راجع محرك المحاسبة."
        )
    elif x > 0:
        st.success(
            f"✅ معادلة المحاسبة محققة: {x} = {y} + {z} + {w}"
        )

    if not rec.get("balance_ok", True) and rec.get("warning_message"):
        st.warning(rec["warning_message"])
    _diag = rec.get("diagnostics") or {}
    _dup = int(_diag.get("duplicate_skipped") or 0)
    _excluded_total = int(w + _dup)
    _fb = st.session_state.get("reconciliation_failed_csv")
    if _excluded_total > 0:
        ex1, ex2 = st.columns([2, 1])
        ex1.metric("🚨 المنتجات المكررة/المستبعدة", f"{_excluded_total:,} منتج")
        with ex2:
            if _fb:
                st.download_button(
                    label="⬇️ تنزيل المستبعدات الآن",
                    data=_fb,
                    file_name="failed_rows.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dl_failed_rows_prominent",
                )
    if not _fb:
        from pathlib import Path

        _fp = audit_stats.get("reconciliation_failed_csv_path")
        if _fp:
            p = Path(str(_fp))
            if p.is_file():
                try:
                    _fb = p.read_bytes()
                    st.session_state.reconciliation_failed_csv = _fb
                except OSError:
                    _fb = None
    if _fb:
        st.download_button(
            label="⬇️ تنزيل failed_rows.xlsx (الصفوف التالفة)",
            data=_fb,
            file_name="failed_rows.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="dl_failed_rows_log",
        )
    st.caption(
        "الأرقام تعكس **صفوف ملفات المنافس** في آخر تشغيل؛ إن فعّلت الدمج التراكمي قد يزيد عدد "
        "صفوف «منتجات مفقودة» في الجداول دون أن يغيّر إجمالي المدخلات أعلاه."
    )


def _find_analysis_row_for_processed(product_name: str):
    """
    يعيد صف التحليل المطابق لسجل «تمت المعالجة»: اسم منتجنا أو اسم المنتج عند المنافس.
    يبحث في analysis_df ثم في أقسام results (والجدول الكامل all).
    """
    pn = str(product_name or "").strip()
    if not pn:
        return None

    def _match_df(df):
        if df is None or getattr(df, "empty", True):
            return None
        for col in ("المنتج", "منتج_المنافس"):
            if col not in df.columns:
                continue
            try:
                m = df[df[col].astype(str).str.strip() == pn]
                if not m.empty:
                    return m.iloc[0]
            except Exception:
                continue
        return None

    adf = st.session_state.get("analysis_df")
    r = _match_df(adf)
    if r is not None:
        return r

    res = st.session_state.get("results") or {}
    for key in ("all", "price_raise", "price_lower", "approved", "review", "excluded", "missing"):
        r = _match_df(res.get(key))
        if r is not None:
            return r
    return None


def _lookup_images_from_analysis_session(product_name: str):
    """صورة منتجنا + صورة المنافس من جلسة التحليل أو أقسام النتائج."""
    row = _find_analysis_row_for_processed(product_name)
    if row is None:
        return "", ""
    try:
        return row_media_urls_from_analysis(row)
    except Exception:
        return "", ""


def _lookup_product_urls_from_analysis_session(product_name: str):
    """رابط منتجنا + رابط صفحة المنتج عند المنافس."""
    row = _find_analysis_row_for_processed(product_name)
    if row is None:
        return "", ""
    try:
        return our_product_url_from_row(row), competitor_product_url_from_row(row)
    except Exception:
        return "", ""


def _processed_dual_image_html(our_img: str, comp_img: str, title_our: str, title_comp: str) -> str:
    """خليتان للصور: منتجنا | المنافس — تحميل eager حتى تظهر فوراً في Streamlit."""
    w, h = 56, 56

    def _slot(label: str, url: str, alt: str) -> str:
        if url and str(url).strip():
            img = lazy_img_tag(url, w, h, alt, loading="eager")
        else:
            img = (
                f'<div style="width:{w}px;height:{h}px;border-radius:8px;background:#121c2e;'
                f'border:1px dashed #2a3f5f;display:flex;align-items:center;justify-content:center;'
                f'color:#4a5c78;font-size:.75rem">—</div>'
            )
        return (
            f'<div style="display:flex;flex-direction:column;align-items:center;gap:5px;min-width:64px">'
            f'<span style="font-size:.68rem;color:#7eb8ff;font-weight:800;letter-spacing:.02em">{label}</span>'
            f"{img}</div>"
        )

    return (
        '<div style="display:flex;gap:16px;flex-shrink:0;align-items:flex-end;padding:2px 0">'
        f'{_slot("منتجنا", our_img, title_our[:40])}'
        f'{_slot("المنافس", comp_img, title_comp[:40])}'
        "</div>"
    )


def _is_http_url_text(s) -> bool:
    t = str(s or "").strip().lower()
    return t.startswith("http://") or t.startswith("https://")


def _humanize_competitor_upload(comp: str) -> str:
    """تطبيع اسم المنافس ليظهر كاسم متجر مقروء بدلاً من رابط أو اسم ملف خام."""
    c = str(comp or "").strip()
    if not c:
        return "—"

    parsed = urlparse(c if re.match(r"^https?://", c, flags=re.I) else f"https://{c}")
    host = (parsed.netloc or parsed.path or "").strip().lower()
    if host and ("." in host or "/" in c):
        host = host.split("/")[0].strip()
        host = re.sub(r"^www\.", "", host, flags=re.I)
        if host:
            c = host

    low = c.lower()
    for ext in (".csv", ".xlsx", ".xls", ".tsv", ".ods"):
        if low.endswith(ext):
            c = c[: -len(ext)].strip() or c
            break

    c = re.sub(r"[_\-]+", " ", c).strip()
    c = re.sub(r"\s+", " ", c).strip()
    return c or "—"


def _normalize_all_competitors(raw_comps) -> list:
    """إزالة التكرار من قائمة جميع المنافسين مع تطبيع أسماء المتاجر دون فقدان أي منافس فعلي."""
    if not isinstance(raw_comps, list):
        return []

    cleaned = []
    seen = set()
    for comp in raw_comps:
        if not isinstance(comp, dict):
            continue
        comp_copy = dict(comp)
        comp_name = _humanize_competitor_upload(comp_copy.get("competitor", ""))
        prod_name = str(comp_copy.get("name", "") or "").strip()
        prod_id = str(comp_copy.get("product_id", "") or "").strip()
        prod_url = str(comp_copy.get("product_url") or comp_copy.get("url") or "").strip().lower()
        key = (comp_name.lower(), prod_id or prod_url or prod_name.lower())
        if key in seen:
            continue
        seen.add(key)
        comp_copy["competitor"] = comp_name
        cleaned.append(comp_copy)
    return cleaned


def _display_competitor_name(row) -> str:
    """اسم المنافس الأساسي في البطاقة مع fallback من قائمة جميع المنافسين عند الحاجة."""
    direct = _humanize_competitor_upload(row.get("المنافس", ""))
    if direct and direct != "—":
        return direct
    normalized = _normalize_all_competitors(row.get("جميع_المنافسين", row.get("جميع المنافسين", [])))
    if normalized:
        return _humanize_competitor_upload(normalized[0].get("competitor", ""))
    return "—"


def _display_name_for_missing_row(row) -> str:
    """
    اسم عرض للمفقودات: يفضّل نصاً حقيقياً من أي عمود معروف قبل اعتبار الاسم رابطاً فقط.
    """
    def _clean(v):
        x = str(v or "").strip()
        if not x or x.lower() in ("nan", "none", "<na>"):
            return ""
        return x

    for key in (
        "المنتج",
        "اسم المنتج",
        "اسم_المنتج",
        "Product",
        "Name",
        "name",
        "title",
        "الاسم",
        "منتج_المنافس",
    ):
        if key not in row.index:
            continue
        v = _clean(row.get(key))
        if v and not _is_http_url_text(v):
            return v

    br = _clean(row.get("الماركة"))
    sz = _clean(row.get("الحجم"))
    pt = _clean(row.get("النوع"))
    chunks = [c for c in (br, sz, pt) if c]
    if chunks:
        return " · ".join(chunks)

    return ""


def _processed_row_url_chips_html(our_url: str, comp_url: str) -> str:
    """روابط مختصرة بجانب سطر الملاحظات في «تمت المعالجة»."""
    parts = []
    ou = (our_url or "").strip()
    cu = (comp_url or "").strip()
    if ou.startswith("http"):
        parts.append(
            f'<a href="{html.escape(ou, quote=True)}" target="_blank" rel="noopener noreferrer" '
            f'style="color:#4fc3f7;font-size:.73rem;font-weight:600;text-decoration:underline">🔗 رابط منتجنا</a>'
        )
    if cu.startswith("http"):
        parts.append(
            f'<a href="{html.escape(cu, quote=True)}" target="_blank" rel="noopener noreferrer" '
            f'style="color:#ff9800;font-size:.73rem;font-weight:600;text-decoration:underline">🔗 عند المنافس</a>'
        )
    if not parts:
        return ""
    return '<span style="margin-right:8px">&nbsp;|&nbsp;</span>' + '<span style="margin:0 4px;color:#555">·</span>'.join(parts)


def _track_processed_price_sku(product_id) -> None:
    # FIX: Smart Workflow & AI Tracking
    _pid = str(product_id or "").strip()
    if _pid and _pid not in ("nan", "None", "NaN"):
        st.session_state["processed_price_skus"].add(_pid)


def _track_processed_missing_url(comp_url: str) -> None:
    # FIX: Smart Workflow & AI Tracking
    _url = str(comp_url or "").strip()
    if _url:
        st.session_state["processed_missing_urls"].add(_url)


def _show_transparency_counter(total_count: int, visible_count: int, label: str = "منتجاً") -> None:
    # FIX: Transparency & Reversibility
    hidden_count = max(0, int(total_count or 0) - int(visible_count or 0))
    st.info(
        f"يوجد {int(total_count or 0)} {label} في هذه الفئة. "
        f"(تم إخفاء {hidden_count} {label} لأنها في قائمة 'تمت المعالجة' أو مخفية يدوياً)."
    )


# ════════════════════════════════════════════════
#  Callbacks — أحداث الأزرار التفاعلية (Event-Driven)
#  تُعرَّف هنا (خارج حلقة الرسم) حتى تتوافق مع on_click.
#  ضمان: تُنفَّذ مرة واحدة بالضبط عند كل نقرة، والحالة تُحدَّث
#  تلقائياً قبل إعادة رسم الصفحة — بدون st.rerun() صريح.
# ════════════════════════════════════════════════
def _cb_send_make(
    prefix: str, idx,
    our_name: str, comp_name: str,
    our_price: float, comp_price: float, diff: float,
    decision: str, comp_src: str, pid: str, comp_url: str,
    no: str = "",
) -> None:
    """
    Callback: إرسال تحديث سعر واحد إلى Make.com عبر on_click.
    يقرأ السعر المستهدف من st.session_state لضمان القراءة اللحظية.
    """
    _price_key = f"target_price_{prefix}_{idx}"
    _tp = float(st.session_state.get(_price_key, 0) or 0)
    if _tp <= 0:
        st.session_state[f"_act_{prefix}_{idx}"] = (
            "error", "❌ السعر يجب أن يكون أكبر من صفر"
        )
        return

    # FIX: Transparency & Reversibility + حماية من خطأ الشبكة
    try:
        _mk_res = send_single_product({
            "NO":         no or pid,
            "product_id": pid,
            "name": our_name,
            "price": float(_tp),
            "comp_name": comp_name,
            "comp_price": comp_price,
            "diff": diff,
            "decision": decision,
            "competitor": comp_src,
            "comp_url": comp_url or "",
        })
    except Exception as _net_err:
        st.session_state[f"_act_{prefix}_{idx}"] = (
            "error", f"❌ خطأ شبكة: {_net_err}"
        )
        return
    _mk_status = int(_mk_res.get("status_code") or 0)
    _ok = bool(_mk_res.get("success"))

    _hk = f"{prefix}_{our_name}_{idx}"
    if _ok:
        _track_processed_price_sku(pid)  # FIX: Smart Workflow & AI Tracking
        _track_processed_missing_url(comp_url)  # FIX: Smart Workflow & AI Tracking
        # Phase 1: تحديث خريطة الأسعار للـ Smart Reversion
        _pid_s = str(pid or "").strip()
        if _pid_s and _pid_s not in ("nan", "None", "NaN"):
            st.session_state.setdefault("_processed_price_map", {})[_pid_s] = float(_tp)
        st.session_state.hidden_products.add(_hk)
        try:
            save_hidden_product(_hk, our_name, "sent_to_make")
            save_processed(
                _hk, our_name, comp_src, "send_price",
                old_price=our_price, new_price=_tp, product_id=pid,
                notes=f"Make ← {prefix} | {comp_src} | {comp_price:.0f}→{_tp:.0f}ر.س",
                comp_url=comp_url or "",
            )
        except Exception:
            pass
        # toast يُعرض على مستوى الصفحة بعد إعادة الرسم
        st.session_state["_action_toast"] = (
            "success", f"✅ تم إرسال «{our_name}» ← {_tp:,.0f} ر.س"
        )
        # لا نستدعي st.rerun() هنا — الـ callback يُعيد الرسم تلقائياً
    else:
        _err_detail = _mk_res.get("message", "خطأ غير معروف")
        st.session_state[f"_act_{prefix}_{idx}"] = (
            "error", f"❌ فشل الإرسال إلى Make — {_err_detail}"
        )


def _cb_exclude(
    prefix: str, idx,
    our_name: str, our_price: float,
    comp_price: float, diff: float,
    comp_src: str, pid: str,
) -> None:
    """Callback: استبعاد المنتج وحفظه في DB عبر on_click."""
    st.session_state[f"excluded_{prefix}_{idx}"] = True
    st.session_state.hidden_products.add(f"{prefix}_{our_name}_{idx}")
    st.session_state.decisions_pending[our_name] = {
        "action": "removed", "reason": "استبعاد",
        "our_price": our_price, "comp_price": comp_price,
        "diff": diff, "competitor": comp_src,
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    try:
        _hk = f"{prefix}_{our_name}_{idx}"
        log_decision(our_name, prefix, "removed", "استبعاد",
                     our_price, comp_price, diff, comp_src)
        save_hidden_product(_hk, our_name, "removed")
        save_processed(
            _hk, our_name, comp_src, "removed",
            old_price=our_price, new_price=our_price, product_id=pid,
            notes=f"استبعاد من {prefix}",
        )
    except Exception:
        pass


# ════════════════════════════════════════════════
#  مكوّن جدول المقارنة البصري (مشترك)
# ════════════════════════════════════════════════
def render_pro_table_v32(_df, prefix, *args, **kwargs):
    """v32: نفس الجدول الاحترافي لكن ببطاقات Head-to-Head Arena (HTML نظيف)."""
    return render_pro_table(_df, prefix, *args, _use_v32_cards=True, **kwargs)


def render_pro_table(
        df, prefix, section_type="update", show_search=True,
        compact_cards=False, inline_filters=True, _use_v32_cards=False):
    """
    جدول احترافي بصري مع:
    - فلاتر ذكية (مكشوفة في شبكة أو داخل Expander)
    - أزرار AI + قرار لكل منتج (Event-Driven via on_click)
    - تصدير Make
    - Pagination
    """
    if df is None or df.empty:
        st.info("لا توجد منتجات")
        return

    # ── تطبيق الفلاتر العالمية (Global Quick-Filters من الشريط الجانبي) ──
    df = apply_global_filters(df)
    if df.empty:
        _gf_sum = get_active_filter_summary()
        st.info(f"لا توجد منتجات تطابق الفلاتر الحالية ({_gf_sum})" if _gf_sum
                else "لا توجد منتجات")
        return

    # ── Task 3.3: Soft-Delete filter — hide rows that were soft-deleted ───────
    # Loads the stable-key set once per render; O(1) per-row check via set lookup.
    # Stable key format: "softdel_{product_name}" — survives page/filter changes.
    _sd_keys = get_soft_deleted_product_keys()
    if _sd_keys and "المنتج" in df.columns:
        _before_sd = len(df)
        df = df[~df["المنتج"].apply(
            lambda _n: f"softdel_{_n}" in _sd_keys
        )].reset_index(drop=True)
        _sd_hidden = _before_sd - len(df)
        if _sd_hidden:
            st.caption(f"🗑️ {_sd_hidden} منتج محذوف (ناعم) — مخفي عن هذا القسم")
    if df.empty:
        st.info("لا توجد منتجات (تم حذف الكل ناعمياً — يمكن الاسترجاع من الأرشيف)")
        return

    # ── فلاتر ─────────────────────────────────
    opts = get_filter_options(df)
    # ملاحظة: الفلاتر ملفوفة بـ st.form حتى لا يُعاد رسم الصفحة عند كل ضغطة مفتاح
    # (تُطبَّق فقط عند الضغط على «تطبيق الفلاتر») — تحسين أداء كبير للقوائم الكبيرة.
    if inline_filters:
        st.markdown(
            '<div class="filter-inline-wrap">'
            '<div class="filter-inline-title">🔍 فلاتر — بحث، ماركة، منافس، نوع</div></div>',
            unsafe_allow_html=True,
        )
        with st.form(key=f"{prefix}_filters_form", border=False):
            # Row 1: text search + brand + competitor + type
            c1, c2, c3, c4 = st.columns([1.15, 1, 1, 1])
            search  = c1.text_input("🔎 بحث", key=f"{prefix}_s")
            brand_f = c2.selectbox("🏷️ الماركة", opts["brands"], key=f"{prefix}_b")
            comp_f  = c3.selectbox("🏪 المنافس", opts["competitors"], key=f"{prefix}_c")
            type_f  = c4.selectbox("🧴 النوع", opts["types"], key=f"{prefix}_t")
            # Row 2: match threshold + price range
            c5, c6, c7 = st.columns([1.2, 1, 1])
            match_min = c5.slider("أقل تطابق %", 0, 100, 0, key=f"{prefix}_m")
            price_min = c6.number_input("سعر من", 0.0, key=f"{prefix}_p1")
            price_max = c7.number_input("سعر إلى", 0.0, key=f"{prefix}_p2")
            # Row 3 (Task 3.1) — gender + size; shown only when columns exist in data
            _has_gender = "الجنس" in df.columns and len(opts["genders"]) > 1
            _has_size   = "الحجم" in df.columns  and len(opts["sizes"])   > 1
            if _has_gender or _has_size:
                c8, c9 = st.columns(2)
                gender_f = (
                    c8.selectbox("🚻 الجنس", opts["genders"], key=f"{prefix}_g")
                    if _has_gender else "الكل"
                )
                size_f = (
                    c9.selectbox("📦 الحجم (مل)", opts["sizes"], key=f"{prefix}_sz")
                    if _has_size else "الكل"
                )
            else:
                gender_f = "الكل"
                size_f   = "الكل"
            _fcb1, _fcb2 = st.columns([1.2, 4.8])
            with _fcb1:
                st.form_submit_button("🔍 تطبيق الفلاتر", use_container_width=True, type="primary")
            with _fcb2:
                st.form_submit_button("↩️ تحديث", use_container_width=True)
    else:
        with st.expander("🔍 فلاتر متقدمة", expanded=False):
            with st.form(key=f"{prefix}_filters_form_adv", border=False):
                # Row 1
                c1, c2, c3, c4 = st.columns(4)
                search  = c1.text_input("🔎 بحث", key=f"{prefix}_s")
                brand_f = c2.selectbox("🏷️ الماركة", opts["brands"], key=f"{prefix}_b")
                comp_f  = c3.selectbox("🏪 المنافس", opts["competitors"], key=f"{prefix}_c")
                type_f  = c4.selectbox("🧴 النوع", opts["types"], key=f"{prefix}_t")
                # Row 2
                c5, c6, c7 = st.columns(3)
                match_min = c5.slider("أقل تطابق%", 0, 100, 0, key=f"{prefix}_m")
                price_min = c6.number_input("سعر من", 0.0, key=f"{prefix}_p1")
                price_max = c7.number_input("سعر لـ", 0.0, key=f"{prefix}_p2")
                # Row 3 (Task 3.1) — gender + size
                _has_gender = "الجنس" in df.columns and len(opts["genders"]) > 1
                _has_size   = "الحجم" in df.columns  and len(opts["sizes"])   > 1
                if _has_gender or _has_size:
                    c8, c9 = st.columns(2)
                    gender_f = (
                        c8.selectbox("🚻 الجنس", opts["genders"], key=f"{prefix}_g")
                        if _has_gender else "الكل"
                    )
                    size_f = (
                        c9.selectbox("📦 الحجم (مل)", opts["sizes"], key=f"{prefix}_sz")
                        if _has_size else "الكل"
                    )
                else:
                    gender_f = "الكل"
                    size_f   = "الكل"
                st.form_submit_button("🔍 تطبيق الفلاتر", use_container_width=True, type="primary")

    filters = {
        "search":    search,
        "brand":     brand_f,
        "competitor": comp_f,
        "type":      type_f,
        "gender":    gender_f,   # Task 3.1
        "size":      size_f,     # Task 3.1
        "match_min": match_min if match_min > 0 else None,
        "price_min": price_min if price_min > 0 else 0.0,
        "price_max": price_max if price_max > 0 else None,
    }
    filtered = apply_filters(df, filters)

    # ── الشرط 11: فلتر «تغيّر سعره» / «منتج جديد» (يظهر بعد تحليل تراكمي) ──
    if "حالة_التغيير" in filtered.columns and filtered["حالة_التغيير"].astype(str).str.strip().ne("").any():
        _new_n = int((filtered["حالة_التغيير"] == "🆕 جديد").sum())
        _chg_n = int((filtered["حالة_التغيير"] == "🔄 تغيّر السعر").sum())
        _cs_sel = st.radio(
            "🔔 فلتر التغيير (مقارنةً بالتحليل السابق)",
            ["الكل", f"🆕 جديد ({_new_n})", f"🔄 تغيّر السعر ({_chg_n})"],
            horizontal=True, key=f"{prefix}_change_filter",
        )
        if _cs_sel.startswith("🆕"):
            filtered = filtered[filtered["حالة_التغيير"] == "🆕 جديد"]
        elif _cs_sel.startswith("🔄"):
            filtered = filtered[filtered["حالة_التغيير"] == "🔄 تغيّر السعر"]

    # ── شريط شارات الفلاتر الفعّالة ──
    _chips_html = render_active_filter_chips_html({
        "search":    search,
        "brand":     brand_f,
        "comp":      comp_f,
        "price_min": price_min if price_min > 0 else None,
        "price_max": price_max if price_max > 0 else None,
        "status":    type_f if type_f and type_f != "الكل" else "",
    })
    if _chips_html:
        st.markdown(_chips_html, unsafe_allow_html=True)

    # ── v32: Priority Score + Smart Sorting ──
    filtered = filtered.copy()
    filtered['_priority'] = filtered.apply(_calc_priority_score, axis=1)
    filtered = filtered.sort_values('_priority', ascending=False).reset_index(drop=True)


    # ── شريط الأدوات ───────────────────────────
    ac1, ac2, ac3, ac4, ac5 = st.columns(5)
    with ac1:
        _exdf = filtered.copy()
        if "جميع المنافسين" in _exdf.columns: _exdf = _exdf.drop(columns=["جميع المنافسين"])
        if "جميع_المنافسين" in _exdf.columns: _exdf = _exdf.drop(columns=["جميع_المنافسين"])
        if "_priority" in _exdf.columns: _exdf = _exdf.drop(columns=["_priority"])
        excel_data = export_to_excel(_exdf, prefix)
        st.download_button("📥 Excel", data=excel_data,
            file_name=f"{prefix}_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"{prefix}_xl",
            )
    with ac2:
        _csdf = filtered.copy()
        if "جميع المنافسين" in _csdf.columns: _csdf = _csdf.drop(columns=["جميع المنافسين"])
        if "جميع_المنافسين" in _csdf.columns: _csdf = _csdf.drop(columns=["جميع_المنافسين"])
        if "_priority" in _csdf.columns: _csdf = _csdf.drop(columns=["_priority"])
        _csv_bytes = _csdf.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("📄 CSV", data=_csv_bytes,
            file_name=f"{prefix}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv", key=f"{prefix}_csv",
            )
    with ac3:
        _bulk_labels = {"raise": "🤖 تحليل ذكي — خفض (أول 20)",
                        "lower": "🤖 تحليل ذكي — رفع (أول 20)",
                        "review": "🤖 تحقق جماعي (أول 20)",
                        "approved": "🤖 مراجعة (أول 20)"}
        if st.button(_bulk_labels.get(prefix, "🤖 AI جماعي (أول 20)"), key=f"{prefix}_bulk"):
            with st.spinner("🤖 AI يحلل البيانات..."):
                _section_map = {"raise": "price_raise", "lower": "price_lower",
                                "review": "review", "approved": "approved"}
                items = [{
                    "our": str(r.get("المنتج", "")),
                    "comp": str(r.get("منتج_المنافس", "")),
                    "our_price": safe_float(r.get("السعر", 0)),
                    "comp_price": safe_float(r.get("سعر_المنافس", 0))
                } for _, r in filtered.head(20).iterrows()]
                res = bulk_verify(items, _section_map.get(prefix, "general"))
                st.markdown(f'<div class="ai-box">{_html_mod.escape(str(res["response"]))}</div>',
                            unsafe_allow_html=True)
    with ac4:
        if section_type == "excluded":
            st.caption("إرسال Make غير متاح لهذا القسم")
        elif st.button("📤 إرسال كل لـ Make", key=f"{prefix}_make_all"):
            products = export_to_make_format(filtered, section_type)
            if section_type in ("missing", "new"):
                res = send_new_products(products)
            else:
                res = send_price_updates(products)
            _mk_status = int(res.get("status_code") or 0)  # FIX: Transparency & Reversibility
            _mk_ok = bool(res.get("success")) and _mk_status in (200, 201, 202, 204)  # FIX: Transparency & Reversibility
            if _mk_ok:
                if section_type in ("missing", "new"):  # FIX: Smart Workflow & AI Tracking
                    if "رابط_المنافس" in filtered.columns:
                        for _u in filtered["رابط_المنافس"].dropna().astype(str):
                            _track_processed_missing_url(_u)
                else:
                    if "معرف_المنتج" in filtered.columns:
                        for _pid in filtered["معرف_المنتج"].dropna().astype(str):
                            _track_processed_price_sku(_pid)
                st.success(res["message"])
                # v26: سجّل كل منتج في processed_products
                for _i, (_idx, _r) in enumerate(filtered.iterrows()):
                    _pname = str(_r.get("المنتج", _r.get("منتج_المنافس", "")))
                    _pkey  = f"{prefix}_{_pname}_{_i}"
                    _pid_r = str(_r.get("معرف_المنتج", _r.get("معرف_المنافس", "")))
                    _comp  = str(_r.get("المنافس",""))
                    _op    = safe_float(_r.get("السعر", _r.get("سعر_المنافس", 0)))
                    _np    = safe_float(_r.get("سعر_المنافس", _r.get("السعر", 0)))
                    st.session_state.hidden_products.add(_pkey)
                    save_hidden_product(_pkey, _pname, "sent_to_make_bulk")
                    save_processed(_pkey, _pname, _comp, "send_price",
                                   old_price=_op, new_price=_np,
                                   product_id=_pid_r,
                                   notes=f"إرسال جماعي ← {prefix}")
                st.rerun()
            else:
                st.error(f"❌ فشل الإرسال إلى Make: {res.get('message', 'خطأ غير معروف')}")  # FIX: Transparency & Reversibility
    with ac5:
        # جمع القرارات المعلقة وإرسالها
        pending = {k: v for k, v in st.session_state.decisions_pending.items()
                   if v["action"] in ["approved", "deferred", "removed"]}
        if pending and st.button(f"📦 ترحيل {len(pending)} قرار → Make", key=f"{prefix}_send_decisions"):
            to_send = [{"name": k, "action": v["action"], "reason": v.get("reason", "")}
                       for k, v in pending.items()]
            res = send_price_updates(to_send)
            st.success(f"✅ تم إرسال {len(to_send)} قرار لـ Make")
            # v26: سجّل القرارات المعلقة في processed_products
            for k, v in pending.items():
                _pkey = f"decision_{k}"
                _act  = v.get("action","approved")
                save_processed(_pkey, k, v.get("competitor",""), _act,
                               old_price=safe_float(v.get("our_price",0)),
                               new_price=safe_float(v.get("comp_price",0)),
                               notes=f"قرار معلق → Make | {v.get('reason','')}")
            st.session_state.decisions_pending = {}
            st.rerun()

    # FIX: Transparency & Reversibility
    _hidden_in_view = 0
    for _idx, _row in filtered.iterrows():
        _our_name_h = str(_row.get("المنتج", "—"))
        _hide_key_h = f"{prefix}_{_our_name_h}_{_idx}"
        if _hide_key_h in st.session_state.hidden_products:
            _hidden_in_view += 1
            continue
        if prefix in ("raise", "lower") and st.session_state.get(f"excluded_{prefix}_{_idx}"):
            _hidden_in_view += 1
    _show_transparency_counter(len(df), max(0, len(filtered) - _hidden_in_view))
    st.caption(f"عرض {len(filtered)} من {len(df)} منتج — {datetime.now().strftime('%H:%M:%S')}")

    # ── v33: تنقل موحّد بأسهم وأرقام صفحات ──
    # ⚡ 15 بدل 25/صفحة: كل منتج ~26-33 ودجت → تقليل ~40% من عناصر الصفحة = رسم أسرع
    start_idx, end_idx, _pg_num = render_pagination(len(filtered), 15, f"{prefix}_pro")
    page_df = filtered.iloc[start_idx:end_idx]


    # ── Task 3.2: Select-All / Deselect-All buttons ───────────────────────────
    # These set checkbox widget state BEFORE the widgets are rendered, which is
    # valid in Streamlit: the keys exist in session_state from the previous cycle.
    _sa_col, _da_col, _sp = st.columns([1, 1, 6])
    with _sa_col:
        if st.button("☑️ تحديد الكل", key=f"{prefix}_sel_all", use_container_width=True):
            for _si in page_df.index:
                st.session_state[f"sel_{prefix}_{_si}"] = True
            st.rerun()
    with _da_col:
        if st.button("⬜ إلغاء الكل", key=f"{prefix}_desel_all", use_container_width=True):
            for _si in page_df.index:
                st.session_state[f"sel_{prefix}_{_si}"] = False
            st.rerun()

    # ── Task 3.2: Bulk Action Bar (إجراءات جماعية حقيقية — لا stubs) ────────────
    # Reads checkbox state from the PREVIOUS render cycle (standard Streamlit pattern).
    _sel_indices = [
        _si for _si in page_df.index
        if st.session_state.get(f"sel_{prefix}_{_si}", False)
    ]
    _n_sel = len(_sel_indices)

    if _n_sel > 0:
        st.markdown(
            f"<div style='background:#0d2a1a;border:2px solid #00C853;border-radius:10px;"
            f"padding:10px 16px;margin:8px 0;display:flex;align-items:center;gap:12px;"
            f"flex-wrap:wrap'>"
            f"<span style='color:#00C853;font-weight:700;font-size:1rem'>"
            f"✅ {_n_sel} منتج محدد</span>"
            f"<span style='color:#607d8b;font-size:.8rem'>"
            f"(اختر إجراءً من الأزرار أدناه)</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        _ba1, _ba2, _ba4 = st.columns(3)
        with _ba1:
            # Task 3.3 — Soft Delete: persists in DB; hidden immediately; restorable
            if st.button(
                f"🗑️ حذف المحدد ({_n_sel})",
                key=f"{prefix}_bulk_del",
                use_container_width=True,
            ):
                _del_count = 0
                for _si in _sel_indices:
                    if _si not in page_df.index:
                        continue
                    _del_row  = page_df.loc[_si]
                    _del_name = str(_del_row.get("المنتج", "") or "")
                    if not _del_name or _del_name in ("—", "nan", "None"):
                        continue
                    # Persist soft-delete with stable key (not idx-based)
                    _sd_key = f"softdel_{_del_name}"
                    soft_delete_product(_sd_key, _del_name)
                    # Also mark in session_state hidden_products for immediate hiding
                    # using both the stable key and the legacy idx-based key
                    st.session_state.hidden_products.add(_sd_key)
                    st.session_state.hidden_products.add(f"{prefix}_{_del_name}_{_si}")
                    # Clear checkbox state
                    st.session_state[f"sel_{prefix}_{_si}"] = False
                    _del_count += 1
                if _del_count:
                    st.success(
                        f"🗑️ تم حذف {_del_count} منتج ناعمياً — "
                        f"يمكن الاسترجاع من الأرشيف (Task 3.4)",
                        icon="✅",
                    )
                    st.rerun()
        with _ba2:
            # تصدير حقيقي للصفوف المحددة (CSV) — download_button يُنزّل عند الضغط
            _sel_in_page = [i for i in _sel_indices if i in page_df.index]
            _sel_df_exp = page_df.loc[_sel_in_page].copy() if _sel_in_page else pd.DataFrame()
            for _drop in ("جميع_المنافسين", "جميع المنافسين", "_priority"):
                if _drop in _sel_df_exp.columns:
                    _sel_df_exp = _sel_df_exp.drop(columns=[_drop])
            _sel_csv = _sel_df_exp.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                f"📥 تصدير المحدد ({_n_sel})",
                data=_sel_csv,
                file_name=f"mahwous_{prefix}_selected.csv",
                mime="text/csv; charset=utf-8",
                use_container_width=True,
                key=f"{prefix}_bulk_export_dl",
            )
        with _ba4:
            if st.button(
                "❌ إلغاء التحديد",
                key=f"{prefix}_bulk_clear",
                use_container_width=True,
            ):
                for _si in page_df.index:
                    st.session_state[f"sel_{prefix}_{_si}"] = False
                st.rerun()

    # ── الجدول البصري ─────────────────────
    for idx, row in page_df.iterrows():
        our_name   = str(row.get("المنتج", "—"))
        # تخطي المنتجات التي أُرسلت لـ Make أو أُزيلت
        _hide_key = f"{prefix}_{our_name}_{idx}"
        if _hide_key in st.session_state.hidden_products:
            continue
        if prefix in ("raise", "lower") and st.session_state.get(f"excluded_{prefix}_{idx}"):
            continue
        comp_name  = str(row.get("منتج_المنافس", "—"))
        our_price  = safe_float(row.get("السعر", 0))
        comp_price = safe_float(row.get("سعر_المنافس", 0))
        diff       = safe_float(row.get("الفرق", our_price - comp_price))
        match_pct  = safe_float(row.get("نسبة_التطابق", 0))
        all_comps  = _normalize_all_competitors(row.get("جميع_المنافسين", row.get("جميع المنافسين", [])))
        comp_src   = _display_competitor_name(row)
        brand      = str(row.get("الماركة", ""))
        size       = row.get("الحجم", "")
        ptype      = str(row.get("النوع", ""))
        risk       = str(row.get("الخطورة", ""))
        decision   = str(row.get("القرار", ""))
        ts_now     = datetime.now().strftime("%Y-%m-%d %H:%M")
        _is_excluded = "مستبعد" in decision
        _vs_border = "#9e9e9e" if _is_excluded else None
        _vs_row_bg = "rgba(245,245,245,0.07)" if _is_excluded else None

        # سحب رقم المنتج من جميع الأعمدة المحتملة
        _pid_raw = (
            row.get("معرف_المنتج", "") or
            row.get("product_id", "") or
            row.get("رقم المنتج", "") or
            row.get("رقم_المنتج", "") or
            row.get("معرف المنتج", "") or ""
        )
        _pid_str = ""
        if _pid_raw and str(_pid_raw) not in ("", "nan", "None", "0"):
            try: _pid_str = str(int(float(str(_pid_raw))))
            except Exception: _pid_str = str(_pid_raw)

        _our_img_v, _comp_img_v = row_media_urls_from_analysis(row)
        _comp_url_v = competitor_product_url_from_row(row)
        _our_url_v = our_product_url_from_row(row)

        # Task 3.2: per-product selection checkbox (left column) + VS card (right column).
        # Only the VS card HTML is wrapped in the narrow column layout; all action
        # widgets below remain at full width so the existing layout is preserved.
        _vs_compact = bool(compact_cards and prefix == "raise")
        if _use_v32_cards:
            # v32: بطاقة Arena من styles.py — تقرأ الأعمدة العربية مباشرةً
            from styles import _build_single_card_html as _v32_card
            _vs_html = _v32_card({
                "المنتج": our_name, "السعر": our_price,
                "منتج_المنافس": comp_name, "سعر_المنافس": comp_price, "الفرق": diff,
                "المنافس": comp_src, "معرف_المنتج": _pid_str,
                "صورة_منتجنا": _our_img_v, "صورة_المنافس": _comp_img_v,
                "رابط_منتجنا": _our_url_v, "رابط_المنافس": _comp_url_v,
                "جميع_المنافسين": all_comps, "الماركة": brand,
                "الحجم": str(size) if size else "", "نسبة_التطابق": match_pct,
                "الخطورة": risk, "تاريخ_المطابقة": str(row.get("تاريخ_المطابقة", "")),
                "سبب_التصنيف": row.get("سبب_التصنيف", row.get("سبب", "")),
            })
        else:
            _vs_html = vs_card(our_name, our_price, comp_name,
                               comp_price, diff, comp_src, _pid_str,
                               our_img=_our_img_v, comp_img=_comp_img_v,
                               comp_url=_comp_url_v, our_url=_our_url_v,
                               accent_border=_vs_border, row_bg=_vs_row_bg,
                               compact=_vs_compact,
                               all_comps=all_comps,
                               brand=brand, size=str(size) if size else "",
                               match_score=match_pct, risk=risk,
                               match_date=str(row.get("تاريخ_المطابقة", "")))
        _sel_key = f"sel_{prefix}_{idx}"
        _chk_col, _card_col = st.columns([0.05, 0.95], gap="small")
        with _chk_col:
            st.markdown(
                "<div style='padding-top:28px'></div>",
                unsafe_allow_html=True,
            )
            st.checkbox(
                "تحديد",
                key=_sel_key,
                label_visibility="collapsed",
                help=f"تحديد: {our_name[:50]}",
            )
        with _card_col:
            st.markdown(_vs_html, unsafe_allow_html=True)

        # ── شريط الإجراءات التفاعلي (Event-Driven via on_click) ─────────
        if prefix in ("raise", "lower"):
            st.write("")
            _suggested = float(comp_price) - 1.0 if comp_price > 0 else float(our_price)
            if _suggested <= 0:
                _suggested = float(our_price)

            # pid يُحسب هنا لأنه مطلوب كـ arg للـ Callbacks
            _pid_cb_raw = (
                row.get("معرف_المنتج", "") or row.get("product_id", "")
                or row.get("رقم المنتج", "") or row.get("رقم_المنتج", "")
                or row.get("معرف المنتج", "") or ""
            )
            try:
                _fv_cb = float(_pid_cb_raw)
                _pid_cb = str(int(_fv_cb)) if _fv_cb == int(_fv_cb) else str(_pid_cb_raw)
            except (ValueError, TypeError):
                _pid_cb = str(_pid_cb_raw).strip()
            if _pid_cb in ("nan", "None", "NaN", ""):
                _pid_cb = ""

            # رقم المنتج No. من كتالوج متجرنا (Primary Key في Make/سلة)
            _no_raw = (
                row.get("No.", "") or row.get("NO", "") or row.get("no", "")
                or row.get("No", "") or row.get("رقم_المنتج", "")
                or row.get("رقم المنتج", "") or ""
            )
            try:
                _fv_no = float(_no_raw)
                _no_cb = str(int(_fv_no)) if _fv_no == int(_fv_no) else str(_no_raw)
            except (ValueError, TypeError):
                _no_cb = str(_no_raw).strip()
            if _no_cb in ("nan", "None", "NaN", ""):
                _no_cb = ""

            _comp_url_make = (_comp_url_v or str(row.get("رابط_المنافس", "") or "")).strip()

            act_col1, act_col2, act_col3, _act_sp = st.columns([2.5, 2.5, 2, 4])
            with act_col1:
                st.number_input(
                    "🎯 السعر المستهدف (ر.س)",
                    value=float(_suggested),
                    min_value=0.0,
                    step=1.0,
                    key=f"target_price_{prefix}_{idx}",
                )
            with act_col2:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                st.button(
                    "🚀 تحديث السعر (Make)",
                    key=f"send_make_{prefix}_{idx}",
                    type="primary",
                    use_container_width=True,
                    on_click=_cb_send_make,
                    args=(
                        prefix, idx, our_name, comp_name,
                        our_price, comp_price, diff,
                        decision, comp_src, _pid_cb, _comp_url_make,
                        _no_cb,
                    ),
                )
            with act_col3:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                st.button(
                    "🗑️ استبعاد",
                    key=f"reject_bar_{prefix}_{idx}",
                    use_container_width=True,
                    on_click=_cb_exclude,
                    args=(
                        prefix, idx, our_name, our_price,
                        comp_price, diff, comp_src, _pid_cb,
                    ),
                )
            # عرض نتيجة الإجراء (خطأ فقط؛ النجاح يُعرض كـ toast أعلى الصفحة)
            _act_res = st.session_state.pop(f"_act_{prefix}_{idx}", None)
            if _act_res:
                _atype, _amsg = _act_res
                st.error(_amsg) if _atype == "error" else st.success(_amsg)

            _hr_act = (
                '<hr style="border:none;border-top:1px solid #2a2a3d;margin:10px 0 14px">'
                if _vs_compact
                else "<hr style='margin:16px 0;border-top:2px dashed rgba(238,238,238,.25);'>"
            )
            st.markdown(_hr_act, unsafe_allow_html=True)

        # ── تعريف الأعمدة (b1..ba) لجميع الأقسام لضمان عدم حدوث UnboundLocalError ──
        if prefix in ("raise", "lower"):
            # b1:AI, b2:Market, b3:OK, b4:Defer, b9:History, ba:Analyze
            # (زر «🔍 تحقق» b8 أُزيل — مكرر وظيفياً مع b1 الذي يستدعي verify_match نفسه)
            b1, b2, b3, b4, b9, ba = st.columns([1, 1, 1, 1, 1, 1])
        elif prefix == "approved":
            # b1:AI, b2:Market, b3:OK, b4:Defer, b5:Remove, b6:Price, b7:Make
            b1, b2, b3, b4, b5, b6, b7 = st.columns(7)
        else:
            # b1..ba (9 columns) — b8 (تحقق) أُزيل لأنه مكرر مع b1
            b1, b2, b3, b4, b5, b6, b7, b9, ba = st.columns([1, 1, 1, 1, 1, 1, 1, 1, 1])

        with b1:  # AI تحقق ذكي — يُصحح القسم
            _ai_label = {"raise": "🤖 هل نخفض؟", "lower": "🤖 هل نرفع؟",
                         "review": "🤖 هل يطابق؟", "approved": "🤖 تحقق"}.get(prefix, "🤖 تحقق")
            if st.button(_ai_label, key=f"v_{prefix}_{idx}"):
                with st.spinner("🤖 AI يحلل ويتحقق..."):
                    r = verify_match(our_name, comp_name, our_price, comp_price)
                    if r.get("success"):
                        icon = "✅" if r.get("match") else "❌"
                        conf = r.get("confidence", 0)
                        reason = r.get("reason","")[:200]
                        correct_sec = r.get("correct_section","")
                        suggested_price = r.get("suggested_price", 0)

                        # تحديد القسم الحالي من prefix
                        current_sec_map = {
                            "raise": "🔴 سعر أعلى",
                            "lower": "🟢 سعر أقل",
                            "approved": "✅ موافق",
                            "review": "⚠️ تحت المراجعة",
                            "excluded": "⚪ مستبعد (لا يوجد تطابق)",
                        }
                        current_sec = current_sec_map.get(prefix, "")

                        # هل AI يوافق على القسم الحالي؟
                        section_ok = True
                        if correct_sec and current_sec:
                            # مقارنة مبسطة
                            if ("اعلى" in correct_sec or "أعلى" in correct_sec) and prefix != "raise":
                                section_ok = False
                            elif ("اقل" in correct_sec or "أقل" in correct_sec) and prefix != "lower":
                                section_ok = False
                            elif "موافق" in correct_sec and prefix != "approved":
                                section_ok = False
                            elif ("مفقود" in correct_sec or "🔵" in correct_sec) and r.get("match") == False:
                                section_ok = False

                        if r.get("match"):
                            # مطابقة صحيحة — عرض نتيجة السعر
                            diff_info = ""
                            if prefix == "raise":
                                diff_info = f"\n\n💡 **توصية:** {'خفض السعر' if diff > 20 else 'إبقاء السعر'}"
                            elif prefix == "lower":
                                diff_info = f"\n\n💡 **توصية:** {'رفع السعر' if abs(diff) > 20 else 'إبقاء السعر'}"
                            if suggested_price > 0:
                                diff_info += f"\n💰 **السعر المقترح: {suggested_price:,.0f} ر.س**"

                            st.success(f"{icon} **تطابق {conf}%** — المطابقة صحيحة\n\n{reason}{diff_info}")

                            if not section_ok:
                                st.warning(f"⚠️ AI يرى أن هذا المنتج يجب أن يكون في قسم: **{correct_sec}**")
                        else:
                            # مطابقة خاطئة — تنبيه
                            st.error(f"{icon} **المطابقة خاطئة** ({conf}%)\n\n{reason}")
                            st.warning("🔵 هذا المنتج يجب أن يكون في **المنتجات المفقودة**")
                    else:
                        st.error("فشل AI")

        with b2:  # بحث سعر السوق ذكي
            _mkt_label = {"raise": "🌐 سعر عادل؟", "lower": "🌐 فرصة رفع؟"}.get(prefix, "🌐 سوق")
            if st.button(_mkt_label, key=f"mkt_{prefix}_{idx}"):
                with st.spinner("🌐 يبحث في السوق السعودي..."):
                    r = search_market_price(our_name, our_price)
                    if r.get("success"):
                        mp  = r.get("market_price", 0)
                        rng = r.get("price_range", {})
                        rec = r.get("recommendation", "")[:250]
                        web_ctx = r.get("web_context","")
                        comps = r.get("competitors", [])
                        conf = r.get("confidence", 0)

                        _verdict = ""
                        if prefix == "raise" and mp > 0:
                            _verdict = "✅ سعرنا ضمن السوق" if our_price <= mp * 1.1 else "⚠️ سعرنا أعلى من السوق — يُنصح بالخفض"
                        elif prefix == "lower" and mp > 0:
                            _gap = mp - our_price
                            _verdict = f"💰 فرصة رفع ~{_gap:.0f} ر.س" if _gap > 10 else "✅ سعرنا قريب من السوق"

                        _comps_txt = ""
                        if comps:
                            _comps_txt = "\n\n**منافسون:**\n" + "\n".join(
                                f"• {c.get('name','')}: {c.get('price',0):,.0f} ر.س" for c in comps[:3]
                            )

                        _price_range = f"{rng.get('min',0):.0f}–{rng.get('max',0):.0f}" if rng else "—"
                        st.info(
                            f"💹 **سعر السوق: {mp:,.0f} ر.س** ({_price_range} ر.س)\n\n"
                            f"{rec}{_comps_txt}\n\n{'**' + _verdict + '**' if _verdict else ''}"
                        )
                        if web_ctx:
                            with st.expander("🔍 مصادر البحث"):
                                st.caption(web_ctx)
                    else:
                        st.warning("تعذر البحث في السوق")

        with b3:  # موافق
            if st.button("✅ موافق", key=f"ok_{prefix}_{idx}"):
                st.session_state.decisions_pending[our_name] = {
                    "action": "approved", "reason": "موافقة يدوية",
                    "our_price": our_price, "comp_price": comp_price,
                    "diff": diff, "competitor": comp_src,
                    "ts": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                log_decision(our_name, prefix, "approved",
                             "موافقة يدوية", our_price, comp_price, diff, comp_src)
                _hk3 = f"{prefix}_{our_name}_{idx}"
                st.session_state.hidden_products.add(_hk3)
                save_hidden_product(_hk3, our_name, "approved")
                # ── توجيه آلي → تمت المعالجة ──
                _auto_route_to_processed(
                    our_name, str(row.get("معرف_المنتج","")),
                    comp_src, "approved",
                    old_price=our_price, new_price=our_price,
                    notes=f"موافق من {prefix}",
                )
                st.rerun()

        with b4:  # تأجيل
            if st.button("⏸️ تأجيل", key=f"df_{prefix}_{idx}"):
                st.session_state.decisions_pending[our_name] = {
                    "action": "deferred", "reason": "تأجيل",
                    "our_price": our_price, "comp_price": comp_price,
                    "diff": diff, "competitor": comp_src,
                    "ts": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                log_decision(our_name, prefix, "deferred",
                             "تأجيل", our_price, comp_price, diff, comp_src)
                st.warning("⏸️")

        if prefix not in ("raise", "lower"):
            with b5:  # إزالة
                if st.button("🗑️ إزالة", key=f"rm_{prefix}_{idx}"):
                    st.session_state.decisions_pending[our_name] = {
                        "action": "removed", "reason": "إزالة",
                        "our_price": our_price, "comp_price": comp_price,
                        "diff": diff, "competitor": comp_src,
                        "ts": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }
                    log_decision(our_name, prefix, "removed",
                                 "إزالة", our_price, comp_price, diff, comp_src)
                    _hk = f"{prefix}_{our_name}_{idx}"
                    st.session_state.hidden_products.add(_hk)
                    save_hidden_product(_hk, our_name, "removed")
                    save_processed(_hk, our_name, comp_src, "removed",
                                   old_price=our_price, new_price=our_price,
                                   product_id=str(row.get("معرف_المنتج","")),
                                   notes=f"إزالة من {prefix}")
                    st.rerun()

            with b6:  # سعر يدوي
                _auto_price_row = round(comp_price - 1, 2) if comp_price > 0 else our_price
                _custom_price = st.number_input(
                    "سعر", value=_auto_price_row, min_value=0.0,
                    step=1.0, key=f"cp_{prefix}_{idx}",
                    label_visibility="collapsed"
                )

            with b7:  # تصدير Make
                if st.button("📤 Make", key=f"mk_{prefix}_{idx}"):
                    _pid_raw = (
                        row.get("معرف_المنتج", "") or
                        row.get("product_id", "") or
                        row.get("رقم المنتج", "") or
                        row.get("رقم_المنتج", "") or
                        row.get("معرف المنتج", "") or ""
                    )
                    try:
                        _fv = float(_pid_raw)
                        _pid = str(int(_fv)) if _fv == int(_fv) else str(_pid_raw)
                    except (ValueError, TypeError):
                        _pid = str(_pid_raw).strip()
                    if _pid in ("nan", "None", "NaN", ""):
                        _pid = ""
                    # رقم المنتج NO. من كتالوج سلة (Primary Key)
                    _no_raw_b7 = (
                        row.get("No.", "") or row.get("NO", "") or row.get("no", "")
                        or row.get("No", "") or row.get("رقم_المنتج", "") or ""
                    )
                    try:
                        _fv_no = float(_no_raw_b7)
                        _no_b7 = str(int(_fv_no)) if _fv_no == int(_fv_no) else str(_no_raw_b7)
                    except (ValueError, TypeError):
                        _no_b7 = str(_no_raw_b7).strip()
                    if _no_b7 in ("nan", "None", "NaN", ""):
                        _no_b7 = ""
                    _final_price = _custom_price if _custom_price > 0 else _auto_price_row
                    res = send_single_product({
                        "NO":         _no_b7 or _pid,
                        "product_id": _pid,
                        "name": our_name, "price": _final_price,
                        "comp_name": comp_name, "comp_price": comp_price,
                        "diff": diff, "decision": decision, "competitor": comp_src
                    })
                    if res["success"]:
                        _hk = f"{prefix}_{our_name}_{idx}"
                        _track_processed_price_sku(_pid)  # FIX: Smart Workflow & AI Tracking
                        st.session_state.hidden_products.add(_hk)
                        save_hidden_product(_hk, our_name, "sent_to_make")
                        # ── توجيه آلي → تمت المعالجة ──
                        _auto_route_to_processed(
                            our_name, _pid,
                            comp_src, "send_price",
                            old_price=our_price, new_price=_final_price,
                            notes=f"إرسال لـ Make من {prefix}",
                        )
                        st.success(f"✅ تم الإرسال: {_pid}")
                        st.rerun()

        if prefix != "approved":
            with b9:  # تاريخ السعر
                if st.button("📈 تاريخ", key=f"ph_{prefix}_{idx}"):
                    history = get_price_history(our_name, comp_src)
                    if history:
                        rows_h = [f"📅 {h['date']}: {h['price']:,.0f} ر.س" for h in history[:5]]
                        st.info("\n".join(rows_h))
                    else:
                        st.info("لا يوجد تاريخ بعد")

            with ba:  # 📊 تحليل المنتج الموضعي
                if st.button("📊 تحليل", key=f"analyze_{prefix}_{idx}",
                             help="تحليل شامل: سعر + مطابقة + قسم صحيح"):
                    _section_map_an = {
                        "raise": "price_raise", "lower": "price_lower",
                        "approved": "approved", "review": "review",
                        "excluded": "excluded",
                    }
                    with st.spinner("🔍 يتم التحليل الآن..."):
                        an_res = analyze_product_inline(row, _section_map_an.get(prefix, prefix))
                        render_analysis_result(an_res)

        # ── Task 3.5 & 3.6 — Inline Edit + Force Link ────────────────────────
        _edit_col, _link_col, _spacer35 = st.columns([1.5, 1.5, 7])

        with _edit_col:
            try:
                _pop_edit = st.popover("✏️ تعديل", use_container_width=True)
            except Exception:
                _pop_edit = st.expander("✏️ تعديل")
            with _pop_edit:
                st.markdown(f"**تعديل:** {our_name}")
                _ov_key35 = f"edit_{our_name}"
                _edit_name35 = st.text_input(
                    "الاسم الجديد",
                    value=our_name,
                    key=f"edit_name_{prefix}_{idx}",
                    placeholder="اتركه فارغاً للإبقاء على الأصلي",
                )
                _edit_price35 = st.number_input(
                    "السعر الجديد (ر.س)",
                    value=float(our_price or 0),
                    min_value=0.0,
                    step=1.0,
                    key=f"edit_price_{prefix}_{idx}",
                )
                _edit_url35 = st.text_input(
                    "الرابط الجديد",
                    value="",
                    key=f"edit_url_{prefix}_{idx}",
                    placeholder="https://...",
                )
                if st.button("💾 حفظ", key=f"save_edit_{prefix}_{idx}", type="primary"):
                    _ok35 = update_product_data(
                        _ov_key35,
                        _edit_name35.strip() or our_name,
                        _edit_price35,
                        _edit_url35.strip(),
                    )
                    if _ok35:
                        st.success("✅ تم الحفظ")
                        st.rerun()
                    else:
                        st.error("❌ فشل الحفظ")

        with _link_col:
            try:
                _pop_link = st.popover("🔗 ربط يدوي", use_container_width=True)
            except Exception:
                _pop_link = st.expander("🔗 ربط يدوي")
            with _pop_link:
                st.markdown(f"**ربط:** {our_name}")
                _fl_url35 = st.text_input(
                    "رابط منتج المنافس",
                    key=f"fl_url_{prefix}_{idx}",
                    placeholder="https://competitor.com/product/...",
                )
                st.caption("سيُسجَّل كمطابقة مؤكدة (source=manual)")
                _pid_fl35 = str(
                    row.get("معرف_المنتج", "")
                    or row.get("product_id", "")
                    or ""
                ).strip()
                if st.button("🔗 تأكيد", key=f"confirm_fl_{prefix}_{idx}", type="primary"):
                    if _fl_url35.startswith("http"):
                        _ok_fl = force_link_product(_pid_fl35, our_name, _fl_url35.strip())
                        if _ok_fl:
                            st.success("✅ تم الربط")
                            st.rerun()
                        else:
                            st.error("❌ فشل الربط")
                    else:
                        st.warning("⚠️ رابط غير صحيح")

        _hr_m = "3px 0" if (compact_cards and prefix == "raise") else "6px 0"
        st.markdown(
            f'<hr style="border:none;border-top:1px solid #1a1a2e;margin:{_hr_m}">',
            unsafe_allow_html=True,
        )

    # ── v32: Bottom Pagination ───────────────
    _btm_tp = max(1, (len(filtered) + 24) // 25)
    if _btm_tp > 1:
        _bpg1, _bpg2, _bpg3 = st.columns([1, 2, 1])
        with _bpg2:
            st.markdown(
                f'<div style="text-align:center;padding:12px;background:#111827;border-radius:10px;'
                f'border:1px solid #1F293788;margin-top:8px">'
                f'<span style="color:#9CA3AF;font-size:.85rem">'
                f'صفحة {_pg_num} من {_btm_tp} '
                f'| إجمالي {len(filtered)} منتج</span></div>',
                unsafe_allow_html=True,
            )



# ════════════════════════════════════════════════
# ════════════════════════════════════════════════
#  نظام التوجيه الآلي (Auto-Routing)
# ════════════════════════════════════════════════
def _auto_route_to_processed(our_name, our_id, comp_src, status, old_price=0, new_price=0, notes=""):
    """نقل المنتج تلقائياً إلى 'تمت المعالجة' وحفظ حالته في DB."""
    try:
        # 1. حفظ في جدول المعالجة
        # FIX: use keyword args to match save_processed() signature correctly
        save_processed(
            product_key=our_id or our_name,
            product_name=our_name,
            competitor=comp_src,
            action=status,
            old_price=old_price,
            new_price=new_price,
            product_id=our_id,
            notes=notes,
        )
        # 2. إخفاء من الواجهة (حفظ في جدول المنتجات المخفية)
        save_hidden_product(our_id, our_name, "approved")
        return True
    except Exception as e:
        st.error(f"خطأ في التوجيه الآلي: {e}")
        return False


# ════════════════════════════════════════════════
#  الشريط الجانبي
# ════════════════════════════════════════════════
# تهيئة آمنة للتنقّل قبل رسم الشريط الجانبي.
# هذا يمنع NameError في أسفل الملف إذا تعذر تعيين قيمة `page`
# لأي سبب أثناء بناء عناصر الشريط الجانبي في بعض البيئات.
page = st.session_state.get("main_nav", SECTIONS[0] if SECTIONS else "📊 لوحة التحكم")
with st.sidebar:
    st.markdown(f"## {APP_ICON} {APP_TITLE}")
    st.caption(f"الإصدار {APP_VERSION}")

    # حالة AI — أي مزود (Gemini و/أو OpenRouter و/أو Cohere) يكفي للمسار الهجين
    ai_ok = ANY_AI_PROVIDER_CONFIGURED
    if ai_ok:
        ai_color = "#00C853"
        _ai_bits = []
        if GEMINI_API_KEYS:
            _ai_bits.append(f"Gemini×{len(GEMINI_API_KEYS)}")
        if (OPENROUTER_API_KEY or "").strip():
            _ai_bits.append("OpenRouter")
        if (COHERE_API_KEY or "").strip():
            _ai_bits.append("Cohere")
        ai_label = f"🤖 {' · '.join(_ai_bits)} ✅"
    else:
        ai_color = "#FF1744"
        ai_label = "🔴 AI غير متصل — أضف مفتاحاً (Gemini أو OpenRouter أو Cohere)"

    st.markdown(
        f'<div style="background:{ai_color}22;border:1px solid {ai_color};'
        f'border-radius:6px;padding:6px;text-align:center;color:{ai_color};'
        f'font-weight:700;font-size:.85rem">{ai_label}</div>',
        unsafe_allow_html=True
    )

    # ── Phase 2: Sidebar scraper status indicator (visible from all pages) ──
    try:
        import os as _os_sb
        _sb_prog_file = _os_sb.path.join(
            _os_sb.environ.get("DATA_DIR", "data"), "scraper_progress.json"
        )
        if _os_sb.path.exists(_sb_prog_file):
            import json as _json_sb
            with open(_sb_prog_file, "r", encoding="utf-8") as _spf:
                _sb_prog = _json_sb.loads(_spf.read() or "{}")
            _sb_sc_running = bool(_sb_prog.get("running", False))
            _sb_sc_phase = str(_sb_prog.get("phase", ""))
            _sb_sc_rows = int(_sb_prog.get("rows_in_csv", 0))
            _sb_sc_store = str(_sb_prog.get("current_store", ""))
            if _sb_sc_running and _sb_sc_phase in ("discovering", "scraping", "retrying"):
                _sb_sc_label = f"🕷️ كشط: {_sb_sc_store or '...'}"
                st.markdown(
                    f'<div style="background:#0a2a0a22;border:1px solid #00C853;'
                    f'border-radius:6px;padding:4px 6px;text-align:center;color:#00C853;'
                    f'font-weight:600;font-size:.78rem;margin-top:4px">'
                    f'{_sb_sc_label} ({_sb_sc_rows:,} منتج)</div>',
                    unsafe_allow_html=True,
                )
            elif _sb_sc_phase == "completed" and _sb_sc_rows > 0:
                st.markdown(
                    f'<div style="background:#0a2a0a22;border:1px solid #4fc3f7;'
                    f'border-radius:6px;padding:4px 6px;text-align:center;color:#4fc3f7;'
                    f'font-weight:600;font-size:.78rem;margin-top:4px">'
                    f'✅ كشط مكتمل ({_sb_sc_rows:,} منتج)</div>',
                    unsafe_allow_html=True,
                )
    except Exception:
        pass  # لا يعطل الشريط الجانبي أبداً

    # زر تشخيص سريع — Railway يستخدم متغيرات البيئة وليس secrets.toml
    if not ai_ok:
        if st.button("🔍 تشخيص المشكلة", key="diag_btn"):
            import os

            def _mask(v: str) -> str:
                v = str(v or "").strip()
                if len(v) <= 12:
                    return "***" if v else ""
                return v[:8] + "…" + v[-4:]

            st.info(
                "على **Railway / Docker**: أضف **أحد** المسارات: `GEMINI_API_KEY` / `GEMINI_API_KEYS` "
                "أو **`OPENROUTER_API_KEY`** أو **`COHERE_API_KEY`** في Variables للخدمة "
                "(لا يعتمد التطبيق على ملف secrets.toml هناك). المحرك يجرّب Gemini ثم OpenRouter ثم Cohere."
            )
            st.write("**متغيرات البيئة — Gemini:**")
            _any = False
            for key_name in (
                "GEMINI_API_KEYS",
                "GEMINI_API_KEY",
                "GEMINI_KEY_1",
                "GEMINI_KEY_2",
                "GEMINI_KEY_3",
            ):
                raw = os.environ.get(key_name, "")
                if raw:
                    _any = True
                    st.success(f"✅ `{key_name}` = `{_mask(raw)}` (طول {len(raw)})")
                else:
                    st.caption(f"— `{key_name}` غير مضبوط")
            st.write("**متغيرات البيئة — بدائل (كافية بدون Gemini):**")
            for key_name in ("OPENROUTER_API_KEY", "OPENROUTER_KEY", "COHERE_API_KEY"):
                raw = os.environ.get(key_name, "")
                if raw:
                    _any = True
                    st.success(f"✅ `{key_name}` = `{_mask(raw)}` (طول {len(raw)})")
                else:
                    st.caption(f"— `{key_name}` غير مضبوط")
            st.write(
                f"**ما يقرأه التطبيق:** Gemini={len(GEMINI_API_KEYS)} | "
                f"OpenRouter={'نعم' if (OPENROUTER_API_KEY or '').strip() else 'لا'} | "
                f"Cohere={'نعم' if (COHERE_API_KEY or '').strip() else 'لا'}"
            )
            if not _any:
                st.warning(
                    "لم يُعثر على أي مفتاح. إما مفتاح **Google AI Studio** (`GEMINI_API_KEY`) "
                    "أو مفتاح **OpenRouter** (`OPENROUTER_API_KEY`) — الأخير يكفي لتشغيل مسار الـ fallback."
                )
            st.write("**Streamlit secrets (اختياري — Streamlit Cloud فقط):**")
            try:
                _sk = list(st.secrets.keys())
                for k in _sk:
                    val = str(st.secrets[k])
                    st.caption(f"  `{k}` = `{_mask(val)}`")
                if not _sk:
                    st.caption("لا مفاتيح — طبيعي على Railway عند الاعتماد على Variables فقط.")
            except Exception as e:
                st.caption(f"لا ملف secrets (طبيعي على Railway): {e}")

    # حالة المعالجة — تحديث حي مع auto-rerun + نتائج جزئية
    if st.session_state.job_id:
        # ⚡ perf: فحص الحالة خفيف (2.4ms) في كل rerun بدل الثقيل (1155ms على 71MB).
        # النتائج الكاملة تُحمَّل (الثقيل) فقط داخل الفروع التي تحتاجها فعلاً.
        job = get_job_progress(st.session_state.job_id, light=True)
        if job:
            _job_status = str(job.get("status", ""))
            if _job_status == "running":
                # ── شريط تقدم في الشريط الجانبي ──
                _sb_tot = max(int(job.get("total") or 0), 1)
                _sb_proc = min(int(job.get("processed") or 0), _sb_tot)
                _sb_pct = _sb_proc / _sb_tot
                st.progress(min(_sb_pct, 0.99))
                st.markdown(f"**⚙️ تحليل: {_sb_proc:,}/{_sb_tot:,} ({100*_sb_pct:.0f}%)**")
                # ── تحميل النتائج الجزئية أثناء التحليل (الثقيل، فقط أثناء running) ──
                job = get_job_progress(st.session_state.job_id)  # heavy: نحتاج results
                if job and job.get("results"):
                    try:
                        _partial = restore_results_from_json(job["results"])
                        _pdf = pd.DataFrame(_partial)
                        if not _pdf.empty:
                            _pr = _split_results(_pdf)
                            # FIX: لا تمسح المفقودات عند إعادة الرسم — احفظها من الجلسة ثم من الوظيفة
                            _prev_miss = (st.session_state.get("results") or {}).get("missing")
                            if isinstance(_prev_miss, pd.DataFrame) and not _prev_miss.empty:
                                _pr["missing"] = _prev_miss
                            else:
                                _pr["missing"] = pd.DataFrame(job.get("missing", []) or [])
                            st.session_state.results = _pr
                            st.session_state.analysis_df = _pdf
                    except Exception:
                        pass
            elif _job_status == "done":
                if st.session_state.get("_applied_job_results_id") != st.session_state.job_id:
                    st.session_state["_applied_job_results_id"] = st.session_state.job_id
                    # الثقيل (json.loads 71MB) يُنفَّذ هنا **مرة واحدة فقط** عند أول
                    # تطبيق — بعدها يحرس _applied_job_results_id فيبقى الفحص خفيفاً.
                    job = get_job_progress(st.session_state.job_id)  # heavy: once
                    if job and job.get("results"):
                        try:
                            _restored = restore_results_from_json(job["results"])
                            df_all = pd.DataFrame(_restored)
                            missing_df = pd.DataFrame(job.get("missing", [])) if job.get("missing") else pd.DataFrame()
                            # v31.11c: إذا المفقودات فارغة، احسبها تلقائياً
                            if (missing_df is None or (isinstance(missing_df, pd.DataFrame) and missing_df.empty)):
                                try:
                                    _our = st.session_state.get("our_df")
                                    _comp = st.session_state.get("comp_dfs")
                                    if _our is not None and _comp:
                                        missing_df = find_missing_products(_our, _comp)
                                        missing_df = smart_missing_barrier(missing_df, _our)
                                except Exception as _miss_err:
                                    import logging as _miss_log
                                    _miss_log.warning("Auto missing calc failed: %s", _miss_err)
                                    missing_df = pd.DataFrame()
                            _r = _split_results(df_all)
                            # ⚠️ لا نستدعي _auto_resolve_review هنا: فهو يُطلق نداءات AI
                            # متزامنة (auto_resolve_review_v2) داخل رسم الشريط الجانبي،
                            # فتُعلّق التطبيق عند فتح/استعادة الجلسة على Railway (شاشة سوداء/
                            # توقف عند ربط الـ volume الذي يحوي وظيفة done). الحسم بالـ AI
                            # يتم بزر مخصّص أثناء التحليل الفعلي فقط — لا في التطبيق السلبي
                            # للنتائج. (نفس إصلاح _safe_auto_restore الموثّق.)
                            _r["missing"] = missing_df
                            _r = _dedup_missing_vs_matched(_r)
                            st.session_state.results = _r
                            st.session_state.analysis_df = df_all
                        except Exception as _sb_apply_err:
                            import logging as _sb_log
                            _sb_log.error("Sidebar result apply failed: %s", _sb_apply_err)
                    st.session_state.last_audit_stats = job.get("audit") or {}
                    st.session_state.job_running = False
                    st.balloons()
                    st.rerun()
            elif _job_status.startswith("error"):
                st.error(f"❌ فشل: {_job_status[7:80]}")
    page = st.radio("الأقسام", SECTIONS, label_visibility="collapsed", key="main_nav")
    st.markdown("---")
    if st.session_state.results:
        r = st.session_state.results
        _all_df_summary = r.get("all", pd.DataFrame())
        _analysis_total = len(_all_df_summary) if isinstance(_all_df_summary, pd.DataFrame) else 0
        _selected_page = st.session_state.get("main_nav", "")
        _is_scraper_page = _selected_page == "🕷️ كشط المنافسين"

        if _is_scraper_page:
            st.info(
                "📊 توجد نتائج تحليل محفوظة، لكن تم إخفاء ملخصها هنا حتى لا يختلط مع أرقام الكشط الحالية. "
                "يمكنك مراجعة الملخص الكامل من صفحة «📊 لوحة التحكم»."
            )
        else:
            st.markdown("**📊 ملخص آخر تحليل:**")
            if _analysis_total:
                st.caption(f"يعرض توزيع **{_analysis_total:,}** من منتجاتنا المحللة، وليس عدد صفوف ملف المنافس.")
            _audit = st.session_state.get("last_audit_stats") or {}
            for key, icon, label in [
                ("price_raise","🔴","أعلى"), ("price_lower","🟢","أقل"),
                ("approved","✅","موافق"), ("missing","🔍","مفقود"),
            ]:
                cnt = len(r.get(key, pd.DataFrame()))
                audit_key = {
                    "price_raise": "price_raise",
                    "price_lower": "price_lower",
                    "approved": "approved",
                    "missing": "missing",
                }.get(key)
                if audit_key and isinstance(_audit, dict):
                    try:
                        cnt = int(_audit.get(audit_key, cnt) or cnt)
                    except Exception:
                        pass
                st.caption(f"{icon} {label}: **{cnt}**")

            _miss_df = r.get("missing", pd.DataFrame())
            if not _miss_df.empty and "مستوى_الثقة" in _miss_df.columns:
                _gc = len(_miss_df[_miss_df["مستوى_الثقة"] == "green"])
                _yc = len(_miss_df[_miss_df["مستوى_الثقة"] == "yellow"])
                _rc = len(_miss_df[_miss_df["مستوى_الثقة"] == "red"])
                st.markdown(
                    f'<div style="background:#1a1a2e;border-radius:6px;padding:6px;margin-top:4px;font-size:.75rem">'
                    f'🟢 مؤكد: <b>{_gc}</b> &nbsp; '
                    f'🟡 محتمل: <b>{_yc}</b> &nbsp; '
                    f'🔴 مشكوك: <b>{_rc}</b></div>',
                    unsafe_allow_html=True)
    pending_cnt = len(st.session_state.decisions_pending)
    if pending_cnt:
        st.markdown(f'<div style="background:#FF174422;border:1px solid #FF1744;'
                    f'border-radius:6px;padding:6px;text-align:center;color:#FF1744;'
                    f'font-size:.8rem">📦 {pending_cnt} قرار معلق</div>',
                    unsafe_allow_html=True)

    # ── فلاتر سريعة عالمية في نهاية الشريط الجانبي ──
    if st.session_state.results:
        _all_df = st.session_state.results.get("all", pd.DataFrame())
        if not _all_df.empty:
            render_sidebar_filters(_all_df)

    # ── تحذيرات الفحص الذاتي — في الشريط الجانبي فقط ───────────────────
    _hs_sb = st.session_state.get("health_status", {})
    _sb_warns = _hs_sb.get("warnings", [])
    if _sb_warns:
        st.sidebar.markdown("---")
        for _w in _sb_warns:
            st.sidebar.caption(f"🔔 {_w}")


# ── FIX: Fragment rerun handler — يلتقط الـ flag من _render_analysis_job_progress_live ──
# st.rerun() داخل @st.fragment يسبب حلقة لانهائية، لذا نستخدم flag بدلاً منه
if st.session_state.pop("_fragment_needs_rerun", False):
    st.rerun()

# إشعار خفيف بعد الانتقال من أزرار لوحة التحكم
if st.session_state.get("nav_flash"):
    _nf = st.session_state.pop("nav_flash", None)
    if _nf:
        if hasattr(st, "toast"):
            st.toast(_nf, icon="⏳")
        else:
            st.info(_nf)

# Toast نتائج Callbacks (إرسال Make / فشل)
_at = st.session_state.pop("_action_toast", None)
if _at:
    _at_type, _at_msg = _at
    if hasattr(st, "toast"):
        st.toast(_at_msg, icon="✅" if _at_type == "success" else "❌")
    elif _at_type == "success":
        st.success(_at_msg)
    else:
        st.error(_at_msg)


# ── الاعتماد النهائي والمتين لقيمة الصفحة الحالية ──
_fallback_page = SECTIONS[0] if SECTIONS else "📊 لوحة التحكم"
page = st.session_state.get("main_nav", _fallback_page)

# ════════════════════════════════════════════════
#  0. مصنع المنتجات (Magic Factory) — مدمج من pages/magic_factory.py
# ════════════════════════════════════════════════
if page == "✨ مصنع المنتجات":
    try:
        if _magic_factory_mod is not None and hasattr(_magic_factory_mod, "show"):
            _magic_factory_mod.show()
        elif _magic_factory_mod is not None:
            st.error("⚠️ دالة show() غير موجودة في ملف pages/magic_factory.py")
        else:
            st.error("❌ تعذّر تحميل وحدة مصنع المنتجات — تحقق من وجود الملف pages/magic_factory.py")
    except Exception as _mf_render_err:
        st.error(f"❌ خطأ في تشغيل مصنع المنتجات: {_mf_render_err}")


# ════════════════════════════════════════════════
#  1. لوحة التحكم
# ════════════════════════════════════════════════
if page == "📊 لوحة التحكم":
    st.header("📊 لوحة التحكم")
    db_log("dashboard", "view")
    if st.session_state.get("last_audit_stats"):
        try:
            _render_audit_bar(st.session_state.last_audit_stats)
            _render_reconciliation_dashboard(st.session_state.last_audit_stats)
        except Exception as _dash_render_err:
            st.error(f"⚠️ خطأ في عرض لوحة المحاسبة: {_dash_render_err}")

    # تغييرات الأسعار
    changes = get_price_changes(7)
    if changes:
        st.markdown("#### 🔔 تغييرات أسعار آخر 7 أيام")
        render_changes_table(changes, limit=200)
        st.markdown("---")

    if st.session_state.results:
        r = st.session_state.results

        # ── v32: Health Score ─────────────────────
        _total_h = sum(len(r.get(k, pd.DataFrame())) for k in ['price_raise','price_lower','approved','review','excluded'])
        if _total_h > 0:
            _approved_h = len(r.get('approved', pd.DataFrame()))
            _raise_h = len(r.get('price_raise', pd.DataFrame()))
            _lower_h = len(r.get('price_lower', pd.DataFrame()))
            _missing_h = len(r.get('missing', pd.DataFrame()))

            _health = int(
                (_approved_h / _total_h) * 40 +
                (1 - _raise_h / _total_h) * 30 +
                min(_lower_h / max(_total_h, 1), 0.3) * 30
            )
            _health = max(0, min(100, _health))
            _health_color = '#10B981' if _health >= 70 else '#F59E0B' if _health >= 40 else '#EF4444'
            _health_label = 'ممتاز 🌟' if _health >= 80 else 'جيد 👍' if _health >= 60 else 'يحتاج تحسين ⚠️' if _health >= 40 else 'ضعيف 🔴'

            st.markdown(f"""
        <div style="text-align:center;padding:20px;background:linear-gradient(135deg,#0B0F19,#111827);border-radius:16px;border:1px solid {_health_color}33;margin-bottom:20px">
            <div style="font-size:.85rem;color:#9CA3AF;margin-bottom:8px">نقطة الصحة التسعيرية</div>
            <div style="font-size:3.5rem;font-weight:900;color:{_health_color};line-height:1">{_health}</div>
            <div style="font-size:.9rem;color:{_health_color};margin-top:4px">{_health_label}</div>
            <div style="margin:12px auto;width:80%;height:8px;background:#1F2937;border-radius:4px;overflow:hidden">
                <div style="width:{_health}%;height:100%;background:{_health_color};border-radius:4px;transition:width 0.5s"></div>
            </div>
            <div style="display:flex;justify-content:center;gap:24px;margin-top:12px;font-size:.75rem;color:#9CA3AF">
                <span>✅ تنافسي: {_approved_h:,}</span>
                <span>🔴 أعلى: {_raise_h:,}</span>
                <span>🟢 أقل: {_lower_h:,}</span>
                <span>🔍 مفقود: {_missing_h:,}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── v33: KPI أداء التحليل (شريط HTML واحد بدل st.metric) ──
        _analysis_total_dash = len(r.get("all", pd.DataFrame())) if isinstance(r.get("all", pd.DataFrame()), pd.DataFrame) else 0
        if _analysis_total_dash:
            render_kpi_row({
                "total":    _analysis_total_dash,
                "raise":    _raise_h,
                "lower":    _lower_h,
                "approved": _approved_h,
                "missing":  _missing_h,
            })

            # ── الشرط 10: لوحة إحصائيات دقيقة (أرقام حقيقية لا تقديرية) ──
            _excluded_h = len(r.get("excluded", pd.DataFrame()))
            _review_h   = len(r.get("review", pd.DataFrame()))
            # منافسون/متاجر من قاعدة البيانات الفعلية (لا تقدير)
            _comp_total_db, _stores_db = 0, 0
            try:
                from engines.competitor_intelligence import CompetitorIntelligence as _CI
                import os as _ci_os2
                _ci_stats2 = _CI(db_path=_ci_os2.path.join(_ci_os2.environ.get("DATA_DIR", "data"), "pricing_v18.db")).get_stats()
                _comp_total_db = int(_ci_stats2.get("total_products", 0))
                _stores_db     = int(_ci_stats2.get("total_competitors", 0))
            except Exception:
                pass
            render_precise_stats({
                "our_products":      _analysis_total_dash,
                "total_competitors": _comp_total_db,
                "stores":            _stores_db,
                # «وُزِّع فعلاً في بطاقات» = الأقسام التي تعرض بطاقات منتجات
                "placed_in_cards":   _raise_h + _lower_h + _approved_h + _missing_h,
                "raise":    _raise_h, "lower": _lower_h, "approved": _approved_h,
                "excluded": _excluded_h, "missing": _missing_h, "review": _review_h,
            })
            _coverage = int((_approved_h + _lower_h) / max(_total_h, 1) * 100)
            st.caption(f"ملخص آخر تحليل لـ **{_analysis_total_dash:,}** منتج · 🎯 تغطية تنافسية: **{_coverage}%**")

        # ── شريط تحقّق حفظ البيانات (Data Conservation) ──
        _rc = _reconciliation_check(r)
        if _rc["gap_ok"] and _rc["duplicate_ok"]:
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#1B5E20,#2E7D32);color:#A5D6A7;'
                f'padding:12px 16px;border-radius:10px;font-weight:700;margin:8px 0;'
                f'border:1px solid #4CAF5044;font-size:.95rem">'
                f'✅ لا فقدان بيانات: كل المنتجات محسوبة ({_rc["all_count"]:,} منتج)'
                f'</div>', unsafe_allow_html=True,
            )
        else:
            _rc_msgs = []
            if not _rc["gap_ok"]:
                _rc_msgs.append(f'🚨 فقدان {abs(_rc["gap"])} منتج غير محسوب')
            if not _rc["duplicate_ok"]:
                _rc_msgs.append(f'🚨 تكرار: {_rc["duplicate_count"]} منتج مطابَق ومفقود معاً')
            st.markdown(
                f'<div style="background:linear-gradient(135deg,#B71C1C,#C62828);color:#FFCDD2;'
                f'padding:12px 16px;border-radius:10px;font-weight:700;margin:8px 0;'
                f'border:1px solid #EF444444;font-size:.95rem">'
                f'{" | ".join(_rc_msgs)}'
                f'</div>', unsafe_allow_html=True,
            )
        if not _rc["sources_consistent"]:
            st.markdown(
                f'<div style="background:#E65100;color:#FFE0B2;padding:10px 16px;'
                f'border-radius:10px;font-weight:600;margin:4px 0;font-size:.85rem">'
                f'⚠️ اختلاف المصدرين: excluded={_rc["excluded_count"]} ≠ missing={_rc["missing_count"]}'
                f' — مساري المطابقة قد يكونان غير متطابقين'
                f'</div>', unsafe_allow_html=True,
            )
        _dash_nav = [
            ("🔴 سعر أعلى", "🔴", "سعر أعلى", "price_raise"),
            ("🟢 سعر أقل", "🟢", "سعر أقل", "price_lower"),
            ("✅ موافق عليها", "✅", "موافق", "approved"),
            ("🔍 منتجات مفقودة", "🔍", "مفقود", "missing"),
        ]
        cols = st.columns(4)
        for col, (sec_title, icon, short_lbl, rkey) in zip(cols, _dash_nav):
            val = len(r.get(rkey, pd.DataFrame()))
            with col:
                if st.button(
                    f"{icon} {val}\n{short_lbl}",
                    key=f"dash_go_{rkey}",
                    use_container_width=True,
                    help=f"انتقل إلى {sec_title}",
                ):
                    st.session_state._nav_pending = sec_title
                    st.session_state.nav_flash = f"➡️ {sec_title}"
                    st.rerun()


        # ── v32: Smart Value Cards ───────────────
        _vc_cols = st.columns(3)
        # Raise section: potential savings
        _raise_df_vc = r.get('price_raise', pd.DataFrame())
        _raise_sum = 0
        if not _raise_df_vc.empty and 'الفرق' in _raise_df_vc.columns:
            try: _raise_sum = _raise_df_vc['الفرق'].apply(lambda x: abs(float(x or 0))).sum()
            except Exception: pass
        with _vc_cols[0]:
            st.markdown(f"""<div style="text-align:center;padding:16px;background:linear-gradient(135deg,#1a0a0a,#2d1111);border-radius:12px;border:1px solid #FF174433">
            <div style="font-size:.8rem;color:#FF8A80">🔴 فرص التوفير</div>
            <div style="font-size:1.8rem;font-weight:900;color:#FF1744;margin:4px 0">{_raise_sum:,.0f} <span style="font-size:.8rem">ر.س</span></div>
            <div style="font-size:.7rem;color:#888">{len(_raise_df_vc)} منتج أعلى سعراً</div>
            </div>""", unsafe_allow_html=True)
        # Lower section: potential earnings
        _lower_df_vc = r.get('price_lower', pd.DataFrame())
        _lower_sum = 0
        if not _lower_df_vc.empty and 'الفرق' in _lower_df_vc.columns:
            try: _lower_sum = _lower_df_vc['الفرق'].apply(lambda x: abs(float(x or 0))).sum()
            except Exception: pass
        with _vc_cols[1]:
            st.markdown(f"""<div style="text-align:center;padding:16px;background:linear-gradient(135deg,#0a1a0a,#112d11);border-radius:12px;border:1px solid #00C85333">
            <div style="font-size:.8rem;color:#69F0AE">🟢 فرص الربح</div>
            <div style="font-size:1.8rem;font-weight:900;color:#00C853;margin:4px 0">{_lower_sum:,.0f} <span style="font-size:.8rem">ر.س</span></div>
            <div style="font-size:.7rem;color:#888">{len(_lower_df_vc)} منتج أقل سعراً</div>
            </div>""", unsafe_allow_html=True)
        # Missing section
        _missing_df_vc = r.get('missing', pd.DataFrame())
        with _vc_cols[2]:
            st.markdown(f"""<div style="text-align:center;padding:16px;background:linear-gradient(135deg,#0a0a1a,#11112d);border-radius:12px;border:1px solid #448AFF33">
            <div style="font-size:.8rem;color:#82B1FF">🔍 منتجات مفقودة</div>
            <div style="font-size:1.8rem;font-weight:900;color:#448AFF;margin:4px 0">{len(_missing_df_vc)}</div>
            <div style="font-size:.7rem;color:#888">فرصة لإضافة منتجات جديدة</div>
            </div>""", unsafe_allow_html=True)

        # ملخص الثقة للمفقودات في لوحة التحكم
        _miss_dash = r.get("missing", pd.DataFrame())
        if not _miss_dash.empty and "مستوى_الثقة" in _miss_dash.columns:
            _g = len(_miss_dash[_miss_dash["مستوى_الثقة"] == "green"])
            _y = len(_miss_dash[_miss_dash["مستوى_الثقة"] == "yellow"])
            _rd = len(_miss_dash[_miss_dash["مستوى_الثقة"] == "red"])
            st.markdown(
                f'<div style="display:flex;gap:12px;justify-content:center;padding:8px;'
                f'background:#1a1a2e;border-radius:8px;margin:8px 0">'
                f'<span style="color:#00C853">🟢 مؤكد: <b>{_g}</b></span>'
                f'<span style="color:#FFD600">🟡 محتمل: <b>{_y}</b></span>'
                f'<span style="color:#FF1744">🔴 مشكوك: <b>{_rd}</b></span>'
                f'</div>', unsafe_allow_html=True)

        st.markdown("---")
        cc1, cc2 = st.columns(2)
        with cc1:
            sheets = {}
            for key, name in [("price_raise","سعر_أعلى"),("price_lower","سعر_أقل"),
                               ("approved","موافق"),("missing","مفقود"),("review","مراجعة"),
                               ("excluded","مستبعد")]:
                if key in r and not r[key].empty:
                    df_ex = r[key].copy()
                    if "جميع المنافسين" in df_ex.columns:
                        df_ex = df_ex.drop(columns=["جميع المنافسين"])
                    sheets[name] = df_ex
            if sheets:
                excel_all = export_multiple_sheets(sheets)
                st.download_button("📥 تصدير كل الأقسام Excel",
                    data=excel_all, file_name="mahwous_all.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="dash_export_all_excel",
                    )
        with cc2:
            if st.button("📤 إرسال كل شيء لـ Make (دفعات ذكية)",
                         key="dash_send_all_make"):
                _prog_all = st.progress(0, text="جاري الإرسال...")
                _status_all = st.empty()
                _sent_total = 0
                _fail_total = 0
                _sections = [
                    ("price_raise", "raise", "update", "🔴 سعر أعلى"),
                    ("price_lower", "lower", "update", "🟢 سعر أقل"),
                    ("approved",    "approved", "update", "✅ موافق"),
                    ("missing",     "missing", "new", "🔍 مفقودة"),
                ]
                for _si, (_key, _sec, _btype, _label) in enumerate(_sections):
                    if _key in r and not r[_key].empty:
                        _p = export_to_make_format(r[_key], _sec)
                        _res = send_batch_smart(_p, batch_type=_btype, batch_size=20, max_retries=3)
                        _full_success = (_res.get("sent", 0) == len(_p)) and (_res.get("failed", 0) == 0)  # FIX: Transparency & Reversibility
                        if _full_success:
                            if _key == "missing":
                                if "رابط_المنافس" in r[_key].columns:
                                    for _u in r[_key]["رابط_المنافس"].dropna().astype(str):
                                        _track_processed_missing_url(_u)
                            else:
                                if "معرف_المنتج" in r[_key].columns:
                                    for _pid in r[_key]["معرف_المنتج"].dropna().astype(str):
                                        _track_processed_price_sku(_pid)
                        elif _res.get("failed", 0) > 0:
                            st.error(f"❌ {_label}: فشل جزئي/كامل، لم يتم وسم المنتجات كـ(تمت المعالجة).")  # FIX: Transparency & Reversibility
                        _sent_total += _res.get("sent", 0)
                        _fail_total += _res.get("failed", 0)
                        _status_all.caption(f"{_label}: ✅ {_res.get('sent',0)} | ❌ {_res.get('failed',0)}")
                    _prog_all.progress((_si + 1) / len(_sections), text=f"جاري: {_label}")
                _prog_all.progress(1.0, text="اكتمل")
                st.success(f"✅ تم إرسال {_sent_total} منتج لـ Make!" + (f" (فشل {_fail_total})" if _fail_total else ""))
    else:
        # استئناف آخر job؟
        last = get_last_job()
        if last and last["status"] == "done" and last.get("results"):
            st.info(f"💾 يوجد تحليل محفوظ من {last.get('updated_at','')}")
            if st.button("🔄 استعادة النتائج المحفوظة", key="dash_restore_saved"):
                _restored_last = restore_results_from_json(last["results"])
                df_all = pd.DataFrame(_restored_last)
                if not df_all.empty:
                    missing_df = pd.DataFrame(last.get("missing", [])) if last.get("missing") else pd.DataFrame()
                    _r = _split_results(df_all)
                    _r["missing"] = missing_df
                    st.session_state.results     = _r
                    st.session_state.analysis_df = df_all
                    st.rerun()
        else:
            st.info("👈 ارفع الملفات في القسم أدناه ثم اضغط «بدء التحليل»")

    # ── Phase 2: Auto-Analysis after scraper completion ─────────────────
    # Fires ONCE — locked by _sc_auto_analysis_pending (consumed here)
    # Requires our_df from a previous upload session (stored in session_state)
    if st.session_state.pop("_sc_auto_analysis_pending", False):
        _prev_our_df = st.session_state.get("our_df")
        if _prev_our_df is not None and not getattr(_prev_our_df, "empty", True):
            st.info("🤖 **تحليل تلقائي بعد الكشط** — يستخدم منتجاتك المحفوظة + بيانات المنافسين الجديدة")
            import os as _os_auto
            _auto_csv_path = _os_auto.path.join(
                _os_auto.environ.get("DATA_DIR", "data"), "competitors_latest.csv"
            )
            _auto_comp_dfs = {}
            # First try: DB competitor store (Phase 1 cumulative)
            _db_stats = get_competitor_store_stats()
            if _db_stats.get("total_products", 0) > 0:
                _db_df = get_competitor_products_df()
                if not _db_df.empty and "competitor" in _db_df.columns:
                    for _cn, _cg in _db_df.groupby("competitor", sort=False):
                        _auto_comp_dfs[str(_cn)] = _cg.reset_index(drop=True)
            # Fallback: CSV file
            if not _auto_comp_dfs and _os_auto.path.exists(_auto_csv_path):
                try:
                    _csv_df = pd.read_csv(_auto_csv_path, encoding="utf-8-sig")
                    _scol = next((c for c in _csv_df.columns if str(c).strip().lower() in ("store", "domain", "المتجر", "المنافس")), None)
                    if _scol:
                        for _sn, _sg in _csv_df.groupby(_scol, sort=False):
                            _sk = str(_sn).replace("https://","").replace("http://","").strip("/").split("/")[0]
                            _auto_comp_dfs[_sk or "auto"] = _sg.reset_index(drop=True)
                    else:
                        _auto_comp_dfs["competitors_latest.csv"] = _csv_df
                except Exception:
                    pass
            if _auto_comp_dfs:
                with st.spinner(f"🤖 جاري التحليل التلقائي — {sum(len(v) for v in _auto_comp_dfs.values()):,} منتج منافس..."):
                    _auto_adf, _auto_audit = run_full_analysis(
                        _prev_our_df, _auto_comp_dfs,
                        progress_callback=None, use_ai=True
                    )
                    # Accumulate with previous results (Phase 1 logic)
                    _prev_adf = st.session_state.get("analysis_df")
                    if _prev_adf is not None and not getattr(_prev_adf, "empty", True):
                        _auto_adf = merge_price_analysis_dataframes(_prev_adf, _auto_adf)
                    _auto_r = _split_results(_auto_adf)
                    # Missing products
                    try:
                        _auto_miss = find_missing_products(_prev_our_df, _auto_comp_dfs)
                        _prev_miss = (st.session_state.get("results") or {}).get("missing")
                        if isinstance(_prev_miss, pd.DataFrame) and not _prev_miss.empty:
                            _auto_miss = merge_missing_products_dataframes(_prev_miss, _auto_miss)
                    except Exception:
                        _auto_miss = pd.DataFrame()
                    _auto_r["missing"] = _auto_miss
                    st.session_state.results = _auto_r
                    st.session_state.analysis_df = _auto_adf
                    st.session_state.comp_dfs = _auto_comp_dfs
                    st.session_state.last_audit_stats = _auto_audit
                st.success(
                    f"✅ اكتمل التحليل التلقائي — {len(_auto_adf):,} مطابقة | "
                    f"{len(_auto_miss) if isinstance(_auto_miss, pd.DataFrame) else 0} مفقود"
                )
                st.balloons()
            else:
                st.warning("⚠️ لا توجد بيانات منافسين جديدة للتحليل التلقائي.")
        else:
            st.warning(
                "⚠️ التحليل التلقائي يحتاج ملف منتجاتك — ارفع الملف ثم اضغط «بدء التحليل» يدوياً."
            )

    st.markdown("---")
    st.subheader("📂 رفع الملفات وبدء التحليل")

    our_file = st.file_uploader(
        "📦 ملف منتجاتنا (CSV/Excel)",
        type=["csv", "xlsx", "xls"],
        key="dash_our_file",
    )

    # ── جسر الكشط التلقائي (Auto-Scraper Bridge) ─────────────────────────
    import os as _os_dash
    _AUTO_CSV = _os_dash.path.join(
        _os_dash.environ.get("DATA_DIR", "data"), "competitors_latest.csv"
    )
    _auto_available = _os_dash.path.exists(_AUTO_CSV)
    _auto_rows = 0   # ← يُهيَّأ دائماً لمنع NameError إذا تغيّرت حالة الملف بين reruns

    if _auto_available:
        _auto_rows = 0
        try:
            with open(_AUTO_CSV, encoding="utf-8-sig") as _af:
                _auto_rows = sum(1 for _ in _af) - 1
        except Exception:
            pass
        st.markdown(
            f'<div style="background:#0a2a0a;border:1px solid #00C853;border-radius:8px;'
            f'padding:10px 14px;margin:6px 0;font-size:.88rem">'
            f'🤖 <b>بيانات الكشط التلقائي جاهزة</b> — '
            f'{_auto_rows:,} منتج من المنافسين<br>'
            f'<span style="color:#9e9e9e;font-size:.78rem">'
            f'استخدمها مباشرةً بدلاً من رفع ملف يدوي</span></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="background:#1a1a1a;border:1px dashed #555;border-radius:8px;'
            'padding:8px 14px;margin:6px 0;font-size:.82rem;color:#888">'
            '🤖 البيانات التلقائية غير متوفرة بعد — '
            '<a href="#" style="color:#4fc3f7">اذهب لصفحة الكشط</a> لتشغيل المحرك</div>',
            unsafe_allow_html=True,
        )

    _use_auto = st.checkbox(
        "🤖 استخدام بيانات الكشط التلقائي من المنافسين",
        value=bool(st.session_state.pop("_use_auto_scraper", False)) and _auto_available,
        disabled=not _auto_available,
        key="dash_use_auto_scraper",
        help="يستخدم الملف المُنتج تلقائياً من محرك الكشط بدلاً من رفع ملف يدوياً",
    )

    if not _use_auto:
        comp_files = st.file_uploader(
            "🏪 ملفات المنافسين (متعدد — CSV/Excel)",
            type=["csv", "xlsx", "xls"],
            accept_multiple_files=True,
            key="dash_comp_files",
            help="ملفات CSV بتصدير سلة/كشط (أعمدة مثل text-sm-2 وstyles_productCard__name__…) تُعرَف تلقائياً هنا.",
        )
    else:
        comp_files = None  # غير مستخدم عند التحميل التلقائي
        st.success(
            f"✅ سيُستخدم الملف الآلي: `{_AUTO_CSV}` ({_auto_rows:,} منتج)"
        )

    if our_file is not None:
        try:
            our_file.seek(0)
        except Exception:
            pass
        _odf, _oe = read_file(our_file)
        try:
            our_file.seek(0)
        except Exception:
            pass
        if not _oe and _odf is not None:
            with st.expander("📋 تعرف تلقائي على أعمدة ملف المتجر", expanded=False):
                _render_column_mapping_expander(_odf, "dash_map_our")
    if comp_files:
        for _ci, cf in enumerate(comp_files):
            _salla_err = None
            try:
                cf.seek(0)
            except Exception:
                pass
            _cfn = getattr(cf, "name", "") or ""
            if _cfn.lower().endswith(".csv"):
                _cdf_salla, _salla_err, _enc_used = load_competitor_csv_for_matching(
                    cf, competitor_label=_dashboard_competitor_label(_cfn)
                )
                if _cdf_salla is not None and not _salla_err:
                    st.caption(
                        f"✅ **{_cfn}** — تعريف تلقائي لتصدير سلة ({_enc_used}) · **{len(_cdf_salla):,}** صف"
                    )
                    with st.expander(f"📋 معاينة منظّفة — {_cfn}", expanded=False):
                        st.dataframe(_cdf_salla.head(8), use_container_width=True, height=260)
                    continue
                try:
                    cf.seek(0)
                except Exception:
                    pass
            _cdf, _ce = read_file(cf)
            try:
                cf.seek(0)
            except Exception:
                pass
            if not _ce and _cdf is not None:
                if _cfn.lower().endswith(".csv") and _salla_err:
                    st.caption(
                        f"⚠️ **{_cfn}**: تعيين سلة تلقائي: {_salla_err} — "
                        "يُستخدم التعرف العام؛ اضبط الأعمدة في المُوسّع إن لزم."
                    )
                with st.expander(f"📋 تعرف تلقائي — {cf.name}", expanded=False):
                    _render_column_mapping_expander(_cdf, f"dash_map_comp_{_ci}")

    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        bg_mode = st.checkbox(
            "⚡ معالجة خلفية (يمكنك التنقل أثناء التحليل)",
            value=True,
            key="dash_bg_mode",
        )
    with col_opt2:
        max_rows = st.number_input(
            "حد الصفوف للمعالجة (0=كل)", 0, step=500, key="dash_max_rows"
        )

    _copt3a, _copt3b = st.columns(2)
    with _copt3a:
        # FIX: Relaxed Constraints — منع فقدان النتائج السابقة بإجبار الدمج التراكمي دائماً.
        st.caption("📎 الدمج التراكمي للنتائج: **مفعّل دائماً (Zero Data Loss)**")
    with _copt3b:
        st.checkbox(
            "📚 تحديث كتالوج قاعدة البيانات من الملفات المرفوعة",
            value=True,
            key="dash_update_db_catalog",
            help="عطّلها لتشغيل المقارنة فقط دون تعديل جداول كتالوجنا والمنافسين في SQLite.",
        )

    # ── Duplicate-click mutex: UI + DB level ────────────────────────────
    try:
        release_stale_running_jobs(stale_after_seconds=300)  # 5 دقائق كافية
    except Exception:
        pass
    _db_running_job = None
    try:
        _db_running_job = any_running_job(stale_after_seconds=300)
    except Exception:
        _db_running_job = None
    _ui_job_running = bool(st.session_state.get("job_running", False))
    _analysis_locked = _ui_job_running or bool(_db_running_job)

    if _analysis_locked:
        _lock_jid = (
            st.session_state.get("job_id")
            or (_db_running_job or {}).get("job_id")
            or "?"
        )

        # ══ قراءة التقدم مباشرة من DB (أدق من any_running_job) — خفيف (2.4ms) ══
        _live_job = None
        try:
            _live_job = get_job_progress(_lock_jid, light=True)
        except Exception:
            pass
        _lock_proc = int((_live_job or {}).get("processed", 0) or (_db_running_job or {}).get("processed", 0))
        _lock_tot  = int((_live_job or {}).get("total", 0) or (_db_running_job or {}).get("total", 0))

        # ══ شريط تقدم مرئي ══
        if _lock_tot > 0:
            _lock_pct = min(_lock_proc / max(_lock_tot, 1), 0.99)
            st.progress(_lock_pct, f"⚙️ {_lock_proc:,} / {_lock_tot:,} ({100*_lock_pct:.0f}%)")
            st.warning(
                f"⏳ التحليل جارٍ — تم **{_lock_proc:,}** من **{_lock_tot:,}** منتج. "
                "اضغط «تحديث» لمتابعة التقدم."
            )
        elif _lock_proc > 0:
            st.progress(0.1, f"⚙️ جارٍ... {_lock_proc:,} منتج")
            st.warning("⏳ التحليل بدأ — اضغط «تحديث» لمتابعة التقدم.")
        else:
            st.progress(0.05, "⚙️ جارٍ التجهيز...")
            st.info(f"⏳ التحليل بدأ (Job: `{_lock_jid}`) — اضغط «تحديث» بعد ثوانٍ.")

        # ══ تحميل النتائج الجزئية أثناء التحليل (الثقيل، فقط عند وجود وظيفة حية) ══
        try:
            _full_job = get_job_progress(_lock_jid) if _live_job else None  # heavy: للنتائج
            if _full_job and _full_job.get("results"):
                _partial_recs = restore_results_from_json(_full_job["results"])
                _partial_df = pd.DataFrame(_partial_recs)
                if not _partial_df.empty:
                    _partial_r = _split_results(_partial_df)
                    # FIX: حافظ على المفقودات عبر إعادة الرسم (الجلسة ثم الوظيفة الحية)
                    _prev_miss = (st.session_state.get("results") or {}).get("missing")
                    if isinstance(_prev_miss, pd.DataFrame) and not _prev_miss.empty:
                        _partial_r["missing"] = _prev_miss
                    else:
                        _partial_r["missing"] = pd.DataFrame(_full_job.get("missing", []) or [])
                    st.session_state.results = _partial_r
                    st.session_state.analysis_df = _partial_df
                    st.caption(f"📊 {len(_partial_df):,} نتيجة جزئية معروضة في الأقسام")
        except Exception:
            pass

        # ══ زر تحديث يدوي (بدل meta refresh الذي يفصل الصفحة) ══
        _rc1, _rc2 = st.columns([1, 1])
        with _rc1:
            if st.button("🔄 تحديث التقدم", key="refresh_progress", type="primary"):
                st.rerun()
        with _rc2:
            if st.button("🔓 تحرير القفل", key="force_release_lock"):
                try:
                    release_stale_running_jobs(stale_after_seconds=0)
                    st.session_state.job_running = False
                    st.session_state.job_id = None
                    st.rerun()
                except Exception as _rel_e:
                    st.error(f"❌ {_rel_e}")

    # ── حماية من الضغطات المتكررة ──
    _btn_clicked_before = st.session_state.get("_analysis_btn_clicked", False)
    if _btn_clicked_before and not _analysis_locked:
        st.session_state["_analysis_btn_clicked"] = False

    if st.button(
        "🚀 بدء التحليل" if not _analysis_locked else "⏳ تحليل جارٍ... (يرجى الانتظار)",
        type="primary",
        key="dash_btn_start_analysis",
        disabled=_analysis_locked or _btn_clicked_before,
    ):
        # Second-chance re-check right before doing work: covers race between
        # render and click-handler (another replica may have acquired the lock).
        try:
            _late = any_running_job(stale_after_seconds=300)
        except Exception:
            _late = None
        if _late or st.session_state.get("job_running", False):
            st.warning(
                f"⚠️ تم منع تشغيل مزدوج — تحليل قيد التنفيذ بالفعل "
                f"(Job: `{(_late or {}).get('job_id', st.session_state.get('job_id','?'))}`)."
            )
            st.stop()
        # Phase 1: لا نمسح المعالجات — البيانات المعالجة تبقى مستمرة عبر التحليلات
        # Smart Reversion في _split_results سيُعيد المنتجات تلقائياً إذا تغير سعر المنافس
        # ── حارس المدخلات (يدعم الوضعين: يدوي وتلقائي) ──────────────────
        _auto_mode = bool(st.session_state.get("dash_use_auto_scraper")) and _auto_available
        # Phase 1: التحقق من وجود بيانات منافسين في المخزن التراكمي (DB)
        _db_store_stats = get_competitor_store_stats()
        _has_db_competitors = _db_store_stats.get("total_products", 0) > 0
        if not our_file and st.session_state.get("our_df") is None:
            st.warning("⚠️ ارفع ملف منتجاتنا أولاً")
        elif not _auto_mode and not comp_files and not _has_db_competitors:
            st.warning("⚠️ ارفع ملف منافس واحد على الأقل، أو فعّل الكشط التلقائي")
        else:
            _prep_ok = False
            our_df = None
            comp_dfs = {}
            job_id = None
            comp_names = ""
            _dash_upd_db_cat = bool(st.session_state.get("dash_update_db_catalog", True))
            _spin_read = (
                "⏳ جاري قراءة الملفات وتحديث كتالوج قاعدة البيانات..."
                if _dash_upd_db_cat
                else "⏳ جاري قراءة الملفات (بدون تحديث كتالوج قاعدة البيانات)..."
            )
            with st.spinner(_spin_read):
                if our_file:
                    # ── قراءة من الملف المرفوع ──
                    try:
                        our_file.seek(0)
                    except Exception:
                        pass
                    our_df, err = read_file(our_file)
                    if err:
                        st.error(f"❌ {err}")
                elif st.session_state.get("our_df") is not None:
                    # ── استخدام الكتالوج المحفوظ في الجلسة ──
                    our_df = st.session_state.our_df.copy()
                    err = None
                    st.info("📋 يُستخدم ملف المنتجات المحفوظ تلقائياً")
                else:
                    our_df = None
                    err = "لا يوجد ملف منتجات"

                if not err and our_df is not None:
                    our_df = apply_user_column_map(our_df, **_effective_column_map(our_df, "dash_map_our"))
                    if max_rows > 0:
                        our_df = our_df.head(int(max_rows))

                    # ── حفظ تلقائي للكتالوج ──
                    # session_state يُحدَّث دائماً حتى لو فشل حفظ CSV على القرص
                    st.session_state.our_df = our_df
                    try:
                        our_df.to_csv(_OUR_CATALOG_PATH, index=False, encoding="utf-8-sig")
                    except Exception:
                        pass
                    comp_dfs = {}
                    if _auto_mode:
                        # ── وضع الكشط التلقائي: تحميل CSV من القرص مع فصل كل متجر كمنافس مستقل ────────
                        try:
                            _auto_df = pd.read_csv(_AUTO_CSV, encoding="utf-8-sig")
                            _auto_store_col = next(
                                (
                                    _c for _c in _auto_df.columns
                                    if str(_c).strip().lower() in ("store", "domain", "المتجر", "المنافس")
                                ),
                                None,
                            )

                            if _auto_store_col:
                                _auto_df[_auto_store_col] = _auto_df[_auto_store_col].fillna("").astype(str).str.strip()
                                _grouped_auto = _auto_df[_auto_df[_auto_store_col] != ""].groupby(_auto_store_col, sort=False)
                                for _store_name, _store_df in _grouped_auto:
                                    _store_key = str(_store_name).strip()
                                    _store_key = _store_key.replace("https://", "").replace("http://", "").strip("/")
                                    _store_key = _store_key.split("/")[0] or "competitors_latest.csv"
                                    if _store_key in comp_dfs:
                                        comp_dfs[_store_key] = pd.concat(
                                            [comp_dfs[_store_key], _store_df.copy()],
                                            ignore_index=True,
                                        )
                                    else:
                                        comp_dfs[_store_key] = _store_df.reset_index(drop=True).copy()

                                _unassigned_auto = _auto_df[_auto_df[_auto_store_col] == ""]
                                if not _unassigned_auto.empty:
                                    comp_dfs["competitors_latest.csv"] = _unassigned_auto.reset_index(drop=True).copy()

                                if comp_dfs:
                                    st.caption(
                                        f"✅ تم تحميل البيانات الآلية: {len(_auto_df):,} صف من {len(comp_dfs):,} متجر منافس"
                                    )
                                else:
                                    comp_dfs["competitors_latest.csv"] = _auto_df
                                    st.caption(f"✅ تم تحميل البيانات الآلية: {len(_auto_df):,} منتج")
                            else:
                                comp_dfs["competitors_latest.csv"] = _auto_df
                                st.caption(f"✅ تم تحميل البيانات الآلية: {len(_auto_df):,} منتج")
                        except Exception as _ae:
                            st.error(f"❌ فشل تحميل الملف الآلي: {_ae}")
                    else:
                        # ── وضع الرفع اليدوي (CSV سلة/كشط → تعريف تلقائي ثم read_file احتياطاً) ──
                        for _ci, cf in enumerate(comp_files):
                            try:
                                cf.seek(0)
                            except Exception:
                                pass
                            _fn = getattr(cf, "name", "") or ""
                            if _fn.lower().endswith(".csv"):
                                cdf_norm, salla_err, _enc = load_competitor_csv_for_matching(
                                    cf, competitor_label=_dashboard_competitor_label(_fn)
                                )
                                if cdf_norm is not None and not salla_err:
                                    comp_dfs[_fn] = cdf_norm
                                    continue
                                try:
                                    cf.seek(0)
                                except Exception:
                                    pass
                            cdf, cerr = read_file(cf)
                            if cerr:
                                st.warning(f"⚠️ {_fn or cf.name}: {cerr}")
                            else:
                                cdf = apply_user_column_map(
                                    cdf, **_effective_column_map(cdf, f"dash_map_comp_{_ci}")
                                )
                                comp_dfs[_fn or cf.name] = cdf

                    # ── Phase 1: دمج تراكمي — تحميل بيانات المنافسين من المخزن الدائم (DB) ──
                    if not comp_dfs and _has_db_competitors:
                        # لا توجد ملفات مرفوعة → تحميل من المخزن التراكمي
                        _db_comp_df = get_competitor_products_df()
                        if not _db_comp_df.empty and "competitor" in _db_comp_df.columns:
                            # تعيين الأعمدة لتطابق ما يتوقعه المحرك
                            _db_rename = {
                                "product_name": "المنتج",
                                "price": "السعر",
                                "image_url": "صورة المنتج",
                                "product_url": "رابط المنتج",
                                "competitor": "المنافس",
                            }
                            _db_comp_df = _db_comp_df.rename(columns={
                                k: v for k, v in _db_rename.items()
                                if k in _db_comp_df.columns
                            })
                            for _cname, _cgroup in _db_comp_df.groupby(
                                "المنافس" if "المنافس" in _db_comp_df.columns else "competitor",
                                sort=False
                            ):
                                comp_dfs[str(_cname)] = _cgroup.reset_index(drop=True)
                            st.caption(
                                f"📂 تم تحميل {len(_db_comp_df):,} منتج منافس من المخزن التراكمي "
                                f"({len(comp_dfs)} متجر)"
                            )
                    elif comp_dfs and _has_db_competitors:
                        # ملفات مرفوعة + بيانات DB → دمج (الملف الجديد يفوز على التكرارات)
                        _db_comp_df = get_competitor_products_df()
                        if not _db_comp_df.empty and "competitor" in _db_comp_df.columns:
                            # تعيين الأعمدة لتطابق ما يتوقعه المحرك
                            _db_rename2 = {
                                "product_name": "المنتج",
                                "price": "السعر",
                                "image_url": "صورة المنتج",
                                "product_url": "رابط المنتج",
                            }
                            _db_comp_df = _db_comp_df.rename(columns={
                                k: v for k, v in _db_rename2.items()
                                if k in _db_comp_df.columns
                            })
                            _db_only_comps = set(_db_comp_df["competitor"].unique()) - set(comp_dfs.keys())
                            _merged_count = 0
                            for _cname in _db_only_comps:
                                _cgroup = _db_comp_df[_db_comp_df["competitor"] == _cname]
                                comp_dfs[str(_cname)] = _cgroup.reset_index(drop=True)
                                _merged_count += len(_cgroup)
                            if _merged_count > 0:
                                st.caption(
                                    f"📂 تم دمج {_merged_count:,} منتج من {len(_db_only_comps)} "
                                    f"متجر إضافي من المخزن التراكمي"
                                )

                    if not comp_dfs:
                        st.error("❌ لم يُحمّل أي ملف منافس صالح")
                    else:
                        _catc = _resolve_catalog_columns_relaxed(our_df)
                        if _dash_upd_db_cat:
                            r_our = upsert_our_catalog(
                                our_df,
                                name_col=_catc["name"] or "اسم المنتج",
                                id_col=_catc["id"] or "رقم المنتج",
                                price_col=_catc["price"] or "سعر المنتج",
                            )
                            r_comp = upsert_comp_catalog(comp_dfs)

                            # ── تراكم بيانات المنافسين عبر الجلسات ──────
                            try:
                                init_competitor_store()
                                _accum_total_new = 0
                                _accum_total_upd = 0
                                for _cname, _cdf in comp_dfs.items():
                                    if _cdf is None or _cdf.empty:
                                        continue
                                    _nc = next((c for c in ["المنتج","اسم المنتج","منتج_المنافس","name"] if c in _cdf.columns), None)
                                    _pc = next((c for c in ["سعر المنتج","السعر","سعر_المنافس","price"] if c in _cdf.columns), None)
                                    if _nc:
                                        _products_list = _cdf.rename(columns={_nc:"المنتج", _pc:"السعر"} if _pc else {_nc:"المنتج"}).to_dict("records")
                                        _r = upsert_competitor_products(_cname, _products_list)
                                        _accum_total_new += _r["inserted"]
                                        _accum_total_upd += _r["updated"]
                                _store_stats = get_competitor_store_stats()
                                st.caption(
                                    f"✅ كتالوجنا: {r_our['inserted']} جديد / {r_our['updated']} تحديث | "
                                    f"المنافسين: {r_comp['new_products']} جديد / {r_comp.get('updated',0)} تحديث | "
                                    f"🗄️ مخزن التراكم: {_accum_total_new} أُضيف / {_accum_total_upd} حُدِّث "
                                    f"(إجمالي: {_store_stats['total_products']:,} منتج)"
                                )
                            except Exception as _acc_err:
                                st.caption(
                                    f"✅ كتالوجنا: {r_our['inserted']} جديد / {r_our['updated']} تحديث | "
                                    f"المنافسين: {r_comp['new_products']} جديد / {r_comp.get('updated', 0)} تحديث"
                                )
                        else:
                            st.caption(
                                "⏭️ تم تخطي تحديث كتالوج قاعدة البيانات — يُحفظ التحليل في الجلسة فقط."
                            )
                        st.session_state.our_df = our_df
                        st.session_state.comp_dfs = comp_dfs
                        job_id = str(uuid.uuid4())[:8]
                        st.session_state.job_id = job_id
                        st.session_state.pop("_applied_job_results_id", None)
                        comp_names = ",".join(comp_dfs.keys())
                        _prep_ok = True

            if _prep_ok and our_df is not None and comp_dfs:
                _validate_uploaded_catalog(our_df, "ملف منتجاتنا")
                for _cfn, _cdf in comp_dfs.items():
                    _validate_uploaded_catalog(_cdf, f"ملف منافس: {_cfn}")
                if bg_mode:
                    _dash_acc = bool(st.session_state.get("dash_accumulate_results", True))
                    _prev_ar = None
                    _prev_mr = None
                    if _dash_acc:
                        _adf_prev = st.session_state.get("analysis_df")
                        if _adf_prev is not None and not getattr(_adf_prev, "empty", True):
                            _prev_ar = safe_results_for_json(_adf_prev.to_dict("records"))
                        _res_prev = st.session_state.get("results") or {}
                        _miss_prev = _res_prev.get("missing")
                        if isinstance(_miss_prev, pd.DataFrame) and not _miss_prev.empty:
                            _prev_mr = _miss_prev.to_dict("records")
                    _bg_target = partial(
                        _run_analysis_background,
                        job_id,
                        our_df,
                        comp_dfs,
                        our_file.name if our_file else "كتالوج_محفوظ",
                        comp_names,
                        merge_previous=_dash_acc,
                        prev_analysis_records=_prev_ar,
                        prev_missing_records=_prev_mr,
                    )
                    t = threading.Thread(target=_bg_target, daemon=True)
                    add_script_run_ctx(t)
                    t.start()
                    st.session_state.job_running = True
                    st.session_state["_analysis_btn_clicked"] = True
                    import time as _start_t
                    st.session_state["_analysis_start_time"] = _start_t.time()
                    st.success(f"✅ بدأ التحليل في الخلفية (Job: {job_id})")
                    st.rerun()
                else:
                    prog = st.progress(0, "جاري التحليل...")

                    def upd(p, _r=None):
                        prog.progress(min(float(p), 0.99), f"{float(p)*100:.0f}%")

                    df_all, audit_stats = run_full_analysis(our_df, comp_dfs, progress_callback=upd)
                    _prev_adf = st.session_state.get("analysis_df")
                    # الشرط 11: وسم الجديد/تغيّر السعر قبل الدمج (مقارنةً بالسابق)
                    df_all = _annotate_change_status(df_all, _prev_adf)
                    if st.session_state.get("dash_accumulate_results", True):
                        if _prev_adf is not None and not getattr(_prev_adf, "empty", True):
                            df_all = merge_price_analysis_dataframes(_prev_adf, df_all)
                            if "حالة_التغيير" in df_all.columns:
                                df_all["حالة_التغيير"] = df_all["حالة_التغيير"].fillna("")
                            st.caption("📎 وُدمت نتائج التحليل مع الجلسة السابقة.")
                    st.session_state.last_audit_stats = audit_stats
                    _render_audit_bar(audit_stats)
                    try:
                        _rec = reconcile_competitor_upload(our_df, comp_dfs)
                        missing_df = smart_missing_barrier(_rec.new_products_df, our_df)
                        _rec.apply_smart_barrier_adjustment(missing_df)
                        audit_stats = merge_reconciliation_into_audit(audit_stats, _rec)
                        st.session_state.last_audit_stats = audit_stats
                        st.session_state.reconciliation_report = _rec.to_dict()
                        st.session_state.reconciliation_failed_csv = (
                            failed_rows_to_xlsx_bytes(_rec.failed_df)
                            if _rec.failed_df is not None and not _rec.failed_df.empty
                            else None
                        )
                        if _rec.failed_df is not None and not _rec.failed_df.empty:
                            import os

                            _dd = os.environ.get("DATA_DIR", "data")
                            os.makedirs(_dd, exist_ok=True)
                            _fj = os.path.join(
                                _dd,
                                f"failed_rows_{st.session_state.get('job_id') or 'local'}.xlsx",
                            )
                            try:
                                _rec.failed_df.to_excel(_fj, index=False, engine="openpyxl")
                                audit_stats["reconciliation_failed_csv_path"] = _fj
                                st.session_state.last_audit_stats = audit_stats
                            except OSError:
                                pass
                        # v31.11c: إذا reconcile لم يجد مفقودات، استخدم find_missing_products
                        if not isinstance(missing_df, pd.DataFrame) or missing_df.empty:
                            st.info("🔍 جاري حساب المنتجات المفقودة...")
                            raw_missing_df = find_missing_products(our_df, comp_dfs)
                            missing_df = smart_missing_barrier(raw_missing_df, our_df)
                    except Exception as _rec_err:
                        st.warning(f"⚠️ محرك المحاسبة: {_rec_err} — يُستخدم مسار المفقودات السابق.")
                        raw_missing_df = find_missing_products(our_df, comp_dfs)
                        missing_df = smart_missing_barrier(raw_missing_df, our_df)
                        st.session_state.reconciliation_report = None
                        st.session_state.reconciliation_failed_csv = None
                    _render_reconciliation_dashboard(st.session_state.get("last_audit_stats") or {})
                    if st.session_state.get("dash_accumulate_results", True):
                        _prev_miss_df = None
                        if st.session_state.get("results") and isinstance(
                            st.session_state["results"], dict
                        ):
                            _prev_miss_df = st.session_state["results"].get("missing")
                        if (
                            isinstance(_prev_miss_df, pd.DataFrame)
                            and not _prev_miss_df.empty
                        ):
                            missing_df = merge_missing_products_dataframes(
                                _prev_miss_df, missing_df
                            )

                    # حفظ تاريخ الأسعار — مع حد أقصى وحماية من التعليق
                    try:
                        _ph_limit = min(len(df_all), 5000)  # حد أقصى لمنع التعليق
                        _ph_count = 0
                        for _, row in df_all.head(_ph_limit).iterrows():
                            if safe_float(row.get("نسبة_التطابق", 0)) > 0:
                                upsert_price_history(
                                    str(row.get("المنتج", "")),
                                    str(row.get("المنافس", "")),
                                    safe_float(row.get("سعر_المنافس", 0)),
                                    safe_float(row.get("السعر", 0)),
                                    safe_float(row.get("الفرق", 0)),
                                    safe_float(row.get("نسبة_التطابق", 0)),
                                    str(row.get("القرار", "")),
                                )
                                _ph_count += 1
                        if len(df_all) > _ph_limit:
                            st.caption(f"⚠️ تم حفظ {_ph_count} من {len(df_all)} سجل في تاريخ الأسعار (حد أقصى {_ph_limit})")
                    except Exception as _ph_err:
                        st.caption(f"⚠️ تعذّر حفظ تاريخ الأسعار: {_ph_err}")

                    _r = _split_results(df_all)
                    _r["missing"] = missing_df
                    st.session_state.results = _r
                    st.session_state.analysis_df = df_all
                    log_analysis(
                        our_file.name if our_file else "كتالوج_محفوظ",
                        comp_names,
                        len(our_df),
                        int((df_all.get("نسبة_التطابق", pd.Series(dtype=float)) > 0).sum()),
                        len(missing_df),
                    )
                    prog.progress(1.0, "✅ اكتمل!")
                    st.balloons()
                    st.rerun()



# ════════════════════════════════════════════════
#  2. سعر أعلى
# ════════════════════════════════════════════════
elif page == "🔴 سعر أعلى":
    st.markdown(
        '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:0 0 4px 0">'
        '<span class="b-high" style="display:inline-block;padding:6px 12px;border-radius:10px;'
        'font-weight:800;font-size:.95rem">🔴 فرصة خفض</span>'
        '<span style="color:#9e9e9e;font-size:.82rem;font-weight:600">مقارنة مع أقل سعر منافس</span>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.header("منتجات سعرنا أعلى")
    db_log("price_raise", "view")
    if st.session_state.results and "price_raise" in st.session_state.results:
        df = st.session_state.results["price_raise"]
        _price_raise_total = len(df) if isinstance(df, pd.DataFrame) else 0  # FIX: Transparency & Reversibility
        if isinstance(df, pd.DataFrame) and not df.empty and "معرف_المنتج" in df.columns:
            _proc_price = {str(x) for x in st.session_state.get("processed_price_skus", set())}
            df = df[~df["معرف_المنتج"].astype(str).isin(_proc_price)]  # FIX: Smart Workflow & AI Tracking
        _show_transparency_counter(_price_raise_total, len(df) if isinstance(df, pd.DataFrame) else 0)  # FIX: Transparency & Reversibility
        if not df.empty:
            st.markdown(
                f'<p style="margin:4px 0 8px;font-size:1.05rem;font-weight:700;color:#FF5252">'
                f"{len(df)} منتج — سعرنا أعلى من المنافس (بيانات التحليل الحالي)</p>",
                unsafe_allow_html=True,
            )
            # AI تدريب لهذا القسم
            with st.expander("🤖 نصيحة AI لهذا القسم", expanded=False):
                if st.button("📡 احصل على تحليل شامل للقسم", key="ai_section_raise"):
                    with st.spinner("🤖 AI يحلل البيانات الفعلية..."):
                        _top = df.nlargest(min(15, len(df)), "الفرق") if "الفرق" in df.columns else df.head(15)
                        _lines = "\n".join(
                            f"- {r.get('المنتج','')}: سعرنا {safe_float(r.get('السعر',0)):.0f} | المنافس ({r.get('المنافس','')}) {safe_float(r.get('سعر_المنافس',0)):.0f} | فرق +{safe_float(r.get('الفرق',0)):.0f}"
                            for _, r in _top.iterrows())
                        _avg_diff = safe_float(df["الفرق"].mean()) if "الفرق" in df.columns else 0
                        _prompt = (f"عندي {len(df)} منتج سعرنا أعلى من المنافسين.\n"
                                   f"متوسط الفرق: {_avg_diff:.0f} ر.س\n"
                                   f"أعلى 15 فرق:\n{_lines}\n\n"
                                   f"أعطني:\n1. أي المنتجات يجب خفض سعرها فوراً (فرق>30)؟\n"
                                   f"2. أي المنتجات يمكن إبقاؤها (فرق<10)؟\n"
                                   f"3. استراتيجية تسعير مخصصة لكل ماركة")
                        r = call_ai(_prompt, "price_raise")
                        st.markdown(f'<div class="ai-box">{_html_mod.escape(str(r["response"]))}</div>', unsafe_allow_html=True)
            render_pro_table_v32(df, "raise", "raise", compact_cards=True)
        else:
            st.success("✅ ممتاز! لا توجد منتجات بسعر أعلى")
    else:
        st.info("ارفع الملفات أولاً")


# ════════════════════════════════════════════════
#  4. سعر أقل
# ════════════════════════════════════════════════
elif page == "🟢 سعر أقل":
    st.header("🟢 منتجات سعرنا أقل — فرصة رفع")
    db_log("price_lower", "view")
    if st.session_state.results and "price_lower" in st.session_state.results:
        df = st.session_state.results["price_lower"]
        _price_lower_total = len(df) if isinstance(df, pd.DataFrame) else 0  # FIX: Transparency & Reversibility
        if isinstance(df, pd.DataFrame) and not df.empty and "معرف_المنتج" in df.columns:
            _proc_price = {str(x) for x in st.session_state.get("processed_price_skus", set())}
            df = df[~df["معرف_المنتج"].astype(str).isin(_proc_price)]  # FIX: Smart Workflow & AI Tracking
        _show_transparency_counter(_price_lower_total, len(df) if isinstance(df, pd.DataFrame) else 0)  # FIX: Transparency & Reversibility
        if not df.empty:
            st.info(f"💰 {len(df)} منتج يمكن رفع سعره لزيادة الهامش")
            with st.expander("🤖 نصيحة AI لهذا القسم", expanded=False):
                if st.button("📡 استراتيجية رفع الأسعار", key="ai_section_lower"):
                    with st.spinner("🤖 AI يحلل فرص الربح..."):
                        _top = df.nsmallest(min(15, len(df)), "الفرق") if "الفرق" in df.columns else df.head(15)
                        _lines = "\n".join(
                            f"- {r.get('المنتج','')}: سعرنا {safe_float(r.get('السعر',0)):.0f} | المنافس ({r.get('المنافس','')}) {safe_float(r.get('سعر_المنافس',0)):.0f} | فرق {safe_float(r.get('الفرق',0)):.0f}"
                            for _, r in _top.iterrows())
                        _total_lost = safe_float(df["الفرق"].sum()) if "الفرق" in df.columns else 0
                        _prompt = (f"عندي {len(df)} منتج سعرنا أقل من المنافسين.\n"
                                   f"إجمالي الأرباح الضائعة: {abs(_total_lost):.0f} ر.س\n"
                                   f"أكبر 15 فرصة ربح:\n{_lines}\n\n"
                                   f"أعطني:\n1. أي المنتجات يمكن رفع سعرها فوراً (فرق>50)؟\n"
                                   f"2. أي المنتجات نرفعها تدريجياً (فرق 10-50)؟\n"
                                   f"3. كم الربح المتوقع إذا رفعنا الأسعار؟")
                        r = call_ai(_prompt, "price_lower")
                        st.markdown(f'<div class="ai-box">{_html_mod.escape(str(r["response"]))}</div>', unsafe_allow_html=True)
            render_pro_table_v32(df, "lower", "lower")
        else:
            st.info("لا توجد منتجات")
    else:
        st.info("ارفع الملفات أولاً")


# ════════════════════════════════════════════════
#  5. موافق عليها
# ════════════════════════════════════════════════
elif page == "✅ موافق عليها":
    st.header("✅ منتجات موافق عليها")
    db_log("approved", "view")
    if st.session_state.results and "approved" in st.session_state.results:
        df = st.session_state.results["approved"]
        if not df.empty:
            st.success(f"✅ {len(df)} منتج بأسعار تنافسية مناسبة")
            render_pro_table_v32(df, "approved", "approved")
        else:
            st.info("لا توجد منتجات موافق عليها")
    else:
        st.info("ارفع الملفات أولاً")


# ════════════════════════════════════════════════
#  6. منتجات مفقودة — v26 مع كشف التستر/الأساسي
# ════════════════════════════════════════════════
elif page == "🔍 منتجات مفقودة":
    st.header("🔍 منتجات المنافسين غير الموجودة عندنا")
    _debug_log("H2", "app.py:missing_page_entry", "Entered missing page", {
        "has_results": bool(st.session_state.results),
        "has_missing_key": bool(st.session_state.results and "missing" in st.session_state.results),
    })
    # ── 🤖 الاستخراج الذكي بـ AI (محرك جديد — يدمج: مطابقة + ماركات + تصنيفات + وصف) ──
    with st.expander("🤖 استخراج ذكي بـ AI (مع ماركات + تصنيفات + وصف Mahwous)", expanded=False):
        st.markdown(
            "ارفع كتالوجك + ملفات المنافسين + ماركات/تصنيفات مهووس → "
            "يستخرج المفقودات الحقيقية فقط (≥85%=موجود، 70-85%=AI verify، <70%=مفقود) "
            "ويصدّر `new_products.xlsx` + `new_brands.csv` بصيغة سلة."
        )
        try:
            from engines.missing_products_engine import build_missing_exports
            import tempfile as _tmp
            from pathlib import Path as _Path

            _c1, _c2 = st.columns(2)
            with _c1:
                _smart_cat  = st.file_uploader("📦 كتالوج متجرنا", type=["xlsx","xls","csv"], key="smart_miss_cat")
                _smart_br   = st.file_uploader("🏷️ ماركات مهووس", type=["csv","xlsx"], key="smart_miss_br")
            with _c2:
                _smart_cmp  = st.file_uploader("🏪 ملفات المنافسين (متعدد)", type=["csv","xlsx"],
                                                accept_multiple_files=True, key="smart_miss_cmp")
                _smart_cats = st.file_uploader("📁 تصنيفات مهووس", type=["csv","xlsx"], key="smart_miss_cats")

            _o1, _o2 = st.columns(2)
            _use_ai     = _o1.toggle("🤖 تفعيل AI", value=True, key="smart_miss_ai")
            _gen_desc   = _o2.toggle("📝 توليد الوصف", value=True, key="smart_miss_desc")

            if st.button("🚀 ابدأ الاستخراج الذكي", type="primary", key="smart_miss_run"):
                if not all([_smart_cat, _smart_br, _smart_cats, _smart_cmp]):
                    st.error("❌ ارفع جميع الملفات الأربعة.")
                else:
                    def _save(f):
                        try:
                            t = _tmp.NamedTemporaryFile(delete=False, suffix=_Path(f.name).suffix)
                            t.write(f.read()); t.close(); return t.name
                        except Exception as _sf_err:
                            st.error(f"❌ فشل حفظ الملف {f.name}: {_sf_err}")
                            return None
                    with st.spinner("⚙️ جارٍ الفحص الذكي..."):
                        try:
                            _res = build_missing_exports(
                                catalog_path=_save(_smart_cat),
                                competitor_paths=[_save(f) for f in _smart_cmp],
                                brands_path=_save(_smart_br),
                                categories_path=_save(_smart_cats),
                                use_ai=_use_ai,
                                generate_descriptions=_gen_desc,
                            )
                        except Exception as _build_err:
                            st.error(f"❌ فشل الاستخراج الذكي: {_build_err}")
                            _res = None
                    if _res:
                        st.success(f"✅ {_res['products_count']} منتج | {_res['new_brands_count']} ماركة جديدة")
                        _d1, _d2 = st.columns(2)
                        with _d1:
                            with open(_res["products_file"], "rb") as fh:
                                st.download_button("📥 تحميل المنتجات الجديدة", fh.read(),
                                    file_name=_Path(_res["products_file"]).name,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True, key="smart_dl_prod")
                        with _d2:
                            if _res["new_brands_file"]:
                                with open(_res["new_brands_file"], "rb") as fh:
                                    st.download_button("📥 تحميل الماركات الجديدة", fh.read(),
                                        file_name=_Path(_res["new_brands_file"]).name,
                                        mime="text/csv", use_container_width=True, key="smart_dl_br")
        except Exception as _smart_e:
            st.error(f"تعذّر تحميل المحرك الذكي: {_smart_e}")

    # ── المستشار الذكي للمفقودات ─────────────────────────────────────────
    with st.expander("🧠 المستشار الذكي للمفقودات (AI Expert)", expanded=False):
        st.markdown("اسأل المستشار عن استراتيجية إضافة هذه المنتجات أو تحليل السوق لها:")
        miss_query = st.text_input(
            "سؤالك للمستشار (مثال: ما هي أكثر ماركة مطلوبة من هذه القائمة؟)",
            key="miss_expert_q",
        )
        if st.button("💬 اسأل المستشار", key="ask_miss_expert"):
            if not miss_query.strip():
                st.warning("اكتب سؤالاً أولاً.")
            else:
                with st.spinner("المستشار يحلل القائمة..."):
                    _sample_data = []
                    if st.session_state.results and "missing" in st.session_state.results:
                        _src_df = st.session_state.results["missing"]
                        if _src_df is not None and not _src_df.empty:
                            _sample_data = _src_df.head(50).to_dict("records")
                    _prompt = (
                        f"بناء على هذه المنتجات المفقودة: {str(_sample_data)[:3000]}\n"
                        f"أجب على: {miss_query}"
                    )
                    _response = call_ai(_prompt, "missing")
                    st.markdown(f'<div class="ai-box">{_html_mod.escape(str(_response["response"]))}</div>', unsafe_allow_html=True)

    # ── 🧠 كشف ذكي من المخزن التراكمي (v31) ─────────────────────────────
    with st.expander("🧠 كشف ذكي من المخزن التراكمي (16+ متجر)", expanded=False):
        st.markdown(
            "يبحث في **قاعدة بيانات المنافسين التراكمية** عن منتجات غير موجودة "
            "عندنا — بالبصمة الذكية (بدون تكرار)."
        )
        try:
            from engines.competitor_intelligence import CompetitorIntelligence
            import os as _ci_os
            _ci_db = _ci_os.path.join(_ci_os.environ.get("DATA_DIR", "data"), "pricing_v18.db")
            _ci = CompetitorIntelligence(db_path=_ci_db)

            # إحصائيات سريعة
            _ci_stats = _ci.get_stats()
            _ci_m1, _ci_m2, _ci_m3 = st.columns(3)
            _ci_m1.metric("📦 منتجات المنافسين", f"{_ci_stats.get('total_products', 0):,}")
            _ci_m2.metric("🏪 المتاجر", f"{_ci_stats.get('total_competitors', 0)}")
            _ci_m3.metric("🆕 جديد (7 أيام)", f"{_ci_stats.get('new_7d', 0):,}")

            # فلاتر
            _ci_f1, _ci_f2 = st.columns(2)
            with _ci_f1:
                _ci_comps = ["الكل"] + (_ci.get_available_competitors() or [])
                _ci_sel_comp = st.selectbox("🏪 المتجر", _ci_comps, key="ci_miss_comp")
            with _ci_f2:
                _ci_brands = ["الكل"] + (_ci.get_available_brands()[:50] or [])
                _ci_sel_brand = st.selectbox("🏷️ الماركة", _ci_brands, key="ci_miss_brand")

            _ci_filters = {}
            if _ci_sel_comp != "الكل":
                _ci_filters["competitor"] = _ci_sel_comp
            if _ci_sel_brand != "الكل":
                _ci_filters["brand"] = _ci_sel_brand

            _ci_page = st.number_input("الصفحة", min_value=1, value=1, step=1, key="ci_miss_page")

            our_df = st.session_state.get("our_df")
            if our_df is not None and not our_df.empty:
                if st.button("🔍 بحث عن المفقود من المخزن", key="ci_miss_search", type="primary"):
                    with st.spinner("🧠 جاري تحليل البصمات..."):
                        import time as _ci_time
                        _ci_t0 = _ci_time.time()
                        _ci_prods, _ci_total = _ci.find_missing_products(
                            our_df, page=_ci_page - 1, per_page=20, filters=_ci_filters
                        )
                        _ci_elapsed = _ci_time.time() - _ci_t0
                        st.session_state["_ci_missing_results"] = (_ci_prods, _ci_total, _ci_elapsed)

                # عرض النتائج المحفوظة
                _ci_cached = st.session_state.get("_ci_missing_results")
                if _ci_cached:
                    _ci_prods, _ci_total, _ci_elapsed = _ci_cached
                    st.caption(f"❌ {_ci_total:,} منتج غير متوفر لدينا — ({_ci_elapsed:.1f}s)")

                    if _ci_prods:
                        for _ci_i, _ci_p in enumerate(_ci_prods):
                            _ci_c1, _ci_c2, _ci_c3 = st.columns([3, 1, 1])
                            with _ci_c1:
                                _ci_name = _ci_p.get("product_name", "")
                                _ci_brand = _ci_p.get("brand", "")
                                st.markdown(f"**{_ci_name[:100]}**")
                                _ci_parts = []
                                if _ci_brand:
                                    _ci_parts.append(f"🏷️ {_ci_brand}")
                                _ci_parts.append(f"💰 أقل: {_ci_p.get('min_price', 0):,.0f} ر.س")
                                _ci_parts.append(f"📊 عند {_ci_p.get('competitor_count', 1)} منافسين")
                                _ci_parts.append(f"💵 المقترح: {_ci_p.get('suggested_price', 0):,.0f} ر.س")
                                st.caption(" | ".join(_ci_parts))
                            with _ci_c2:
                                if st.button("🤖 تجهيز", key=f"ci_prep_{_ci_i}_{_ci_page}"):
                                    _ci_prepared = _ci.prepare_for_make(_ci_p)
                                    st.session_state[f"ci_prepared_{_ci_i}"] = _ci_prepared
                                    st.success("✅")
                            with _ci_c3:
                                _ci_prep_data = st.session_state.get(f"ci_prepared_{_ci_i}")
                                if _ci_prep_data:
                                    if st.button("📤 Make", key=f"ci_send_{_ci_i}_{_ci_page}"):
                                        try:
                                            _ci_result = send_new_products([_ci_prep_data])
                                            st.success("✅ تم الإرسال")
                                        except Exception as _ci_e:
                                            st.error(f"فشل: {_ci_e}")
                            st.divider()
                    else:
                        st.success("🎉 كل منتجات المنافسين متوفرة لديك!")
            else:
                st.warning("⚠️ ارفع كتالوج منتجاتنا أولاً من لوحة التحكم")
        except Exception as _ci_err:
            st.error(f"تعذّر تحميل محرك الذكاء: {_ci_err}")

    st.caption(
        "العدد هنا = **عناوين فريدة** بعد إزالة التكرار والمطابقة مع كتالوجنا — وليس بالضرورة كل صفوف ملف المنافس."
    )
    db_log("missing", "view")

    # ── استعادة ذاتية + تشخيص حالة حساب المفقودات ──────────────────────────
    # المفقودات تُحسب (reconcile على عشرات آلاف المنافسين) بعد بلوغ التقدّم 100%،
    # وقد تستغرق دقائق. هنا: (1) استعِدها من آخر وظيفة إن فُقدت من الجلسة،
    # (2) أبلِغ المستخدم بوضوح إن كانت ما تزال قيد الحساب في الخلفية.
    _res_now = st.session_state.get("results")
    if not isinstance(_res_now, dict):
        _res_now = {}
    _cur_miss = _res_now.get("missing")
    if not isinstance(_cur_miss, pd.DataFrame) or _cur_miss.empty:
        try:
            _last = get_last_job()
            _job_miss = pd.DataFrame((_last or {}).get("missing", []) or [])
            _job_status_m = str((_last or {}).get("status", ""))
            if not _job_miss.empty:
                _res_now["missing"] = _ensure_competitor_details(_job_miss)  # v33
                st.session_state.results = _res_now
                st.info(
                    f"♻️ استُعيدت **{len(_job_miss):,}** منتجاً مفقوداً من آخر تحليل محفوظ "
                    "(كانت قد فُقدت من الجلسة الحالية)."
                )
            else:
                # لا مفقودات في الجلسة ولا في آخر وظيفة (الوظيفة غالباً ماتت قبل
                # حسابها). الحل: احسبها **تلقائياً عند فتح هذه الصفحة** من المخزن
                # الدائم (لا عند الإقلاع — لتفادي تثقيل بدء التطبيق). الحساب مُخبّأ
                # (@st.cache_data) فيُنفَّذ مرة ويُعاد فورياً؛ وعلَم الجلسة يمنع
                # إعادة المحاولة كل rerun حتى لو كانت النتيجة فارغة.
                _auto_key = "_missing_store_autocomputed"
                if not st.session_state.get(_auto_key):
                    with st.spinner("🧠 جارٍ فحص كل منتجات المنافسين مقابل كتالوجنا… "
                                     "(يُحسب مرة ويُخزَّن — لحظات)"):
                        try:
                            _computed = _compute_missing_from_store(_our_sig="v1")
                        except Exception as _cm_err:
                            _computed = pd.DataFrame()
                            st.error(f"❌ تعذّر حساب المفقودات: {_cm_err}")
                    # ضع العلَم دائماً — حتى لو فارغة — كي لا نُعيد الحساب الثقيل كل rerun
                    st.session_state[_auto_key] = True
                    if isinstance(_computed, pd.DataFrame) and not _computed.empty:
                        _res_now["missing"] = _ensure_competitor_details(_computed)  # v33
                        st.session_state.results = _res_now
                        st.rerun()  # أعد الرسم ليعرضها قسم العرض أدناه مباشرة
                    else:
                        st.info(
                            "لم يُعثر على منتجات مفقودة في المخزن التراكمي "
                            "(كل منتجات المنافسين موجودة لدينا، أو لا يوجد مخزن/كتالوج)."
                        )
                # زر إعادة حساب يدوي (يُفرغ الكاش والعلَم لإجبار حساب جديد)
                if st.button("🔄 إعادة حساب المفقودة من المخزن (108k+ منافس)",
                             key="miss_compute_now"):
                    st.session_state.pop(_auto_key, None)
                    try:
                        _compute_missing_from_store.clear()
                    except Exception:
                        pass
                    st.rerun()
        except Exception as _heal_err:
            import logging as _heal_log
            _heal_log.warning("Missing self-heal failed: %s", _heal_err)

    if st.session_state.results and "missing" in st.session_state.results:
        df_missing = st.session_state.results["missing"]
        # ═══ v33: ضمان وجود تفاصيل المنافسين ═══
        if isinstance(df_missing, pd.DataFrame) and not df_missing.empty:
            if "تفاصيل_المنافسين" not in df_missing.columns:
                df_missing = _ensure_competitor_details(df_missing)
                st.session_state.results["missing"] = df_missing
        # ═══ v33: حساب الأولوية ═══
        if isinstance(df_missing, pd.DataFrame) and not df_missing.empty:
            if "درجة_الأولوية" not in df_missing.columns:
                try:
                    from engines.engine import calculate_missing_priority
                    df_missing = calculate_missing_priority(df_missing)
                    st.session_state.results["missing"] = df_missing
                except Exception as _prio_err:
                    import logging as _prio_log
                    _prio_log.warning("v33 priority calc failed: %s", _prio_err)
        df_missing_to_show = df_missing.copy() if isinstance(df_missing, pd.DataFrame) else pd.DataFrame()
        _missing_total = len(df_missing) if isinstance(df_missing, pd.DataFrame) else 0  # FIX: Missing Products Display Recovery
        # FIX: Safe Filtering for Missing Products to prevent KeyError
        if isinstance(df_missing, pd.DataFrame):
            if not df_missing.empty:
                link_col_actual = None
                possible_link_cols = ["رابط_المنافس", "الرابط", "رابط المنتج", "url", "رابط", "Link"]
                for col in possible_link_cols:
                    if col in df_missing.columns:
                        link_col_actual = col
                        break
                if link_col_actual:
                    df_missing_to_show = df_missing[
                        ~df_missing[link_col_actual].astype(str).isin(
                            {str(x) for x in st.session_state.get("processed_missing_urls", set())}
                        )
                    ]
                else:
                    name_col_actual = "المنتج"
                    for ncol in ["المنتج", "اسم المنتج", "منتج_المنافس", "Name"]:
                        if ncol in df_missing.columns:
                            name_col_actual = ncol
                            break
                    if name_col_actual in df_missing.columns:
                        df_missing_to_show = df_missing[
                            ~df_missing[name_col_actual].astype(str).isin(
                                {str(x) for x in st.session_state.get("processed_missing_urls", set())}
                            )
                        ]
                    else:
                        df_missing_to_show = df_missing.copy()
            else:
                df_missing_to_show = df_missing.copy()
        df = df_missing_to_show
        _show_transparency_counter(_missing_total, len(df_missing_to_show) if isinstance(df_missing_to_show, pd.DataFrame) else 0)  # FIX: Missing Products Display Recovery
        if df is not None and not df.empty:
            # ── v33: إحصاءات محسّنة مع توزيع الثقة ──────────────────────
            total_miss   = len(df)
            has_tester   = df["نوع_متاح"].str.contains("تستر", na=False).sum()    if "نوع_متاح" in df.columns else 0
            has_base     = df["نوع_متاح"].str.contains("العطر الأساسي", na=False).sum() if "نوع_متاح" in df.columns else 0
            pure_missing = total_miss - has_tester - has_base

            # عدد المنتجات حسب مستوى الثقة
            _gc = len(df[df["مستوى_الثقة"] == "green"]) if "مستوى_الثقة" in df.columns else 0
            _yc = len(df[df["مستوى_الثقة"] == "yellow"]) if "مستوى_الثقة" in df.columns else 0
            _rc = len(df[df["مستوى_الثقة"] == "red"]) if "مستوى_الثقة" in df.columns else 0
            _revc = len(df[df["مستوى_الثقة"] == "review"]) if "مستوى_الثقة" in df.columns else 0

            # قيمة تقديرية
            _est_val = 0
            for _pc in ("سعر_المنافس", "سعر المنافس", "السعر"):
                if _pc in df.columns:
                    _est_val = pd.to_numeric(df[_pc], errors="coerce").sum()
                    break

            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("🟢 مفقود مؤكد", f"{_gc:,}")
            c2.metric("🔵 محتمل موجود", f"{_revc:,}", help="65-82% — يُحسم بالذكاء الاصطناعي أو يدوياً")
            c3.metric("🏷️ تستر", f"{has_tester:,}")
            c4.metric("📦 إجمالي معروض", f"{total_miss:,}")
            c5.metric("💰 قيمة تقديرية", f"{_est_val:,.0f} ر.س")
            with c6:
                if (_revc > 0 or _gc > 0) and st.button("🤖 تحقّق AI (مراجعة + مشتبه امتلاكه)", key="miss_ai_verify_btn",
                                           use_container_width=True,
                                           help="Gemini يفحص «محتمل موجود» + «المؤكد مفقود» المشابه لمنتجاتنا (≥55%) — يلتقط المملوك باسم آخر (عربي↔إنجليزي). حتى 150/ضغطة، كرّر للمزيد. المؤكد امتلاكه يُزال، والمرفوض يبقى مفقوداً."):
                    with st.spinner("🤖 Gemini يفحص حتى 150 منتجاً (مراجعة + مشتبه امتلاكه)…"):
                        try:
                            _new_df, _conf_owned, _conf_miss = verify_review_bucket_with_ai(df)
                            st.session_state.results["missing"] = _new_df
                            st.session_state["_action_toast"] = (
                                "success",
                                f"✅ تحقّق AI: {_conf_owned:,} مؤكد امتلاكنا (أُزيل) · "
                                f"{_conf_miss:,} مؤكد مفقود (بقي).",
                            )
                        except Exception as _ai_err:
                            st.session_state["_action_toast"] = ("error", f"تعذّر تحقّق AI: {_ai_err}")
                    st.rerun()

            # ═══ v33: مقاييس الأولوية ═══
            _critical_count = 0
            if "درجة_الأولوية" in df.columns:
                _critical_count = int((pd.to_numeric(df["درجة_الأولوية"], errors="coerce").fillna(0) >= 80).sum())
            _multi_comp = 0
            if "تفاصيل_المنافسين" in df.columns:
                _multi_comp = int(df["تفاصيل_المنافسين"].apply(
                    lambda x: len(x) if isinstance(x, list) else 1
                ).ge(3).sum())
            elif "عدد_المنافسين" in df.columns:
                _multi_comp = int((pd.to_numeric(df["عدد_المنافسين"], errors="coerce").fillna(1) >= 3).sum())
            _pk1, _pk2, _pk3 = st.columns(3)
            _pk1.metric("🔴 أولوية حرجة", f"{_critical_count:,}")
            _pk2.metric("🏪 عند 3+ منافسين", f"{_multi_comp:,}")
            _pk3.metric("📦 إجمالي", f"{total_miss:,}")

            # ── v31.11c: تصدير سريع للمنتجات المؤكدة الجاهزة للرفع ──
            if _gc > 0:
                st.markdown("---")
                _exp_c1, _exp_c2, _exp_c3 = st.columns([2, 1, 1])
                with _exp_c1:
                    _margin = st.number_input(
                        "هامش الربح %", min_value=0, max_value=100,
                        value=15, step=5, key="miss_margin_pct"
                    )
                with _exp_c2:
                    if st.button("📦 تجهيز للرفع", key="miss_prep_upload", type="primary"):
                        with st.spinner("جاري تجهيز المنتجات..."):
                            _upload_df = prepare_missing_for_upload(_clean_for_export(df), margin_pct=_margin)
                            st.session_state["_miss_upload_ready"] = _upload_df
                with _exp_c3:
                    st.caption(f"🟢 {_gc} منتج مؤكد جاهز")

                _upload_ready = st.session_state.get("_miss_upload_ready")
                if isinstance(_upload_ready, pd.DataFrame) and not _upload_ready.empty:
                    st.success(f"✅ تم تجهيز {len(_upload_ready)} منتج — جاهز للتحميل!")
                    st.dataframe(_upload_ready, use_container_width=True, height=300)
                    _dl1, _dl2 = st.columns(2)
                    with _dl1:
                        _csv_data = _upload_ready.to_csv(index=False, encoding="utf-8-sig")
                        st.download_button(
                            "📥 CSV (سلة)", data=_csv_data,
                            file_name="mahwous_missing_upload.csv",
                            mime="text/csv", use_container_width=True,
                        )
                    with _dl2:
                        try:
                            _xl_buf = io.BytesIO()
                            _upload_ready.to_excel(_xl_buf, index=False, engine="openpyxl")
                            st.download_button(
                                "📥 Excel", data=_xl_buf.getvalue(),
                                file_name="mahwous_missing_upload.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                use_container_width=True,
                            )
                        except Exception:
                            st.caption("❌ openpyxl غير متوفر")


            # ── تحليل AI الأولويات ────────────────────────────────────────
            with st.expander("🤖 تحليل AI — أولويات الإضافة", expanded=False):
                if st.button("📡 تحليل الأولويات", key="ai_missing_section"):
                    with st.spinner("🤖 AI يحلل أولويات الإضافة..."):
                        _pure = df[df["نوع_متاح"].str.strip() == ""] if "نوع_متاح" in df.columns else df
                        _brands = _pure["الماركة"].value_counts().head(10).to_dict() if "الماركة" in _pure.columns else {}
                        _summary = " | ".join(f"{b}:{c}" for b,c in _brands.items()) if _brands else "غير محدد"
                        _lines   = "\n".join(
                            f"- {r.get('منتج_المنافس','')}: {safe_float(r.get('سعر_المنافس',0)):.0f}ر.س ({r.get('الماركة','')}) — {r.get('المنافس','')}"
                            for _, r in _pure.head(20).iterrows())
                        _prompt = (
                            f"لديّ {len(_pure)} منتج مفقود فعلاً (بدون التستر/الأساسي المتاح).\n"
                            f"توزيع الماركات: {_summary}\nعينة:\n{_lines}\n\n"
                            "أعطني:\n1. ترتيب أولويات الإضافة (عالية/متوسطة/منخفضة) مع السبب\n"
                            "2. أي الماركات الأكثر ربحية؟\n"
                            "3. سعر مقترح (أقل من المنافس بـ5-10 ر.س)\n"
                            "4. منتجات لا تستحق الإضافة — ولماذا؟"
                        )
                        r_ai = call_ai(_prompt, "missing")
                        resp = r_ai["response"] if r_ai["success"] else "❌ فشل AI"
                        # تنظيف JSON من المخرجات
                        import re as _re
                        resp = _re.sub(r'```json.*?```', '', resp, flags=_re.DOTALL)
                        resp = _re.sub(r'```.*?```', '', resp, flags=_re.DOTALL)
                        st.markdown(f'<div class="ai-box">{_html_mod.escape(str(resp))}</div>', unsafe_allow_html=True)

            # ── v33: فلاتر محسّنة ظاهرة ─────────────────────────────────
            opts = get_filter_options(df)
            st.markdown("---")

            # ═══ v33: شريط الترتيب ═══
            st.radio(
                "🔀 ترتيب حسب",
                ["⚡ الأولوية", "🏪 عدد المنافسين", "💰 السعر (الأعلى)", "💰 السعر (الأقل)", "🔤 الاسم"],
                horizontal=True,
                key="miss_sort_mode_v33",
            )

            # صف 1: مستوى الثقة (أزرار ملوّنة) — خارج الـ form لأنها تعتمد rerun فوري
            _conf_options = ["الكل", "🟢 مفقود مؤكد", "🔵 محتمل موجود", "🟡 محتمل", "🔴 مشكوك"]
            _conf_cols = st.columns(len(_conf_options))
            for _ci, _co in enumerate(_conf_options):
                with _conf_cols[_ci]:
                    _is_active = st.session_state.get("miss_conf_active", "الكل") == _co
                    _btn_type = "primary" if _is_active else "secondary"
                    if st.button(_co, key=f"miss_conf_btn_{_ci}", type=_btn_type, use_container_width=True):
                        st.session_state["miss_conf_active"] = _co
                        st.rerun()
            conf_f = st.session_state.get("miss_conf_active", "الكل")

            # باقي الفلاتر داخل form — لا يُعاد الرسم عند كل حرف (تُطبَّق عند الضغط)
            _price_col = None
            for _pc in ("سعر_المنافس", "سعر المنافس", "السعر"):
                if _pc in df.columns:
                    _price_col = _pc
                    break
            with st.form(key="miss_filters_form", border=False):
                search = st.text_input("🔎 بحث في الاسم/الماركة", key="miss_s", placeholder="اكتب للبحث...")
                # صف 2: ماركة + منافس + نوع + تصنيف
                _f3, _f4, _f5, _f6 = st.columns(4)
                with _f3:
                    brand_f = st.selectbox("🏷️ الماركة", opts["brands"], key="miss_b")
                with _f4:
                    comp_f = st.selectbox("🏪 المنافس", opts["competitors"], key="miss_c")
                with _f5:
                    variant_f = st.selectbox("📦 النوع",
                        ["الكل", "مفقود فعلاً", "يوجد تستر", "يوجد الأساسي"], key="miss_v")
                with _f6:
                    _cat_opts = ["الكل", "🌸 عطور", "🧴 عناية", "💄 تجميل", "📦 أخرى"]
                    cat_f = st.selectbox("📋 التصنيف", _cat_opts, key="miss_cat")

                # v33: فلتر عدد المنافسين
                _max_comps = 10
                if "تفاصيل_المنافسين" in df.columns:
                    _max_comps = max(int(df["تفاصيل_المنافسين"].apply(
                        lambda x: len(x) if isinstance(x, list) else 1
                    ).max()), 2)
                elif "عدد_المنافسين" in df.columns:
                    _max_comps = max(int(pd.to_numeric(df["عدد_المنافسين"], errors="coerce").max() or 2), 2)
                _min_comp = st.slider(
                    "🏪 الحد الأدنى لعدد المنافسين",
                    min_value=1, max_value=min(_max_comps, 15), value=1,
                    key="miss_min_comp_v33",
                )

                # صف 3: نطاق السعر (slider)
                if _price_col:
                    _prices = pd.to_numeric(df[_price_col], errors="coerce").dropna()
                    if not _prices.empty:
                        _pmin = int(max(0, _prices.min()))
                        _pmax = int(min(99999, _prices.max()))
                        if _pmax > _pmin:
                            _p_range = st.slider(
                                "💰 نطاق السعر (ر.س)", _pmin, _pmax, (_pmin, _pmax),
                                key="miss_price_range"
                            )
                        else:
                            _p_range = (_pmin, _pmax)
                    else:
                        _p_range = None
                else:
                    _p_range = None
                st.form_submit_button("🔍 تطبيق الفلاتر", use_container_width=True, type="primary")

            st.markdown("---")

            # ── تطبيق الفلاتر ──
            filtered = df.copy()
            if search:
                _s_lower = search.lower()
                # بحث vectorized سريع بدل lambda بطيء
                _mask = pd.Series(False, index=filtered.index)
                for _sc in ("منتج_المنافس", "الماركة", "المنافس"):
                    if _sc in filtered.columns:
                        _mask = _mask | filtered[_sc].astype(str).str.lower().str.contains(_s_lower, na=False, regex=False)
                filtered = filtered[_mask]
            if brand_f != "الكل" and "الماركة" in filtered.columns:
                filtered = filtered[filtered["الماركة"].str.contains(brand_f, case=False, na=False, regex=False)]
            if comp_f != "الكل" and "المنافس" in filtered.columns:
                filtered = filtered[filtered["المنافس"].str.contains(comp_f, case=False, na=False, regex=False)]
            if variant_f == "مفقود فعلاً" and "نوع_متاح" in filtered.columns:
                filtered = filtered[filtered["نوع_متاح"].str.strip() == ""]
            elif variant_f == "يوجد تستر" and "نوع_متاح" in filtered.columns:
                filtered = filtered[filtered["نوع_متاح"].str.contains("تستر", na=False)]
            elif variant_f == "يوجد الأساسي" and "نوع_متاح" in filtered.columns:
                filtered = filtered[filtered["نوع_متاح"].str.contains("الأساسي", na=False)]
            # فلتر الثقة
            if conf_f != "الكل" and "مستوى_الثقة" in filtered.columns:
                _conf_map = {"🟢 مفقود مؤكد": "green", "🟢 مؤكد": "green",
                             "🔵 محتمل موجود": "review",
                             "🟡 محتمل": "yellow", "🔴 مشكوك": "red"}
                _cv = _conf_map.get(conf_f, "")
                if _cv:
                    filtered = filtered[filtered["مستوى_الثقة"] == _cv]
            # فلتر التصنيف
            if cat_f != "الكل" and "تصنيف_المنتج" in filtered.columns:
                filtered = filtered[filtered["تصنيف_المنتج"] == cat_f]
            # فلتر السعر
            if _p_range and _price_col and _price_col in filtered.columns:
                _f_prices = pd.to_numeric(filtered[_price_col], errors="coerce").fillna(0)
                filtered = filtered[(_f_prices >= _p_range[0]) & (_f_prices <= _p_range[1])]

            # v33: فلتر عدد المنافسين
            if _min_comp > 1:
                if "تفاصيل_المنافسين" in filtered.columns:
                    filtered = filtered[filtered["تفاصيل_المنافسين"].apply(
                        lambda x: len(x) if isinstance(x, list) else 1
                    ) >= _min_comp]
                elif "عدد_المنافسين" in filtered.columns:
                    filtered = filtered[pd.to_numeric(filtered["عدد_المنافسين"], errors="coerce").fillna(1) >= _min_comp]

            # ═══ v33: ترتيب متقدم ─────────────────
            _sm = st.session_state.get("miss_sort_mode_v33", "⚡ الأولوية")
            if _sm == "⚡ الأولوية" and "درجة_الأولوية" in filtered.columns:
                filtered = filtered.sort_values("درجة_الأولوية", ascending=False)
            elif _sm == "🏪 عدد المنافسين":
                if "تفاصيل_المنافسين" in filtered.columns:
                    filtered = filtered.assign(
                        _nc=filtered["تفاصيل_المنافسين"].apply(lambda x: len(x) if isinstance(x, list) else 1)
                    ).sort_values("_nc", ascending=False).drop(columns=["_nc"])
                elif "عدد_المنافسين" in filtered.columns:
                    filtered = filtered.sort_values("عدد_المنافسين", ascending=False)
            elif _sm == "💰 السعر (الأعلى)":
                _pc2 = next((c for c in ["سعر_المنافس", "السعر"] if c in filtered.columns), None)
                if _pc2:
                    filtered = filtered.assign(
                        _sp=pd.to_numeric(filtered[_pc2], errors="coerce").fillna(0)
                    ).sort_values("_sp", ascending=False).drop(columns=["_sp"])
            elif _sm == "💰 السعر (الأقل)":
                _pc2 = next((c for c in ["سعر_المنافس", "السعر"] if c in filtered.columns), None)
                if _pc2:
                    filtered = filtered.assign(
                        _sp=pd.to_numeric(filtered[_pc2], errors="coerce").fillna(0)
                    ).sort_values("_sp", ascending=True).drop(columns=["_sp"])
            elif _sm == "🔤 الاسم":
                if "منتج_المنافس" in filtered.columns:
                    filtered = filtered.sort_values("منتج_المنافس")
            else:
                # ترتيب افتراضي: ثقة ثم أولوية (السلوك القديم)
                if "مستوى_الثقة" in filtered.columns:
                    _conf_order = {"green": 0, "review": 1, "yellow": 2, "red": 3}
                    filtered = filtered.assign(
                        _co=filtered["مستوى_الثقة"].map(_conf_order).fillna(4)
                    )
                    if "درجة_الأولوية" in filtered.columns:
                        filtered = filtered.sort_values(["_co", "درجة_الأولوية"], ascending=[True, False]).drop(columns=["_co"])
                    else:
                        filtered = filtered.sort_values("_co").drop(columns=["_co"])

            # ── شريط شارات الفلاتر الفعّالة ──
            _miss_chips = render_active_filter_chips_html({
                "search":    search,
                "brand":     brand_f,
                "comp":      comp_f,
                "status":    "" if conf_f == "الكل" else conf_f,
            })
            if _miss_chips:
                st.markdown(_miss_chips, unsafe_allow_html=True)

            # ── عداد النتائج + إحصائيات التصنيف ──
            _fc1, _fc2, _fc3 = st.columns([2, 2, 6])
            _fc1.metric("📋 نتائج الفلتر", f"{len(filtered):,}")
            if _price_col and _price_col in filtered.columns:
                _est_rev = pd.to_numeric(filtered[_price_col], errors="coerce").sum()
                _fc2.metric("💰 قيمة تقديرية", f"{_est_rev:,.0f} ر.س")
            # إحصائيات التصنيف
            if "تصنيف_المنتج" in df.columns:
                _cat_counts = df["تصنيف_المنتج"].value_counts()
                _cat_parts = " • ".join(f"{k}: {v}" for k, v in _cat_counts.items())
                with _fc3:
                    st.caption(f"📊 التوزيع: {_cat_parts}")

            # ── تصدير جاهز للرفع → قالب سلة الشامل (الشرط 3) — مع فصل retail/تستر/عينة ──
            st.markdown("##### 📦 تصدير جاهز للرفع — قالب سلة الشامل (40 عمود)")
            # تصنيف نوع السلعة (retail/tester/sample) — يُحسب من المخزن أو fallback من الاسم
            if "نوع_السلعة" in filtered.columns:
                _itype = filtered["نوع_السلعة"].fillna("retail").astype(str)
            else:
                _nm_s = filtered.get("منتج_المنافس", pd.Series([""] * len(filtered))).astype(str)
                _itype = pd.Series(
                    [("sample" if (("عينة" in n) or ("عينه" in n) or ("sample" in n.lower())
                                   or ("ديكانت" in n) or ("مينياتشر" in n) or ("تقسيم" in n))
                      else "tester" if (("تستر" in n) or ("tester" in n.lower()))
                      else "retail") for n in _nm_s],
                    index=filtered.index,
                )
            _n_retail = int((_itype == "retail").sum())
            _n_tester = int((_itype == "tester").sum())
            _n_sample = int((_itype == "sample").sum())
            _ic1, _ic2, _ic3 = st.columns(3)
            _ic1.metric("🛍️ مفقود حقيقي (retail)", f"{_n_retail:,}")
            _ic2.metric("🧪 تستر", f"{_n_tester:,}")
            _ic3.metric("💧 عينة/ديكانت", f"{_n_sample:,}")
            # العينات تُستبعد دائماً من ملف الإضافة؛ التستر خيار (الافتراضي: مُضمَّن — قرار المالك)
            _inc_tester = st.toggle("🧪 تضمين التستر في ملف الإضافة", value=True, key="miss_exp_inc_tester")
            st.caption("💧 العينات/الديكانت مُستبعَدة دائماً (ليست منتجات للبيع كجديد).")
            _exp_types = ["retail"] + (["tester"] if _inc_tester else [])
            _export_src = filtered[_itype.isin(_exp_types)]
            _exp_d1, _exp_d2 = st.columns([1, 1])
            with _exp_d1:
                if st.button(f"⚙️ توليد ملف سلة ({len(_export_src):,} منتج)",
                             key="miss_direct_salla_gen", use_container_width=True):
                    with st.spinner(f"⚙️ جارٍ بناء ملف سلة لـ {len(_export_src):,} منتج "
                                     "(اسم + ماركة + تصنيف + حجم + صورة + سعر مقترح + وصف)…"):
                        try:
                            _xb_salla = export_to_salla_shamel(
                                _clean_for_export(_export_src), st.session_state.get("analysis_df"),
                                verify_missing=False,
                                export_mode=st.session_state.get("salla_export_mode", "safe"),
                            )
                            st.session_state["_miss_direct_salla_xlsx"] = _xb_salla
                            st.success("✅ تم بناء الملف — اضغط تحميل.")
                        except Exception as _e_salla:
                            st.error(f"❌ تعذّر بناء ملف سلة: {_e_salla}")
            with _exp_d2:
                _xb_ready = st.session_state.get("_miss_direct_salla_xlsx")
                if _xb_ready:
                    st.download_button(
                        "📥 تحميل سلة الشامل (xlsx)", data=_xb_ready,
                        file_name="mahwous_missing_salla.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary", use_container_width=True, key="miss_direct_salla_dl",
                    )

            # ── أزرار تحديد جماعي ──
            _sel_c1, _sel_c2, _sel_c3, _sel_c4 = st.columns([2, 2, 2, 4])
            with _sel_c1:
                if st.button("✅ تحديد الكل", key="miss_select_all", use_container_width=True):
                    st.session_state["selected_missing_indices"] = list(filtered.index)
                    st.rerun()
            with _sel_c2:
                if st.button("🟢 تحديد المؤكدة", key="miss_select_green", use_container_width=True):
                    if "مستوى_الثقة" in filtered.columns:
                        _green = filtered[filtered["مستوى_الثقة"] == "green"]
                        st.session_state["selected_missing_indices"] = list(_green.index)
                    st.rerun()
            with _sel_c3:
                if st.button("❌ إلغاء الكل", key="miss_deselect_all", use_container_width=True):
                    st.session_state["selected_missing_indices"] = []
                    st.rerun()
            _sel_count = len(st.session_state.get("selected_missing_indices", []))
            with _sel_c4:
                if _sel_count > 0:
                    st.info(f"📌 محدد: {_sel_count} منتج")

            _export_ok, _export_issues = validate_export_product_dataframe(filtered)
            if not _export_ok:
                with st.expander(
                    "⚠️ تنبيه جودة التصدير: صفوف لا تطابق معايير سلة (اسم/سعر) — راجع قبل الاستيراد",
                    expanded=False,
                ):
                    for _ei in _export_issues[:40]:
                        st.caption(_ei)

            # ── v33: تجهيز المفقودات المؤكدة بنقرة واحدة ──────────────
            _green_df = filtered[filtered["مستوى_الثقة"] == "green"] if "مستوى_الثقة" in filtered.columns else filtered
            _pure_green = _green_df[_green_df["نوع_متاح"].str.strip() == ""] if "نوع_متاح" in _green_df.columns else _green_df

            st.markdown("### 🚀 تجهيز سريع — المفقودات المؤكدة")

            _qc1, _qc2, _qc3 = st.columns([3, 3, 4])
            with _qc1:
                st.metric("🟢 جاهز للتجهيز", f"{len(_pure_green):,} منتج")
            with _qc2:
                if _price_col and _price_col in _pure_green.columns:
                    _gval = pd.to_numeric(_pure_green[_price_col], errors="coerce").sum()
                    st.metric("💰 قيمة", f"{_gval:,.0f} ر.س")
            with _qc3:
                _auto_sku = st.toggle("🔑 توليد SKU تلقائي", value=True, key="miss_auto_sku")

            if st.button(
                f"📦 تجهيز {len(_pure_green):,} منتج مؤكد (ملف سلة جاهز)",
                type="primary", use_container_width=True, key="miss_prepare_all_green",
                disabled=len(_pure_green) == 0,
            ):
                _prog = st.progress(0, "⚙️ جاري التجهيز...")
                _total_g = len(_pure_green)
                _prepared = []
                for _gi, (_, _grow) in enumerate(_pure_green.iterrows()):
                    _rd = _grow.to_dict()
                    # توليد SKU إذا مفعّل
                    if _auto_sku:
                        _sk_brand = str(_rd.get("الماركة", "UNK"))[:3].upper()
                        _sk_size = str(_rd.get("الحجم", "100")).replace(" ", "")[:4]
                        _sk_hash = abs(hash(str(_rd.get("منتج_المنافس", "")))) % 9999
                        _rd["رمز المنتج sku"] = f"MH-{_sk_brand}-{_sk_size}-{_sk_hash:04d}"
                    _prepared.append(_rd)
                    if (_gi + 1) % 5 == 0 or _gi == _total_g - 1:
                        _prog.progress(min((_gi + 1) / _total_g, 0.99),
                                       f"⚙️ {_gi+1}/{_total_g}")
                _prog.progress(1.0, f"✅ تم تجهيز {_total_g} منتج")
                _ready_df = pd.DataFrame(_prepared)
                st.session_state["_v33_ready_green_df"] = _ready_df
                st.success(f"✅ تم تجهيز **{_total_g}** منتج بمعايير مهووس الكاملة!")

            # عرض أزرار التحميل إذا جاهز
            if st.session_state.get("_v33_ready_green_df") is not None:
                _ready_g = st.session_state["_v33_ready_green_df"]
                _our_df_ref = st.session_state.get("analysis_df")
                _export_mode = st.session_state.get("salla_export_mode", "safe")
                _dl1, _dl2, _dl3 = st.columns(3)
                with _dl1:
                    try:
                        _csv_b, _csv_c, _ = export_to_salla_shamel_csv(
                            _clean_for_export(_ready_g), _our_df_ref, verify_missing=True, export_mode=_export_mode
                        )
                        st.download_button(
                            f"📥 CSV سلة ({_csv_c} منتج)",
                            data=_csv_b,
                            file_name="mahwous_ready_products.csv",
                            mime="text/csv; charset=utf-8",
                            type="primary", use_container_width=True,
                        )
                    except Exception as _e_csv:
                        st.error(f"❌ خطأ CSV: {_e_csv}")
                with _dl2:
                    try:
                        _xlsx_b = export_to_salla_shamel(
                            _clean_for_export(_ready_g), _our_df_ref, verify_missing=True, export_mode=_export_mode
                        )
                        st.download_button(
                            "📥 XLSX Excel",
                            data=_xlsx_b,
                            file_name="mahwous_ready_products.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )
                    except Exception as _e_xl:
                        st.error(f"❌ خطأ XLSX: {_e_xl}")
                with _dl3:
                    if st.button("🗑️ مسح التجهيز", key="miss_clear_ready"):
                        st.session_state["_v33_ready_green_df"] = None
                        st.rerun()
                st.caption(f"📦 {len(_ready_g)} منتج جاهز — 40 عمود مطابق لقالب سلة")

            st.markdown("---")

            # ── خط الإنتاج الذكي (المعالجة والتحقق الإلزامي) ────────────────
            st.markdown("### ⚙️ تجهيز وتصدير المنتجات المحددة")

            if "selected_missing_indices" not in st.session_state:
                st.session_state.selected_missing_indices = []
            # تنظيف المؤشرات القديمة التي لم تعد موجودة في filtered
            if 'filtered' in dir() and hasattr(filtered, 'index'):
                _valid_indices = set(filtered.index)
                st.session_state.selected_missing_indices = [
                    i for i in st.session_state.selected_missing_indices if i in _valid_indices
                ]
            if "ready_missing_df" not in st.session_state:
                st.session_state.ready_missing_df = None
            if "missing_dup_uncertain" not in st.session_state:
                st.session_state.missing_dup_uncertain = []

            c1, c2 = st.columns([2, 1])
            with c1:
                st.info(f"المنتجات المحددة للمعالجة: {len(st.session_state.selected_missing_indices)}")
                _debug_log("H4", "app.py:missing_pipeline_ui", "Missing pipeline rendered", {
                    "selected_count": len(st.session_state.selected_missing_indices),
                    "policy": st.session_state.get("miss_dup_policy", ""),
                })
                with st.expander("🛡️ سياسة منع التكرار قبل البدء", expanded=False):
                    uncertain_policy = st.radio(
                        "عند وجود حالة مشكوك فيها:",
                        ["❌ استبعاد تلقائي", "⏸️ إيقاف وطلب قرار", "▶️ متابعة مع التحذير"],
                        index=1,
                        key="miss_dup_policy",
                        horizontal=True,
                    )
                    st.checkbox(
                        "استخدم تحقق AI للحالات المشكوك فيها فقط (أدق لكنه أبطأ)",
                        value=True,
                        key="miss_dup_ai_verify",
                    )
                if st.button("🤖 1. بدء الفحص والمعالجة الذكية (إلزامي)", type="primary", use_container_width=True):
                    if not st.session_state.selected_missing_indices:
                        st.warning("الرجاء تحديد منتج واحد على الأقل من القائمة بالأسفل.")
                    else:
                        st.session_state.ready_missing_df = None
                        st.session_state.missing_dup_uncertain = []
                        with st.status("جاري المعالجة الذكية...", expanded=True) as status:
                            processed_rows = []
                            selected_df = filtered.loc[
                                filtered.index.isin(st.session_state.selected_missing_indices)
                            ]

                            # ── Phase A: RapidFuzz Bulk Screening ──────────────
                            st.write("⚡ المرحلة 1: فحص سريع بـ RapidFuzz...")
                            our_prods = []
                            if st.session_state.analysis_df is not None and not st.session_state.analysis_df.empty:
                                our_prods = [
                                    str(n).strip()
                                    for n in st.session_state.analysis_df["المنتج"].dropna().tolist()
                                    if str(n).strip() and str(n).strip().lower() not in ("nan", "none")
                                ]

                            # Pre-build normalized catalog ONCE
                            _our_norms = [_norm_dup_text(n) for n in our_prods] if our_prods else []

                            confirmed_skipped = 0
                            uncertain_skipped = 0
                            uncertain_pending = []
                            # Buckets: confirmed_dup, uncertain, truly_missing
                            _truly_missing_rows = []  # (idx, row) tuples to enrich
                            _ai_verify_queue = []     # (idx, row, candidates) for Phase B

                            try:
                                from rapidfuzz import process as rf_process, fuzz as rf_fuzz
                                _has_rapidfuzz = True
                            except ImportError:
                                _has_rapidfuzz = False

                            for idx, row in selected_df.iterrows():
                                p_name = str(row.get("منتج_المنافس", "")).strip()
                                if not p_name:
                                    continue
                                p_norm = _norm_dup_text(p_name)

                                if not _our_norms or not _has_rapidfuzz:
                                    # No catalog or no rapidfuzz → treat as truly missing
                                    _truly_missing_rows.append((idx, row))
                                    continue

                                # RapidFuzz: top 5 candidates — C-optimized, ~0.5ms per query
                                _top5 = rf_process.extract(
                                    p_norm, _our_norms,
                                    scorer=rf_fuzz.token_set_ratio,
                                    limit=min(5, len(_our_norms)),
                                )
                                best_score = _top5[0][1] if _top5 else 0

                                if best_score >= 88:
                                    # Confirmed duplicate — auto-skip
                                    _matched_name = our_prods[_top5[0][2]] if _top5 else ""
                                    st.write(f"⛔ مكرر مؤكد: {p_name[:30]} ≈ {_matched_name[:30]} ({best_score:.0f}%)")
                                    confirmed_skipped += 1
                                elif best_score >= 68:
                                    # Uncertain — queue for Phase B AI verification
                                    _candidates = [
                                        {"name": our_prods[c[2]], "score": c[1]}
                                        for c in _top5[:3]
                                        if c[1] >= 50
                                    ]
                                    _ai_verify_queue.append((idx, row, _candidates))
                                else:
                                    # < 68 — truly missing
                                    _truly_missing_rows.append((idx, row))

                            st.write(
                                f"⚡ نتائج الفحص السريع: "
                                f"✅ {len(_truly_missing_rows)} فريد | "
                                f"⚠️ {len(_ai_verify_queue)} مشكوك | "
                                f"⛔ {confirmed_skipped} مكرر"
                            )

                            # ── Phase B: AI Verification (uncertain only) ──────
                            if _ai_verify_queue and st.session_state.get("miss_dup_ai_verify", True):
                                _ai_max = min(len(_ai_verify_queue), 25)  # حد أقصى لمنع التعليق
                                if len(_ai_verify_queue) > _ai_max:
                                    st.write(f"⚠️ سيتم فحص {_ai_max} من {len(_ai_verify_queue)} حالة مشكوكة (حد أقصى)")
                                    # البقية تعامل ك truly missing
                                    for _q_idx, _q_row, _q_cands in _ai_verify_queue[_ai_max:]:
                                        _truly_missing_rows.append((_q_idx, _q_row))
                                st.write(f"🤖 المرحلة 2: تحقق AI لـ {_ai_max} حالة مشكوكة...")
                                for _qi, (_q_idx, _q_row, _q_cands) in enumerate(_ai_verify_queue[:_ai_max]):
                                    _q_name = str(_q_row.get("منتج_المنافس", "")).strip()
                                    st.write(f"  🔍 [{_qi+1}/{_ai_max}] {_q_name[:35]}...")

                                    try:
                                        _ai_result = ai_verify_dedup(_q_name, _q_cands)
                                        _ai_match = _ai_result.get("match", False)
                                        _ai_conf = _ai_result.get("confidence", 0)
                                        _ai_matched = _ai_result.get("matched_name", "")

                                        if _ai_match and _ai_conf >= 75:
                                            st.write(f"  ⛔ AI أكد التكرار: {_q_name[:28]} ≈ {_ai_matched[:28]} ({_ai_conf}%)")
                                            confirmed_skipped += 1
                                        elif (not _ai_match) and _ai_conf >= 65:
                                            # AI confidently says NOT a match → truly missing
                                            _truly_missing_rows.append((_q_idx, _q_row))
                                        else:
                                            # Still uncertain after AI
                                            _best_cand = _q_cands[0]["name"] if _q_cands else "—"
                                            _best_score = _q_cands[0]["score"] if _q_cands else 0
                                            _item = {
                                                "المنتج_المنافس": _q_name,
                                                "مرشح_لدينا": _best_cand,
                                                "سبب": f"تشابه {_best_score:.0f}% — AI غير حاسم ({_ai_conf}%)",
                                                "_idx": str(_q_idx),
                                                "_row": _q_row.to_dict() if hasattr(_q_row, "to_dict") else dict(_q_row),
                                            }
                                            uncertain_pending.append(_item)
                                            if uncertain_policy == "❌ استبعاد تلقائي":
                                                st.write(f"  ⚠️ استبعاد مشكوك: {_q_name[:30]}")
                                                uncertain_skipped += 1
                                            elif uncertain_policy == "⏸️ إيقاف وطلب قرار":
                                                pass  # will pause after loop
                                            else:
                                                # متابعة مع التحذير
                                                _truly_missing_rows.append((_q_idx, _q_row))
                                                st.write(f"  ⚠️ متابعة رغم الشك: {_q_name[:30]}")
                                    except Exception as _ai_err:
                                        # فشل AI → اعتبره مفقوداً فعلاً
                                        _truly_missing_rows.append((_q_idx, _q_row))
                                        st.write(f"  ⚠️ تعذّر التحقق: {_q_name[:30]} — {str(_ai_err)[:50]}")
                            elif _ai_verify_queue:
                                # AI verify disabled — apply policy directly
                                for _q_idx, _q_row, _q_cands in _ai_verify_queue:
                                    _q_name = str(_q_row.get("منتج_المنافس", "")).strip()
                                    _best_cand = _q_cands[0]["name"] if _q_cands else "—"
                                    _best_score = _q_cands[0]["score"] if _q_cands else 0
                                    _item = {
                                        "المنتج_المنافس": _q_name,
                                        "مرشح_لدينا": _best_cand,
                                        "سبب": f"تشابه {_best_score:.0f}%",
                                        "_idx": str(_q_idx),
                                        "_row": _q_row.to_dict() if hasattr(_q_row, "to_dict") else dict(_q_row),
                                    }
                                    uncertain_pending.append(_item)
                                    if uncertain_policy == "❌ استبعاد تلقائي":
                                        uncertain_skipped += 1
                                    elif uncertain_policy == "⏸️ إيقاف وطلب قرار":
                                        pass
                                    else:
                                        _truly_missing_rows.append((_q_idx, _q_row))

                            # ── Phase C: Enrichment (only truly missing) ───────
                            if uncertain_pending and uncertain_policy == "⏸️ إيقاف وطلب قرار":
                                st.session_state.missing_dup_uncertain = uncertain_pending
                                status.update(label="⏸️ تم إيقاف المعالجة لوجود حالات مشكوك فيها", state="error", expanded=True)
                                st.warning("تم الإيقاف: راجع جدول الحالات المشكوك فيها بالأسفل ثم غيّر السياسة أو عدّل الاختيار.")
                            else:
                                _enrich_max = 50  # حد أقصى للإثراء لمنع التعليق
                                _enrichable = _truly_missing_rows[:_enrich_max]
                                if _enrichable and not ANY_AI_PROVIDER_CONFIGURED:
                                    st.warning(
                                        "🔴 الذكاء الاصطناعي غير مُفعّل — سيُكتفى بالوصف القالبي بدون "
                                        "إثراء حقيقي (مكونات/عائلة عطرية). أضف مفتاح GEMINI_API_KEY "
                                        "للحصول على أوصاف مهووس كاملة."
                                    )
                                if _enrichable:
                                    st.write(f"📝 المرحلة 3: إثراء {len(_enrichable)} منتج (Fragrantica + AI)...")
                                    if len(_truly_missing_rows) > _enrich_max:
                                        st.write(f"⚠️ سيتم إثراء {_enrich_max} من {len(_truly_missing_rows)} منتج (حد أقصى)")
                                        # البقية تضاف بدون إثراء
                                        for _e_idx, _e_row in _truly_missing_rows[_enrich_max:]:
                                            processed_rows.append(_e_row.copy())
                                for _ei, (_e_idx, _e_row) in enumerate(_enrichable):
                                    try:
                                        p_name = str(_e_row.get("منتج_المنافس", "")).strip()
                                        p_price = safe_float(_e_row.get("سعر_المنافس", 0))
                                        st.write(f"  📦 [{_ei+1}/{len(_enrichable)}] {p_name[:35]}...")

                                        frag_info = fetch_fragrantica_info(p_name)
                                        raw_data = f"الاسم: {p_name}, السعر: {p_price}"
                                        if frag_info.get("success"):
                                            raw_data += f", المكونات: {', '.join(frag_info.get('top_notes', []))}"

                                        html_body = generate_mahwous_description(
                                            product_name=p_name,
                                            price=p_price,
                                            fragrantica_data=frag_info if frag_info.get("success") else None,
                                        )
                                        seo_data = generate_seo_description(raw_data)

                                        new_row = _e_row.copy()
                                        new_row["وصف_AI"] = html_body or seo_data.get("markdown_desc", "")
                                        new_row["الماركة_الرسمية"] = seo_data.get(
                                            "exact_brand",
                                            str(_e_row.get("الماركة", "")),
                                        )
                                        new_row["التصنيف_الرسمي"] = seo_data.get(
                                            "exact_category",
                                            "العطور",
                                        )
                                        if frag_info.get("success"):
                                            new_row["top_notes"]   = ", ".join(frag_info.get("top_notes", []))
                                            new_row["heart_notes"] = ", ".join(frag_info.get("middle_notes", []))
                                            new_row["base_notes"]  = ", ".join(frag_info.get("base_notes", []))
                                        processed_rows.append(new_row)
                                    except Exception as _enrich_err:
                                        # فشل إثراء منتج واحد → أضفه بدون إثراء
                                        processed_rows.append(_e_row.copy())
                                        st.write(f"  ⚠️ تعذّر إثراء: {str(_enrich_err)[:50]}")

                                status.update(label="✅ اكتملت المعالجة!", state="complete", expanded=False)

                            if confirmed_skipped or uncertain_skipped:
                                st.caption(
                                    f"منع التكرار: مؤكد {confirmed_skipped} | مشكوك مستبعد {uncertain_skipped}"
                                )
                            if processed_rows:
                                st.session_state.ready_missing_df = pd.DataFrame(processed_rows)
                                st.success(
                                    f"تمت معالجة {len(processed_rows)} منتج بنجاح، "
                                    "ومطابقة الماركات وتوليد الأوصاف."
                                )
                            else:
                                if not (uncertain_pending and uncertain_policy == "⏸️ إيقاف وطلب قرار"):
                                    st.error("لم يتم معالجة أي منتج (قد تكون جميعها مكررة).")

            with c2:
                if st.session_state.get("ready_missing_df") is not None and not st.session_state.ready_missing_df.empty:
                    _ready_df = st.session_state.ready_missing_df
                    _our_df_ref = st.session_state.get("our_df")
                    salla_export_mode = st.radio(
                        "⚙️ وضع تصدير ملف سلة (للمفقودات):",  # FIX: Salla Export Mode Toggle
                        options=[
                            "Strict Safe Mode (ينصح به لتجنب الأخطاء)",
                            "Category Path Mode (استخدام المسار الكامل للتصنيف)",
                        ],
                        index=0 if st.session_state.get("salla_export_mode", "safe") == "safe" else 1,
                        help="الوضع الآمن يرسل اسم التصنيف النهائي فقط. وضع المسار يرسل المسار الكامل (مثل: العطور > عطور رجالية) ويجب أن يكون متطابقاً 100% في متجرك.",
                        key="missing_salla_export_mode_ui",
                    )
                    st.session_state["salla_export_mode"] = (  # FIX: Salla Export Mode Toggle
                        "safe" if "Strict" in salla_export_mode else "path"
                    )
                    _export_mode = st.session_state.get("salla_export_mode", "safe")

                    # ── التحقق من المنتجات المفقودة فعلاً ─────────────────
                    try:
                        _truly_missing, _found_in_cat = verify_truly_missing(
                            _ready_df, _our_df_ref, fuzzy_threshold=82.0
                        )
                        if not _found_in_cat.empty:
                            st.warning(
                                f"⚠️ **{len(_found_in_cat)}** منتج وُجد في الكتالوج بأسماء مختلفة "
                                f"وسيُستبعد من التصدير لتفادي التكرار.",
                                icon="🔍"
                            )
                            with st.expander(f"👁️ منتجات موجودة في الكتالوج ({len(_found_in_cat)})", expanded=False):
                                st.dataframe(_found_in_cat[["منتج_المنافس","المنافس","سعر_المنافس"]].head(20)
                                             if "منتج_المنافس" in _found_in_cat.columns
                                             else _found_in_cat.head(20),
                                             use_container_width=True)
                        export_df = _truly_missing if not _truly_missing.empty else _ready_df
                    except Exception:
                        export_df = _ready_df

                    st.caption(f"📦 **{len(export_df)}** منتج جاهز للتصدير لسلة")

                    # ── زر CSV (مطابق لقالب سلة الرسمي) ─────────────────
                    try:
                        _csv_bytes, _csv_count, _ = export_to_salla_shamel_csv(
                            _clean_for_export(export_df), _our_df_ref, verify_missing=False, export_mode=_export_mode  # FIX: Salla Export Mode Toggle
                        )
                        st.download_button(
                            "📥 2. تحميل ملف سلة CSV (مطابق للقالب الرسمي)",
                            data=_csv_bytes,
                            file_name="mahwous_missing_ready.csv",
                            mime="text/csv; charset=utf-8",
                            type="primary",
                            use_container_width=True,
                            help=f"يحتوي على {_csv_count} منتج — قالب سلة الرسمي مع صف بيانات المنتج",
                        )
                    except Exception as _csv_exp:
                        st.error(f"❌ فشل توليد CSV سلة: {_csv_exp}")

                    # ── زر XLSX (احتياطي) ────────────────────────────────
                    try:
                        _xlsx_bytes = export_to_salla_shamel(
                            _clean_for_export(export_df), _our_df_ref, verify_missing=False, export_mode=_export_mode  # FIX: Salla Export Mode Toggle
                        )
                        st.download_button(
                            "📥 تحميل ملف سلة XLSX (Excel)",
                            data=_xlsx_bytes,
                            file_name="mahwous_missing_ready.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                        )
                    except Exception as _xlsx_exp:
                        st.error(f"❌ فشل توليد XLSX: {_xlsx_exp}")

                    # ── Phase 3: تأكيد اكتمال التصدير (Lifecycle Closing) ────
                    st.divider()
                    if st.button(
                        "✅ 3. تأكيد اكتمال التصدير لسلة (تعليم كمُعالَج)",
                        use_container_width=True,
                        help="بعد تحميل الملف ورفعه لسلة، اضغط هنا لتعليم المنتجات كمُعالَجة حتى لا تظهر مجدداً.",
                        key="confirm_salla_export_lifecycle",
                    ):
                        _lc_count = 0
                        _lc_link_col = None
                        for _c in ["رابط_المنافس", "الرابط", "رابط المنتج", "url", "رابط", "Link"]:
                            if _c in export_df.columns:
                                _lc_link_col = _c
                                break
                        for _, _lc_row in export_df.iterrows():
                            _lc_name = str(_lc_row.get("منتج_المنافس", "") or _lc_row.get("أسم المنتج", "")).strip()
                            _lc_comp = str(_lc_row.get("المنافس", "")).strip()
                            _lc_price = safe_float(_lc_row.get("سعر_المنافس", 0))
                            _lc_url = str(_lc_row.get(_lc_link_col, "")).strip() if _lc_link_col else ""
                            _lc_pk = f"miss_{_lc_name[:30]}_{_lc_comp}"
                            save_processed(
                                _lc_pk,
                                _lc_name,
                                _lc_comp,
                                "export_salla",
                                new_price=_lc_price,
                                comp_url=_lc_url,
                            )
                            # Update session tracking sets
                            if _lc_url:
                                _track_processed_missing_url(_lc_url)
                            _lc_count += 1
                        st.success(f"✅ تم تعليم {_lc_count} منتج كمُعالَج — لن تظهر مجدداً في قائمة المفقودات.")
                        st.session_state.ready_missing_df = None
                        st.rerun()
                else:
                    st.button(
                        "📥 2. تحميل ملف سلة (جاهز للاستيراد)",
                        disabled=True,
                        use_container_width=True,
                        help="قم بالمعالجة أولاً",
                        key="miss_salla_download_disabled",
                    )

            if st.session_state.get("missing_dup_uncertain"):
                with st.expander("⚠️ حالات مشكوك فيها (تحتاج قرار)", expanded=True):
                    st.caption("اتخذ قراراً سريعاً لكل حالة بدلاً من إعادة المعالجة:")
                    _uncertain_list = list(st.session_state.missing_dup_uncertain)
                    _to_remove = []
                    _to_send_quick = []
                    for _ui, _uitem in enumerate(_uncertain_list):
                        _u_name = _uitem.get("المنتج_المنافس", "")
                        _u_cand = _uitem.get("مرشح_لدينا", "—")
                        _u_reason = _uitem.get("سبب", "")
                        _row_dict = _uitem.get("_row", {}) or {}
                        _u_price = safe_float(_row_dict.get("سعر_المنافس", 0))
                        _u_comp = str(_row_dict.get("المنافس", ""))

                        st.markdown(
                            f"**{_u_name[:60]}**  \n"
                            f"<span style='color:#999;font-size:.85rem'>"
                            f"مرشح لدينا: {_u_cand[:60]} — {_u_reason}</span>",
                            unsafe_allow_html=True,
                        )
                        _bc1, _bc2, _bc3 = st.columns(3)
                        with _bc1:
                            if st.button("✅ مفقود فعلاً (أرسل)", key=f"unc_send_{_ui}",
                                         use_container_width=True):
                                if _u_price > 0:
                                    _send_p = max(int(round(_u_price - 1)), 1)
                                    _img = str(_row_dict.get("صورة_المنافس", "") or "").strip()
                                    _payload = {
                                        "name": _u_name,
                                        "price": _send_p,
                                        "image_url": _img,
                                        "section": "missing",
                                        "competitor": _u_comp,
                                        "comp_name": _u_name,
                                        "brand": str(_row_dict.get("الماركة", "")),
                                    }
                                    with st.spinner("جاري الإرسال..."):
                                        _r = send_missing_products([_payload])
                                    if _r.get("sent", 0) > 0:
                                        st.success(f"✅ تم إرسال «{_u_name[:35]}»")
                                        save_processed(
                                            f"miss_unc_{_u_name[:30]}_{_u_comp}",
                                            _u_name, _u_comp, "send_missing_uncertain",
                                            new_price=_send_p,
                                        )
                                        _to_remove.append(_ui)
                                    else:
                                        st.error(f"❌ فشل: {_r.get('message','')}")
                                else:
                                    st.error("❌ السعر غير صالح")
                        with _bc2:
                            if st.button("⛔ موجود (تجاهل)", key=f"unc_skip_{_ui}",
                                         use_container_width=True):
                                save_processed(
                                    f"miss_unc_{_u_name[:30]}_{_u_comp}",
                                    _u_name, _u_comp, "ignored_uncertain",
                                    notes=f"موجود لدينا — {_u_cand[:50]}",
                                )
                                _to_remove.append(_ui)
                                st.success(f"⛔ تم تجاهل «{_u_name[:35]}»")
                        with _bc3:
                            if st.button("⏭️ تأجيل", key=f"unc_skip_later_{_ui}",
                                         use_container_width=True,
                                         help="إبقاؤه في القائمة للمراجعة لاحقاً"):
                                st.toast(f"⏭️ تم تأجيل «{_u_name[:30]}» — سيبقى في قائمة المراجعة", icon="⏭️")
                        st.markdown('<hr style="border:none;border-top:1px solid #1a2a44;margin:6px 0">', unsafe_allow_html=True)

                    if _to_remove:
                        st.session_state.missing_dup_uncertain = [
                            it for i, it in enumerate(_uncertain_list) if i not in _to_remove
                        ]
                        st.rerun()

            # ── خيارات الإرسال الذكي ─────────────────────────────
            _conf_opts = {"🟢 مؤكدة فقط": "green", "🟡 محتملة": "yellow", "🔵 الكل": ""}
            _conf_sel = st.selectbox("مستوى الثقة", list(_conf_opts.keys()), key="miss_conf_sel")
            _conf_val = _conf_opts[_conf_sel]
            if st.button("📤 إرسال بدفعات ذكية لـ Make", key="miss_make_all"):
                # فلتر المفقودة الفعلية فقط (بدون التستر/الأساسي المتاح)
                _to_send = filtered[filtered["نوع_متاح"].str.strip() == ""] if "نوع_متاح" in filtered.columns else filtered

                is_valid, issues = validate_export_product_dataframe(_to_send)
                if not is_valid:
                    st.error("❌ تم إيقاف الإرسال! البيانات لا تطابق معايير سلة الصارمة:")
                    for issue in issues:
                        st.warning(issue)
                else:
                    products = export_to_make_format(_clean_for_export(_to_send), "missing")
                    # إضافة مستوى الثقة لكل منتج
                    for _ip, _pr_row in enumerate(products):
                        if _ip < len(_to_send):
                            _pr_row["مستوى_الثقة"] = str(_to_send.iloc[_ip].get("مستوى_الثقة", "green"))
                    _prog_bar = st.progress(0, text="جاري الإرسال...")
                    _status_txt = st.empty()

                    def _miss_progress(sent, failed, total, cur_name):
                        pct = (sent + failed) / max(total, 1)
                        _prog_bar.progress(min(pct, 1.0), text=f"إرسال: {sent}/{total} | {cur_name}")
                        _status_txt.caption(f"✅ {sent} | ❌ {failed} | الإجمالي {total}")

                    res = send_batch_smart(
                        products,
                        batch_type="new",
                        batch_size=20,
                        max_retries=3,
                        progress_cb=_miss_progress,
                        confidence_filter=_conf_val,
                    )
                    _prog_bar.progress(1.0, text="اكتمل")
                    _full_success = (res.get("sent", 0) == len(products)) and (res.get("failed", 0) == 0)  # FIX: Transparency & Reversibility
                    if _full_success:
                        st.success(res["message"])
                        # FIX: Missing Products Display Recovery
                        _miss_link_col = None
                        for _c in ["رابط_المنافس", "الرابط", "رابط المنتج", "url", "رابط", "Link"]:
                            if _c in _to_send.columns:
                                _miss_link_col = _c
                                break
                        if _miss_link_col:
                            for _u in _to_send[_miss_link_col].dropna().astype(str):
                                _track_processed_missing_url(_u)
                        # v26: احفظ في قائمة المعالجة
                        for _, _pr in _to_send.iterrows():
                            _pk = f"miss_{str(_pr.get('منتج_المنافس',''))[:30]}_{str(_pr.get('المنافس',''))}"
                            save_processed(
                                _pk,
                                str(_pr.get('منتج_المنافس','')),
                                str(_pr.get('المنافس','')),
                                "send_missing",
                                new_price=safe_float(_pr.get('سعر_المنافس',0)),
                            )
                        st.rerun()  # FIX: Smart Workflow & AI Tracking
                    else:
                        st.error(f"❌ فشل الإرسال الكامل إلى Make: {res.get('message', 'خطأ غير معروف')}")  # FIX: Transparency & Reversibility
                        st.error("لم يتم تعليم أي منتج كمُعالج لأن الإرسال لم ينجح بالكامل.")  # FIX: Transparency & Reversibility
                    if res.get("errors"):
                        with st.expander(f"❌ منتجات فشلت ({len(res['errors'])})"):
                            for _en in res["errors"]:
                                st.caption(f"• {_en}")

            st.caption(f"{len(filtered)} منتج — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

            # ── 🤖 فحص المكررات (الموزّع الذكي) ───────────────────────────
            with st.expander("🤖 فحص المكررات بالذكاء الاصطناعي", expanded=False):
                st.caption(
                    "يفحص المنتجات المفقودة عبر 3 طبقات (مفتاح ثابت + تشابه ضبابي + تحقق AI). "
                    "كل منتج يُؤكَّد كمكرر يُرحَّل تلقائياً إلى « ⚠️ تحت المراجعة » مع سجل تدقيق كامل."
                )
                if st.button("🔁 ابدأ فحص المكررات", key="miss_dup_scan", type="primary"):
                    try:
                        from engines.duplicate_detector import detect as _dup_detect
                        from engines.smart_router import ingest_product as _smart_ingest
                        from utils.product_key import make_product_key as _mk_key
                        # كتالوج البحث = كل صفوف التحليل (المنتج عندنا)
                        _adf = st.session_state.get("analysis_df")
                        _catalog = []
                        if _adf is not None and not _adf.empty and "المنتج" in _adf.columns:
                            for _, _r in _adf.iterrows():
                                _catalog.append({
                                    "name":  str(_r.get("المنتج", "")),
                                    "store": "mahwous",
                                    "url":   "",
                                })
                        _existing = set()
                        _moved = 0; _kept = 0; _errs = 0
                        with st.spinner("🤖 جاري الفحص…"):
                            for _i, _row in filtered.iterrows():
                                try:
                                    _nm  = str(_row.get("منتج_المنافس", ""))
                                    _cmp = str(_row.get("المنافس", ""))
                                    _url = competitor_product_url_from_row(_row) or ""
                                    _key = _mk_key(_nm, _cmp, _url)
                                    _verdict = _dup_detect(
                                        {"name": _nm, "store": _cmp, "url": _url},
                                        _catalog, existing_keys=_existing,
                                    )
                                    _existing.add(_key)
                                    # سجّل في الموزّع الذكي (مصدر الحقيقة الموحّد)
                                    _smart_ingest(
                                        {"name": _nm, "store": _cmp, "url": _url,
                                         "price": safe_float(_row.get("سعر_المنافس", 0))},
                                        _catalog, existing_keys=_existing,
                                        decided_by="duplicate_scan",
                                    )
                                    if _verdict.decision == "DUPLICATE":
                                        # رحّل المكرر إلى « تحت المراجعة »
                                        _hk = f"missing_{_nm}"
                                        st.session_state.hidden_products.add(_hk)
                                        save_hidden_product(_hk, _nm, "moved_to_review_duplicate")
                                        log_decision(_nm, "missing", "review",
                                                     f"مكرر ({_verdict.confidence:.0f}%): {_verdict.reason}",
                                                     0, safe_float(_row.get("سعر_المنافس", 0)),
                                                     0, _cmp)
                                        _moved += 1
                                    else:
                                        _kept += 1
                                except Exception:
                                    _errs += 1
                        st.success(
                            f"✅ تم الفحص: {_moved} منتج رُحّل إلى « تحت المراجعة » | "
                            f"{_kept} منتج بقي في المفقودة | أخطاء: {_errs}"
                        )
                        if _moved > 0:
                            st.rerun()
                    except Exception as _e_dup:
                        st.error(f"❌ تعذّر الفحص: {_e_dup}")

            # ── عرض المنتجات ──────────────────────────────────────────────
            # طيّ تكرار العرض فقط (لا يمسّ الإجماليات ولا الإرسال — يبقى على filtered)
            _display_df, _disp_dups = _dedup_missing_display(filtered)
            if _disp_dups > 0:
                st.caption(
                    f"🔁 طُويت {_disp_dups} بطاقة مكرّرة بصرياً للعرض فقط "
                    f"(الإجمالي والإرسال يبقيان على {len(filtered):,} منتج)"
                )
            # ── v33: تنقل موحّد بأسهم وأرقام صفحات ──
            # ⚡ 12 بدل 20/صفحة: بطاقات المفقودات ثقيلة (HTML+صور) → صفحة أخف وأسرع
            _ms, _me, _mp = render_pagination(len(_display_df), 12, "miss")
            page_df = _display_df.iloc[_ms:_me]

            # ⚡ خريطة بحث مسبقة (اسم منتجنا → أول صف مطابق في analysis_df) تُبنى مرة
            # واحدة بدل مسح DataFrame كامل لكل بطاقة. تحفظ صفوف Series كاملة فتطابق
            # دلالة [df["المنتج"]==x].iloc[0] تماماً (نفس كل الأعمدة).
            _adf_pot_loop = st.session_state.analysis_df
            _adf_first_by_name = {}
            if (isinstance(_adf_pot_loop, pd.DataFrame) and not _adf_pot_loop.empty
                    and "المنتج" in _adf_pot_loop.columns):
                try:
                    _dedup_adf = _adf_pot_loop.drop_duplicates(subset="المنتج", keep="first")
                    for _pos in range(len(_dedup_adf)):
                        _r_series = _dedup_adf.iloc[_pos]
                        _adf_first_by_name[_r_series["المنتج"]] = _r_series
                except Exception:
                    _adf_first_by_name = {}

            for idx, row in page_df.iterrows():
                name  = str(row.get("منتج_المنافس", ""))
                # مفتاح إخفاء مستقر بالاسم (لا موضعي): يبقى المنتج المُرسَل/المُتجاهَل
                # مخفياً حتى بعد إعادة الحساب (idx يتغيّر، الاسم لا).
                _miss_key = f"missing_{name}"
                if _miss_key in st.session_state.hidden_products:
                    continue

                select_col, card_col = st.columns([0.5, 9.5])
                with select_col:
                    _selected_ids = st.session_state.get("selected_missing_indices", [])
                    is_selected = st.checkbox(
                        "تحديد",
                        key=f"sel_{idx}",
                        value=idx in _selected_ids,
                        label_visibility="collapsed",
                    )
                    if is_selected and idx not in st.session_state.selected_missing_indices:
                        st.session_state.selected_missing_indices.append(idx)
                    elif not is_selected and idx in st.session_state.selected_missing_indices:
                        st.session_state.selected_missing_indices.remove(idx)

                price           = safe_float(row.get("سعر_المنافس", 0))
                brand           = str(row.get("الماركة", ""))
                comp            = str(row.get("المنافس", ""))
                size            = str(row.get("الحجم", "") or "").strip()
                # Fallback: استخراج الحجم من اسم المنتج إن لم يوجد
                if not size or size.lower() in ("nan", "none"):
                    # re مستورد على مستوى الوحدة (سطر 61) — لا داعي لاستيراد داخل الحلقة
                    _name_for_size = str(row.get("منتج_المنافس", "") or row.get("المنتج", "") or name)
                    _m_size = re.search(r"(\d{1,4})\s*(?:مل|ملي|ml|ML|mL)\b", _name_for_size)
                    size = f"{_m_size.group(1)} مل" if _m_size else ""
                ptype           = str(row.get("النوع", ""))
                _comp_show = _humanize_competitor_upload(comp)
                _title_display = _display_name_for_missing_row(row)
                if not _title_display:
                    _u_title = competitor_product_url_from_row(row)
                    if not str(_u_title or "").strip().lower().startswith("http") and _is_http_url_text(name):
                        _u_title = name.strip()
                    if str(_u_title or "").strip().lower().startswith("http"):
                        _ft = _cached_title_from_product_url(str(_u_title).strip())
                        if _ft:
                            _title_display = _ft
                if _title_display:
                    nm_ai = _title_display
                elif not _is_http_url_text(name):
                    nm_ai = name
                else:
                    _fb = f"{brand} {size} {ptype}".strip()
                    if not _fb:
                        _fb = _comp_show if _comp_show != "—" else "منتج"
                    nm_ai = _fb
                note            = str(row.get("ملاحظة", ""))
                # استخراج معرف المنتج (SKU/الكود)
                _miss_pid_raw = (
                    row.get("معرف_المنافس", "") or
                    row.get("product_id", "") or
                    row.get("رقم المنتج", "") or
                    row.get("رقم_المنتج", "") or
                    row.get("SKU", "") or
                    row.get("sku", "") or
                    row.get("الكود", "") or
                    row.get("كود", "") or
                    row.get("الباركود", "") or ""
                )
                _miss_pid = ""
                if _miss_pid_raw and str(_miss_pid_raw) not in ("", "nan", "None", "0", "NaN"):
                    try: _miss_pid = str(int(float(str(_miss_pid_raw))))
                    except Exception: _miss_pid = str(_miss_pid_raw).strip()
                variant_label   = str(row.get("نوع_متاح", ""))
                variant_product = str(row.get("منتج_متاح", ""))
                variant_score   = safe_float(row.get("نسبة_التشابه", 0))
                is_tester_flag  = bool(row.get("هو_تستر", False))
                conf_level      = str(row.get("مستوى_الثقة", "green"))
                conf_score      = safe_float(row.get("درجة_التشابه", 0))
                suggested_price = round(price - 1, 2) if price > 0 else 0

                _is_similar = "⚠️" in note
                _has_variant= bool(variant_label and variant_label.strip())
                _is_tester_type = "تستر" in variant_label if _has_variant else False
                if idx == page_df.index[0]:
                    _debug_log("H3", "app.py:missing_cards_loop", "Rendering first missing card", {
                        "idx": str(idx),
                        "name": name[:80],
                        "has_variant": _has_variant,
                        "variant_product": variant_product[:80],
                    })

                # ملاحظة: إشارات اللون/النوع المتاح/التستر تُصاغ الآن داخل
                # miss-card-v32 (styles.miss_card) من حقول الصف مباشرةً.

                _miss_img = str(row.get("صورة_المنافس", "") or "").strip()
                if not _miss_img:
                    _miss_img = _first_image_url_from_row(row) or ""
                _miss_comp_url = competitor_product_url_from_row(row)
                if not _miss_comp_url and _is_http_url_text(name):
                    _miss_comp_url = name.strip()
                if not _miss_img and _miss_comp_url.startswith("http"):
                    _miss_img = _cached_thumb_from_product_url(_miss_comp_url)

                _our_potential_img = ""
                if variant_product and variant_product in _adf_first_by_name:
                    _our_potential_img, _ = row_media_urls_from_analysis(
                        _adf_first_by_name[variant_product]
                    )

                with card_col:
                    if _our_potential_img and _has_variant:
                        images_html = _processed_dual_image_html(
                            _our_potential_img,
                            _miss_img,
                            "منتجنا (محتمل)",
                            name[:40],
                        )
                        st.markdown(images_html, unsafe_allow_html=True)
                    # v33: بطاقة محسّنة مع بطاقات فرعية لكل منافس
                    _comp_details_raw = row.get("تفاصيل_المنافسين", [])
                    if isinstance(_comp_details_raw, str):
                        try:
                            import json as _j33
                            _comp_details_raw = _j33.loads(_comp_details_raw)
                        except Exception:
                            _comp_details_raw = []
                    if not isinstance(_comp_details_raw, list) or not _comp_details_raw:
                        # fallback: بناء بطاقة واحدة من البيانات المتوفرة
                        _comp_details_raw = [{
                            "المنافس": _comp_show,
                            "اسم_المنتج": _title_display or name,
                            "السعر": float(price) if price else 0.0,
                            "الصورة": _miss_img,
                            "الرابط": _miss_comp_url,
                            "الحجم": size,
                            "النوع": ptype,
                            "المعرف": _miss_pid,
                        }]
                    st.markdown(miss_card_v2({
                        "منتج_المنافس":       _title_display or name,
                        "الماركة":             brand,
                        "الحجم":               size,
                        "النوع":               ptype,
                        "الجنس":               str(row.get("الجنس", "") or ""),
                        "مستوى_الثقة":         conf_level,
                        "درجة_الأولوية":       int(row.get("درجة_الأولوية", 50) or 50),
                        "هو_تستر":             is_tester_flag,
                        "تفاصيل_المنافسين":    _comp_details_raw,
                        "عدد_المنافسين":       int(row.get("عدد_المنافسين", len(_comp_details_raw)) or 1),
                        "نوع_متاح":            variant_label,
                        "منتج_متاح":           variant_product,
                        "نسبة_التشابه":        variant_score,
                        "منتج_مطابق_محتمل":    str(row.get("منتج_مطابق_محتمل", "") or ""),
                        "درجة_التشابه":        conf_score,
                    }), unsafe_allow_html=True)

                # ── إجراءات مختصرة على البطاقة ───────────────────────────
                a_quick, a_enrich, a_ign = st.columns(3)
                _miss_url_card = _miss_comp_url if _miss_comp_url else ""
                _send_price = max(int(round(price - 1)), 1) if price > 0 else 0

                with a_quick:
                    if st.button("⚡ إرسال سريع", key=f"qs_{idx}",
                                 use_container_width=True,
                                 help="إرسال فوري لـ Make (اسم + سعر + صورة) بدون إثراء AI"):
                        if _send_price <= 0 or not nm_ai.strip():
                            st.error("❌ بيانات ناقصة: تأكد من السعر والاسم")
                        else:
                            _payload = {
                                "name": nm_ai,
                                "price": _send_price,
                                "image_url": _miss_img or "",
                                "sku": _miss_pid,
                                "section": "missing",
                                "comp_name": name,
                                "competitor": comp,
                                "brand": brand,
                            }
                            with st.spinner("جاري الإرسال..."):
                                _r = send_missing_products([_payload])
                            if _r.get("sent", 0) > 0:
                                st.success(f"✅ تم إرسال «{nm_ai[:40]}» إلى Make")
                                _pk = f"miss_{name[:30]}_{comp}"
                                save_processed(_pk, nm_ai, comp, "send_missing_single",
                                               new_price=_send_price, comp_url=_miss_url_card)
                                if _miss_url_card:
                                    _track_processed_missing_url(_miss_url_card)
                                # مفتاح مستقر بالاسم + حفظ دائم: يبقى مخفياً عبر إعادة الحساب
                                # وإعادة التشغيل حتى لو بلا رابط منافس (لا يعود للقسم).
                                _mk_hide = f"missing_{name}"
                                st.session_state.hidden_products.add(_mk_hide)
                                save_hidden_product(_mk_hide, nm_ai, "sent_to_make")
                                st.rerun()
                            else:
                                st.error(f"❌ فشل الإرسال: {_r.get('message', 'خطأ غير معروف')}")

                with a_enrich:
                    if st.button("🤖 إثراء + إرسال", key=f"en_{idx}",
                                 use_container_width=True,
                                 help="يولّد الوصف والماركة بـ AI ثم يرسل (~10 ثواني)"):
                        if not ANY_AI_PROVIDER_CONFIGURED:
                            st.error(
                                "🔴 الذكاء الاصطناعي غير مُفعّل — لا يمكن توليد وصف مهووس.\n\n"
                                "أضف مفتاح **GEMINI_API_KEY** (أو OPENROUTER_API_KEY / COHERE_API_KEY) "
                                "في الإعدادات أو متغيرات البيئة، ثم أعد المحاولة. "
                                "أو استخدم زر «⚡ إرسال سريع» للإرسال بدون إثراء."
                            )
                        elif _send_price <= 0 or not nm_ai.strip():
                            st.error("❌ بيانات ناقصة: تأكد من السعر والاسم")
                        else:
                            with st.spinner("🤖 إثراء + إرسال..."):
                                try:
                                    _frag = fetch_fragrantica_info(nm_ai) or {}
                                    _html = generate_mahwous_description(
                                        product_name=nm_ai,
                                        price=price,
                                        fragrantica_data=_frag if _frag.get("success") else None,
                                    )
                                except Exception as _e_enrich:
                                    _html = ""
                                    st.warning(f"⚠️ تعذّر الإثراء، سيُرسل بدون وصف: {_e_enrich}")
                                _payload = {
                                    "name": nm_ai,
                                    "price": _send_price,
                                    "image_url": _miss_img or "",
                                    "sku": _miss_pid,
                                    "الوصف": _html or "",
                                    "section": "missing",
                                    "comp_name": name,
                                    "competitor": comp,
                                    "brand": brand,
                                }
                                _r = send_missing_products([_payload])
                            if _r.get("sent", 0) > 0:
                                st.success(f"✅ تم إثراء وإرسال «{nm_ai[:40]}»")
                                _pk = f"miss_{name[:30]}_{comp}"
                                save_processed(_pk, nm_ai, comp, "send_missing_enriched",
                                               new_price=_send_price, comp_url=_miss_url_card)
                                if _miss_url_card:
                                    _track_processed_missing_url(_miss_url_card)
                                # مفتاح مستقر بالاسم + حفظ دائم (لا يعود بعد الإرسال)
                                _mk_hide = f"missing_{name}"
                                st.session_state.hidden_products.add(_mk_hide)
                                save_hidden_product(_mk_hide, nm_ai, "sent_to_make")
                                st.rerun()
                            else:
                                st.error(f"❌ فشل الإرسال: {_r.get('message', 'خطأ غير معروف')}")

                with a_ign:
                    if st.button("🗑️ تجاهل", key=f"ign_{idx}", use_container_width=True):
                        log_decision(nm_ai,"missing","ignored","تجاهل",0,price,-price,comp)
                        _ign = f"missing_{name}"
                        st.session_state.hidden_products.add(_ign)
                        save_hidden_product(_ign, nm_ai, "ignored")
                        save_processed(_ign, nm_ai, comp, "ignored",
                                       new_price=price,
                                       notes="تجاهل من قسم المفقودة")
                        st.rerun()

                st.markdown('<hr style="border:none;border-top:1px solid #0d1a2e;margin:8px 0">', unsafe_allow_html=True)
        else:
            st.success("✅ لا توجد منتجات مفقودة!")
    else:
        st.info("ارفع الملفات أولاً")

# ════════════════════════════════════════════════
#  المستبعدة — منتجاتنا التي لم تُصنَّف في سلة سعرية (الشرط 9)
# ════════════════════════════════════════════════
elif page == "⚪ المستبعدة":
    st.header("⚪ المنتجات المستبعدة")
    st.caption("منتجاتنا التي لم تدخل أي سلة سعرية — مع سبب الاستبعاد لكل منتج")
    db_log("excluded", "view")
    _exc_df = None
    if st.session_state.results and isinstance(st.session_state.results, dict):
        _exc_df = st.session_state.results.get("excluded")
    if isinstance(_exc_df, pd.DataFrame) and not _exc_df.empty:
        _exc_view = _exc_df.copy()
        # عمود السبب: سبب_التصنيف إن وُجد، وإلا القرار (الذي يحوي سبب الاستبعاد)
        if "سبب_التصنيف" in _exc_view.columns and _exc_view["سبب_التصنيف"].astype(str).str.strip().replace("nan", "").any():
            _reason = _exc_view["سبب_التصنيف"].fillna("").astype(str).str.strip()
            _reason = _reason.where(_reason != "", _exc_view.get("القرار", "غير محدد"))
        else:
            _reason = _exc_view.get("القرار", pd.Series(["غير محدد"] * len(_exc_view))).fillna("غير محدد").astype(str).str.strip()
        _reason = _reason.replace("", "غير محدد")
        _exc_view["__reason__"] = _reason

        # عدّاد + توزيع الأسباب (أرقام حقيقية)
        render_kpi_row({"total": len(_exc_view), "raise": 0, "lower": 0,
                        "approved": 0, "missing": 0})
        _reason_counts = _reason.value_counts()
        _c1, _c2 = st.columns([1, 2])
        with _c1:
            _reason_opts = ["الكل"] + _reason_counts.index.tolist()
            _sel_reason = st.selectbox("🔍 فلتر بالسبب", _reason_opts, key="exc_reason_filter")
        with _c2:
            _dist = " · ".join(f"{r}: {c:,}" for r, c in _reason_counts.head(6).items())
            st.caption(f"📊 توزيع الأسباب: {_dist}")

        _filtered_exc = _exc_view if _sel_reason == "الكل" else _exc_view[_reason == _sel_reason]
        st.caption(f"عرض {len(_filtered_exc):,} من {len(_exc_view):,} منتج مستبعد")

        # ⚡ 25 بدل 50/صفحة: قسم المستبعدة كان يرسم 50 صفاً دفعة واحدة
        _es, _ee, _ep = render_pagination(len(_filtered_exc), 25, "exc")
        render_excluded_table(_filtered_exc.iloc[_es:_ee].to_dict("records"))

        # تصدير CSV للمستبعدة (مع السبب)
        _exc_csv = _filtered_exc[[c for c in ["المنتج", "الماركة", "السعر", "النوع", "الحجم", "__reason__"]
                                  if c in _filtered_exc.columns]].rename(
            columns={"__reason__": "سبب_الاستبعاد"}).to_csv(index=False, encoding="utf-8-sig")
        st.download_button("📥 تصدير المستبعدة (CSV)", data=_exc_csv,
                           file_name="mahwous_excluded.csv", mime="text/csv")
    elif st.session_state.results:
        st.success("✅ لا توجد منتجات مستبعدة — كل منتجاتنا دخلت سلة سعرية.")
    else:
        st.info("شغّل تحليلاً أولاً لعرض المنتجات المستبعدة.")

# ════════════════════════════════════════════════
#  تمت المعالجة — v26
# ════════════════════════════════════════════════
elif page in ("✔️ تمت المعالجة", "✅ تمت المعالجة"):
    st.header("✔️ المنتجات المعالجة")
    st.caption("جميع المنتجات التي تم ترحيلها أو تحديث سعرها أو إضافتها")
    db_log("processed", "view")

    _analysis_df = st.session_state.get("analysis_df", pd.DataFrame())
    _missing_df = (st.session_state.get("results") or {}).get("missing", pd.DataFrame())
    _proc_ids = {str(x) for x in st.session_state.get("processed_price_skus", set())}
    _proc_urls = {str(x) for x in st.session_state.get("processed_missing_urls", set())}

    _processed_price_df = pd.DataFrame()
    if isinstance(_analysis_df, pd.DataFrame) and not _analysis_df.empty and "معرف_المنتج" in _analysis_df.columns:
        _processed_price_df = _analysis_df[_analysis_df["معرف_المنتج"].astype(str).isin(_proc_ids)].copy()

    _processed_missing_df = pd.DataFrame()
    if isinstance(_missing_df, pd.DataFrame) and not _missing_df.empty and "رابط_المنافس" in _missing_df.columns:
        _processed_missing_df = _missing_df[_missing_df["رابط_المنافس"].astype(str).isin(_proc_urls)].copy()

    proc_t1, proc_t2, proc_t3 = st.tabs(["💰 أسعار تم تعديلها", "📦 مفقودات تمت إضافتها", "🤖 ملخص ذكي"])  # FIX: Smart Workflow & AI Tracking
    with proc_t1:
        if _processed_price_df.empty:
            st.info("لا توجد عناصر سعرية معالجة في هذه الجلسة.")
        else:
            st.dataframe(_processed_price_df, use_container_width=True, height=260)
            # FIX: Transparency & Reversibility
            _price_revert_ids = sorted({
                str(x) for x in _processed_price_df.get("معرف_المنتج", pd.Series(dtype=str)).dropna().astype(str).tolist()
                if str(x).strip() not in ("", "nan", "None", "NaN")
            })
            _sel_price_revert = st.multiselect(
                "اختر معرفات المنتجات لإلغاء المعالجة",
                _price_revert_ids,
                key="processed_price_revert_ids",
            )
            if st.button("↩️ إلغاء المعالجة للأسعار المحددة", key="processed_price_revert_btn", disabled=not _sel_price_revert):
                for _pid in _sel_price_revert:
                    st.session_state["processed_price_skus"].discard(str(_pid))
                    st.session_state.get("_processed_price_map", {}).pop(str(_pid), None)
                # Phase 1: إزالة من DB أيضاً — بحث بـ product_id في processed_products
                _db_revert_keys = [
                    p["product_key"] for p in get_processed(limit=50000)
                    if str(p.get("product_id", "")).strip() in {str(x) for x in _sel_price_revert}
                ]
                if _db_revert_keys:
                    bulk_revert_processed(_db_revert_keys)
                st.success(f"تمت إعادة {len(_sel_price_revert)} منتج إلى الأقسام الأصلية.")
                st.rerun()
    with proc_t2:
        if _processed_missing_df.empty:
            st.info("لا توجد منتجات مفقودة معالجة في هذه الجلسة.")
        else:
            st.dataframe(_processed_missing_df, use_container_width=True, height=260)
            # FIX: Transparency & Reversibility
            _miss_revert_urls = sorted({
                str(x) for x in _processed_missing_df.get("رابط_المنافس", pd.Series(dtype=str)).dropna().astype(str).tolist()
                if str(x).strip()
            })
            _sel_miss_revert = st.multiselect(
                "اختر روابط المفقودات لإلغاء المعالجة",
                _miss_revert_urls,
                key="processed_missing_revert_urls",
            )
            if st.button("↩️ إلغاء معالجة المفقودات المحددة", key="processed_missing_revert_btn", disabled=not _sel_miss_revert):
                for _u in _sel_miss_revert:
                    st.session_state["processed_missing_urls"].discard(str(_u))
                # Phase 1: إزالة من DB أيضاً — بحث بـ comp_url في processed_products
                _db_revert_keys = [
                    p["product_key"] for p in get_processed(limit=50000)
                    if str(p.get("comp_url", "")).strip() in {str(x) for x in _sel_miss_revert}
                ]
                if _db_revert_keys:
                    bulk_revert_processed(_db_revert_keys)
                st.success(f"تمت إعادة {len(_sel_miss_revert)} مفقود إلى قائمته الأصلية.")
                st.rerun()
    with proc_t3:
        if st.button("🤖 توليد تقرير ذكي للإجراءات (AI Summary)", key="processed_ai_summary_btn"):  # FIX: Smart Workflow & AI Tracking
            _price_lines = []
            if not _processed_price_df.empty:
                for _, _r in _processed_price_df.head(120).iterrows():
                    _price_lines.append(
                        f"- المنتج: {str(_r.get('المنتج',''))} | قديم: {safe_float(_r.get('السعر',0)):.2f} | جديد: {safe_float(_r.get('سعر_المنافس',0)):.2f}"
                    )
            _missing_lines = []
            if not _processed_missing_df.empty:
                for _, _r in _processed_missing_df.head(120).iterrows():
                    _missing_lines.append(
                        f"- منتج مفقود مضاف: {str(_r.get('منتج_المنافس',''))} | سعر مرجعي: {safe_float(_r.get('سعر_المنافس',0)):.2f}"
                    )
            _actions_text = (
                "## Price Actions\n"
                + ("\n".join(_price_lines) if _price_lines else "- لا توجد تعديلات أسعار مسجلة في هذه الجلسة")
                + "\n\n## Missing Products Added\n"
                + ("\n".join(_missing_lines) if _missing_lines else "- لا توجد منتجات مفقودة مضافة في هذه الجلسة")
            )
            _ai_sum = generate_action_summary(_actions_text)
            if _ai_sum.get("success"):
                st.success(_ai_sum.get("response", ""))
            else:
                st.info(_ai_sum.get("response", "تعذر توليد الملخص حالياً."))

    processed = get_processed(limit=500)
    if not processed:
        st.info("📭 لا توجد منتجات معالجة بعد")
    else:
        df_proc = pd.DataFrame(processed)

        # إحصاء
        actions = df_proc["action"].value_counts()
        cols_p = st.columns(len(actions) + 1)
        for i, (act, cnt) in enumerate(actions.items()):
            icon = {"send_price":"💰","send_missing":"📦","approved":"✅","removed":"🗑️"}.get(act,"📌")
            cols_p[i].metric(f"{icon} {act}", cnt)
        cols_p[-1].metric("📦 الإجمالي", len(df_proc))

        # فلتر
        act_filter = st.selectbox("نوع الإجراء", ["الكل"] + list(actions.index))
        show_df = df_proc if act_filter == "الكل" else df_proc[df_proc["action"] == act_filter]

        st.markdown("---")

        for _, row in show_df.iterrows():
            p_key  = str(row.get("product_key",""))
            p_name = str(row.get("product_name",""))
            p_act  = str(row.get("action",""))
            p_ts   = str(row.get("timestamp",""))
            p_price_old = safe_float(row.get("old_price",0))
            p_price_new = safe_float(row.get("new_price",0))
            p_notes = str(row.get("notes",""))
            p_comp  = str(row.get("competitor",""))

            icon_map = {"send_price":"💰","send_missing":"📦","approved":"✅","removed":"🗑️"}
            icon = icon_map.get(p_act, "📌")

            col_a, col_b = st.columns([5, 1])
            with col_a:
                price_info = ""
                if p_price_old > 0 and p_price_new > 0:
                    price_info = f" | {p_price_old:.0f} → {p_price_new:.0f} ر.س"
                elif p_price_new > 0:
                    price_info = f" | {p_price_new:.0f} ر.س"
                _notes_html = ("<br><span style='color:#aaa;font-size:.73rem'>" + p_notes[:80] + "</span>") if p_notes else ""
                _arow = _find_analysis_row_for_processed(p_name)
                _p_our_u, _p_comp_u = _lookup_product_urls_from_analysis_session(p_name)
                _url_chips_html = _processed_row_url_chips_html(_p_our_u, _p_comp_u)
                _po, _pc = (
                    row_media_urls_from_analysis(_arow)
                    if _arow is not None
                    else ("", "")
                )
                # إن وُجد رابط صفحة بلا صورة في الجدول — جرّب og:image / أيقونة الموقع
                if (not _po) and (_p_our_u or "").strip().lower().startswith("http"):
                    _po = _cached_thumb_from_product_url(_p_our_u) or ""
                if (not _pc) and (_p_comp_u or "").strip().lower().startswith("http"):
                    _pc = _cached_thumb_from_product_url(_p_comp_u) or ""
                _comp_disp = (
                    str(_arow.get("منتج_المنافس", "") or "").strip()
                    if _arow is not None
                    else ""
                )
                if not _comp_disp:
                    _comp_disp = p_comp or "منافس"
                _thumb_cell = _processed_dual_image_html(_po, _pc, p_name[:100], _comp_disp[:100])
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;padding:6px 10px;border-radius:6px;background:#0a1628;'
                    f'border:1px solid #1a2a44;font-size:.85rem">'
                    f'{_thumb_cell}'
                    f'<div style="flex:1;min-width:0">'
                    f'<span style="color:#888;font-size:.75rem">{p_ts[:16]}</span> &nbsp;'
                    f'{icon} <b style="color:#4fc3f7">{p_name[:60]}</b>'
                    f'<span style="color:#888"> — {p_act}{price_info}</span>'
                    f'{_notes_html}{_url_chips_html}</div></div>',
                    unsafe_allow_html=True
                )
            with col_b:
                if st.button("↩️ تراجع", key=f"undo_{p_key}"):
                    undo_processed(p_key)
                    # Phase 1: مزامنة كاملة — إزالة من كل مصادر التتبع
                    st.session_state.hidden_products.discard(p_key)
                    _undo_pid = str(row.get("product_id", "") or "").strip()
                    _undo_url = str(row.get("comp_url", "") or "").strip()
                    if _undo_pid:
                        st.session_state["processed_price_skus"].discard(_undo_pid)
                        st.session_state.get("_processed_price_map", {}).pop(_undo_pid, None)
                    if _undo_url:
                        st.session_state["processed_missing_urls"].discard(_undo_url)
                    st.success(f"✅ تم التراجع: {p_name[:40]}")
                    st.rerun()

        # تصدير
        st.markdown("---")
        csv_proc = df_proc.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("📥 تصدير CSV", data=csv_proc,
                           file_name="processed_products.csv", mime="text/csv",
                           )





# ════════════════════════════════════════════════
#  11. كشط المنافسين (Async Scraper Dashboard)
# ════════════════════════════════════════════════
# ════════════════════════════════════════════════
#  11. كشط المنافسين (Unified Dashboard v26.1 — FIXED)
#
#  التغييرات الجذرية عن النسخة السابقة:
#  ✅ Single Source of Truth عبر _get_true_scraper_status()
#  ✅ تحقق PID فعلي من OS (os.kill(pid,0)) وليس JSON فقط
#  ✅ تنظيف الحالة العالقة تلقائياً (stale state cleanup)
#  ✅ كشف التجميد إذا لم يتحدث last_updated منذ 5+ دقائق
#  ✅ منع التشغيل المتداخل على مستوى PID
#  ✅ واجهة موحدة (expanders بدل tabs) — بدون ازدواجية
#  ✅ زر إيقاف مع SIGTERM + تنظيف
#  ✅ Phase labels واضحة: discovering/scraping/retrying/stale/completed/failed/stopped
#  ✅ لا time.sleep()، لا infinite reruns
# ════════════════════════════════════════════════
elif page == "🕷️ كشط المنافسين":
    import subprocess
    import sys as _sys_sc
    import os as _os_scraper
    import json as _json_sc
    import tempfile

    try:
        import fcntl as _fcntl_sc
    except ImportError:
        _fcntl_sc = None

    st.header("🕷️ كشط بيانات المنافسين")
    db_log("scraper", "view")

    # ════════════════════════════════════════════════════════════════════════
    #  ⚡ كشط سريع عبر محلي — Mahally.com (Algolia API)
    # ════════════════════════════════════════════════════════════════════════
    with st.expander("⚡ كشط سريع عبر محلي (الأسرع والأدق)", expanded=True):
        st.caption(
            "يستخدم منصة **mahally.com** لاستخراج بيانات المنافسين مباشرة — "
            "**بدون حظر Cloudflare** — بيانات غنية ومنظمة (اسم، سعر، ماركة، تصنيف، صورة) "
            "في ثوانٍ معدودة."
        )

        # ── تحميل المحرك ──
        _mahally_ok = False
        try:
            from engines.mahally_scraper import MahallyScraper as _MS
            _mahally_ok = True
        except ImportError as _me:
            st.error(f"❌ تعذّر تحميل محرك محلي: {_me}")

        if _mahally_ok:
            # ── تحميل المتاجر المُعرَّفة ──
            import json as _json_mh
            _mh_comp_file = _os_scraper.path.join(
                _os_scraper.environ.get("DATA_DIR", "data"), "competitors_list_v30.json"
            )
            _mh_stores = {}
            try:
                with open(_mh_comp_file, "r", encoding="utf-8") as _f:
                    _mh_raw = _json_mh.load(_f)
                for _entry in _mh_raw:
                    _mid = _entry.get("mahally_store_id")
                    if _mid:
                        _mh_stores[_entry.get("name", f"store_{_mid}")] = int(_mid)
            except Exception:
                pass

            # ── إحصاءات سريعة ──
            if _mh_stores:
                _c1, _c2, _c3 = st.columns(3)
                _c1.metric("🏪 متاجر مُعرَّفة", len(_mh_stores))
                _c2.metric("⚡ السرعة", "~1000 منتج / 24 ثانية")
                _c3.metric("🛡️ بدون حظر", "✅ Cloudflare bypass")

            # ── اختيار المتاجر ──
            _mh_all_names = list(_mh_stores.keys()) if _mh_stores else []
            _mh_selected = st.multiselect(
                "اختر المتاجر للكشط",
                options=_mh_all_names,
                default=_mh_all_names,
                key="mahally_store_select",
            )

            # ── إضافة متجر جديد ──
            with st.popover("➕ إضافة متجر جديد"):
                st.caption("أدخل رابط المتجر من mahally.com مثل:")
                st.code("https://mahally.com/stores/216339537/")
                _new_mh_url = st.text_input("رابط محلي", key="new_mahally_url", placeholder="https://mahally.com/stores/...")
                _new_mh_name = st.text_input("اسم المتجر", key="new_mahally_name", placeholder="اسم المنافس")
                if st.button("✅ إضافة", key="add_mahally_store"):
                    import re as _re_mh
                    _id_match = _re_mh.search(r'/stores/(\d+)', _new_mh_url or "")
                    if _id_match and _new_mh_name:
                        _new_id = int(_id_match.group(1))
                        # اختبار سريع
                        try:
                            _test_scraper = _MS()
                            _test_info = _test_scraper.get_store_info(_new_id)
                            if _test_info.get("total_products", 0) > 0:
                                # حفظ في JSON
                                try:
                                    with open(_mh_comp_file, "r", encoding="utf-8") as _f:
                                        _comp_data = _json_mh.load(_f)
                                except Exception:
                                    _comp_data = []
                                # تحقق من عدم التكرار
                                _exists = any(e.get("mahally_store_id") == _new_id for e in _comp_data)
                                if not _exists:
                                    _comp_data.append({
                                        "name": _new_mh_name,
                                        "store_url": _new_mh_url,
                                        "sitemap_url": "",
                                        "mahally_store_id": _new_id,
                                    })
                                    with open(_mh_comp_file, "w", encoding="utf-8") as _f:
                                        _json_mh.dump(_comp_data, _f, ensure_ascii=False, indent=2)
                                st.success(
                                    f"✅ تم إضافة **{_test_info.get('name', _new_mh_name)}** "
                                    f"({_test_info.get('total_products', 0):,} منتج)"
                                )
                                st.rerun()
                            else:
                                st.error("❌ لم يتم العثور على منتجات — تأكد من الرابط")
                        except Exception as _te:
                            st.error(f"❌ خطأ: {_te}")
                    else:
                        st.warning("⚠️ أدخل رابط صحيح واسم المتجر")

            # ── زر الكشط ──
            st.markdown("---")
            _col_btn1, _col_btn2 = st.columns(2)
            _mh_scrape_btn = _col_btn1.button(
                "🚀 بدء الكشط السريع",
                type="primary",
                use_container_width=True,
                disabled=not _mh_selected,
                key="mahally_scrape_btn",
            )
            _mh_info_btn = _col_btn2.button(
                "ℹ️ معلومات المتاجر",
                use_container_width=True,
                disabled=not _mh_selected,
                key="mahally_info_btn",
            )

            # ── معلومات المتاجر ──
            if _mh_info_btn:
                _info_scraper = _MS()
                _info_data = []
                for _sn in _mh_selected:
                    _sid = _mh_stores.get(_sn)
                    if _sid:
                        _inf = _info_scraper.get_store_info(_sid)
                        _info_data.append({
                            "المتجر": _inf.get("name", _sn),
                            "Store ID": _sid,
                            "المنتجات": f"{_inf.get('total_products', 0):,}",
                            "الصفحات": _inf.get("pages", 0),
                        })
                if _info_data:
                    st.dataframe(pd.DataFrame(_info_data), use_container_width=True, hide_index=True)

            # ── تنفيذ الكشط ──
            if _mh_scrape_btn and _mh_selected:
                _selected_ids = {n: _mh_stores[n] for n in _mh_selected if n in _mh_stores}
                _scraper = _MS(
                    db_path=_os_scraper.path.join(
                        _os_scraper.environ.get("DATA_DIR", "data"), "pricing_v18.db"
                    )
                )

                _progress_bar = st.progress(0, text="جاري التحضير...")
                _status_text = st.empty()
                _results_container = st.container()

                _all_results = {}
                _total_stores = len(_selected_ids)
                _total_products = 0

                for _i, (_sname, _sid) in enumerate(_selected_ids.items(), 1):
                    _progress_bar.progress(
                        (_i - 1) / _total_stores,
                        text=f"⏳ كشط {_sname} ({_i}/{_total_stores})..."
                    )
                    _status_text.info(f"🔄 جاري كشط **{_sname}** (Store ID: {_sid})...")

                    try:
                        _prods = _scraper.scrape_store(_sid, _sname)

                        # إعادة محاولة إذا فشل (0 منتجات مع وجود منتجات فعلية)
                        if not _prods:
                            import time as _time_mh
                            _status_text.warning(f"⚠️ {_sname}: 0 منتج — إعادة المحاولة بعد 10 ثوانٍ...")
                            _time_mh.sleep(10)
                            _prods = _scraper.scrape_store(_sid, _sname)

                        _all_results[_sname] = _prods
                        _total_products += len(_prods)

                        # حفظ في DB
                        if _prods:
                            _scraper.save_to_db(_prods, _sname)

                        _status_text.success(
                            f"✅ {_sname}: {len(_prods):,} منتج"
                        )
                    except Exception as _se:
                        _status_text.error(f"❌ {_sname}: {_se}")
                        _all_results[_sname] = []

                    # تأخير 5 ثوانٍ بين المتاجر لتجنب حظر mahally.com
                    if _i < _total_stores:
                        import time as _time_mh2
                        _status_text.info(f"⏳ انتظار 5 ثوانٍ قبل المتجر التالي...")
                        _time_mh2.sleep(5)

                _progress_bar.progress(1.0, text="✅ اكتمل الكشط!")

                # ── عرض النتائج ──
                with _results_container:
                    st.markdown("### 📊 نتائج الكشط")
                    _res_cols = st.columns(3)
                    _res_cols[0].metric("📦 إجمالي المنتجات", f"{_total_products:,}")
                    _res_cols[1].metric("🏪 المتاجر", f"{len(_all_results)}")
                    _res_cols[2].metric("⚡ الحالة", "✅ مكتمل")

                    # جدول ملخص
                    _summary = []
                    for _sn, _prods in _all_results.items():
                        _prices = [p["price"] for p in _prods if p.get("price", 0) > 0]
                        _summary.append({
                            "المتجر": _sn,
                            "المنتجات": len(_prods),
                            "أقل سعر": f"{min(_prices):,.0f}" if _prices else "—",
                            "أعلى سعر": f"{max(_prices):,.0f}" if _prices else "—",
                            "متوسط السعر": f"{sum(_prices)/len(_prices):,.0f}" if _prices else "—",
                        })
                    st.dataframe(pd.DataFrame(_summary), use_container_width=True, hide_index=True)

                    # تصدير
                    st.markdown("### 📥 تصدير النتائج")
                    _exp_dir = _os_scraper.path.join(
                        _os_scraper.path.dirname(_os_scraper.path.abspath(__file__)), "exports"
                    )

                    _exp_c1, _exp_c2, _exp_c3 = st.columns(3)

                    # CSV
                    try:
                        _csv_path = _scraper.export_csv(_all_results, _exp_dir)
                        if _csv_path and _os_scraper.path.exists(_csv_path):
                            with open(_csv_path, "rb") as _cf:
                                _exp_c1.download_button(
                                    "📄 تحميل CSV",
                                    data=_cf.read(),
                                    file_name="mahally_products.csv",
                                    mime="text/csv",
                                    key="dl_mahally_csv",
                                )
                    except Exception:
                        pass

                    # Excel
                    try:
                        _xlsx_path = _scraper.export_excel(_all_results, _exp_dir)
                        if _xlsx_path and _os_scraper.path.exists(_xlsx_path):
                            with open(_xlsx_path, "rb") as _xf:
                                _exp_c2.download_button(
                                    "📊 تحميل Excel",
                                    data=_xf.read(),
                                    file_name="mahally_products.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    key="dl_mahally_xlsx",
                                )
                    except Exception:
                        pass

                    # عرض عينة
                    with st.expander("👀 عينة من المنتجات"):
                        for _sn, _prods in _all_results.items():
                            if _prods:
                                st.markdown(f"**{_sn}** ({len(_prods):,} منتج)")
                                _sample_df = pd.DataFrame(_prods[:20])[
                                    ["name", "price", "original_price", "brand", "category"]
                                ]
                                _sample_df.columns = ["المنتج", "السعر", "السعر الأصلي", "الماركة", "التصنيف"]
                                st.dataframe(_sample_df, use_container_width=True, hide_index=True)

        st.markdown("---")

    # ════════════════════════════════════════════════════════════════════════
    #  🚀 التحديث الذكي عبر Sitemap (تزايدي — يكشط فقط ما تغيّر)
    # ════════════════════════════════════════════════════════════════════════
    with st.expander("🚀 تحديث ذكي عبر Sitemap (موصى به)", expanded=True):
        st.caption(
            "يجلب أحدث Sitemap من كل متجر منافس، ويكشط فقط المنتجات الجديدة أو التي تغيّر تاريخ تعديلها (lastmod) "
            "منذ آخر تشغيل — أسرع 5×–10× من الكشط الكامل، وأقل ضغطاً، وأقل تعرضاً للحظر."
        )
        from utils import sitemap_cache as _smc
        _stat_rows = _smc.status_all()
        _DATA_SM = _os_scraper.environ.get("DATA_DIR", "data")
        _sm_prog_path = _os_scraper.path.join(_DATA_SM, "sitemap_auto_progress.json")
        _sm_pid_path  = _os_scraper.path.join(_DATA_SM, "sitemap_auto.pid")

        # حالة الكاش
        if _stat_rows:
            import datetime as _dt_smc
            _total_urls = sum(r["urls_count"] for r in _stat_rows)
            _last_ts = max((r["fetched_at"] for r in _stat_rows), default=0)
            _last_str = _dt_smc.datetime.fromtimestamp(_last_ts).strftime("%Y-%m-%d %H:%M") if _last_ts else "—"
            cA, cB, cC = st.columns(3)
            cA.metric("🗂️ متاجر مكشوطة سابقاً", f"{len(_stat_rows)}")
            cB.metric("🔗 روابط منتجات محفوظة", f"{_total_urls:,}")
            cC.metric("🕒 آخر تحديث", _last_str)
        else:
            st.info("لم يتم تشغيل التحديث الذكي بعد — سيتم كشط جميع المنتجات في المرة الأولى.")

        # حالة العملية الجارية
        _sm_prog = {}
        if _os_scraper.path.exists(_sm_prog_path):
            try:
                with open(_sm_prog_path, "r", encoding="utf-8") as _f:
                    _sm_prog = _json_sc.load(_f)
            except Exception:
                _sm_prog = {}
        _sm_running = bool(_sm_prog.get("running", False))

        # تحقق من الـPID
        _sm_pid = 0
        if _os_scraper.path.exists(_sm_pid_path):
            try:
                with open(_sm_pid_path, "r", encoding="utf-8") as _f:
                    _sm_pid = int((_f.read() or "0").strip() or 0)
            except Exception:
                _sm_pid = 0
        if _sm_pid and _sm_running:
            try:
                _os_scraper.kill(_sm_pid, 0)
                _alive = True
            except Exception:
                _alive = False
            if not _alive:
                _sm_running = False
                _sm_prog["running"] = False

        col1, col2 = st.columns(2)
        with col1:
            _btn_inc = st.button(
                "🔄 تحديث ذكي (تزايدي)",
                type="primary",
                use_container_width=True,
                disabled=_sm_running,
                key="sm_btn_inc",
            )
        with col2:
            _btn_full = st.button(
                "🔁 كشط كامل (تجاهل الكاش)",
                use_container_width=True,
                disabled=_sm_running,
                key="sm_btn_full",
            )

        if _btn_inc or _btn_full:
            try:
                _cmd = [_sys_sc.executable, "sitemap_automation.py"]
                if _btn_full:
                    _cmd.append("--full")
                _os_scraper.makedirs(_DATA_SM, exist_ok=True)
                _log_path = _os_scraper.path.join(_DATA_SM, "sitemap_auto.log")
                with open(_log_path, "ab") as _lf:
                    _proc = subprocess.Popen(
                        _cmd, stdout=_lf, stderr=subprocess.STDOUT,
                        cwd=_os_scraper.getcwd(),
                    )
                with open(_sm_pid_path, "w", encoding="utf-8") as _pf:
                    _pf.write(str(_proc.pid))
                st.success(f"✅ بدأ التشغيل (PID={_proc.pid}). تابع التقدم أدناه.")
                import time as _t_sc
                _t_sc.sleep(1)
                st.rerun()
            except Exception as _e:
                st.error(f"❌ فشل التشغيل: {_e}")

        # شريط التقدم الحي — تحديث ذاتي عبر st.fragment بدل حلقة sleep+rerun
        @st.fragment(run_every=5)
        def _poll_progress():
            _p = {}
            if _os_scraper.path.exists(_sm_prog_path):
                try:
                    with open(_sm_prog_path, "r", encoding="utf-8") as _f:
                        _p = _json_sc.load(_f)
                except Exception:
                    _p = {}
            if not _p:
                return
            _phase = str(_p.get("phase", ""))
            if _p.get("running", False):
                st.markdown("### 📊 حالة التشغيل الحالية")
                _ts = _p.get("total_stores", 0) or 1
                _si = _p.get("store_index", 0)
                st.progress(min(_si / _ts, 1.0), text=f"المتجر {_si}/{_ts}: {_p.get('current_store', '...')}")
                _pd = _p.get("products_done", 0)
                _pt = _p.get("products_total", 0) or 1
                st.progress(min(_pd / _pt, 1.0), text=f"منتجات هذا المتجر: {_pd}/{_pt} (نجح: {_p.get('successful', 0)})")
                st.caption(f"البدء: {_p.get('started_at', '')} • وضع: {'تزايدي' if _p.get('incremental') else 'كامل'}")
            elif _phase == "completed":
                st.success(
                    f"✅ اكتمل بنجاح — {_p.get('products_done', 0):,} منتج عبر "
                    f"{_p.get('total_stores', 0)} متجر • انتهى: {_p.get('finished_at', '')}"
                )
                _tps = _p.get("totals_per_store") or {}
                if _tps:
                    st.dataframe(
                        [{"المتجر": k, "منتجات محدّثة": v} for k, v in _tps.items()],
                        use_container_width=True, hide_index=True,
                    )
            elif _phase == "error":
                st.error(f"❌ {_p.get('message', 'فشل التشغيل')}")
        _poll_progress()

        st.markdown("---")
        st.caption("⬇️ أو استخدم الكاشط القديم الكامل (Playwright/v30):")

    # ─── ثوابت المسارات ──────────────────────────────────────────────────────
    _SCRAPER_SCRIPT   = _os_scraper.path.join("scrapers", "async_scraper.py")
    _DATA_SC          = _os_scraper.environ.get("DATA_DIR", "data")
    _PROGRESS_FILE    = _os_scraper.path.join(_DATA_SC, "scraper_progress.json")
    _OUTPUT_CSV       = _os_scraper.path.join(_DATA_SC, "competitors_latest.csv")
    _COMPETITORS_FILE = _os_scraper.path.join(_DATA_SC, "competitors_list.json")
    _PID_FILE         = _os_scraper.path.join(_DATA_SC, "scraper.pid")
    _LOG_FILE         = _os_scraper.path.join(_DATA_SC, "scraper_stderr.log")

    # ════════════════════════════════════════════════════════════════════════
    #  دوال البنية التحتية (Infrastructure Layer)
    # ════════════════════════════════════════════════════════════════════════

    def _is_process_alive(pid: int) -> bool:
        """
        يتحقق على مستوى kernel من أن العملية بهذا PID موجودة فعلاً.
        os.kill(pid, 0) لا يرسل إشارة — فقط يتحقق من وجود العملية.
        """
        if not pid or pid <= 0:
            return False
        try:
            _os_scraper.kill(pid, 0)
            return True
        except ProcessLookupError:
            # العملية غير موجودة
            return False
        except PermissionError:
            # موجودة لكن لا صلاحية لإشارتها (= حية بالفعل)
            return True
        except Exception:
            return False

    def _read_pid_file() -> int:
        """يقرأ PID من الملف — يعيد 0 عند أي خطأ."""
        try:
            if not _os_scraper.path.exists(_PID_FILE):
                return 0
            with open(_PID_FILE, "r", encoding="utf-8") as pf:
                raw = (pf.read() or "").strip()
                return int(raw) if raw.isdigit() else 0
        except (ValueError, OSError):
            return 0

    def _load_progress_raw() -> dict:
        """
        يقرأ ملف التقدم كما هو — دون أي تحقق من العملية.
        يستخدم shared lock على Linux لتجنب Partial Read.
        """
        _EMPTY = {"running": False}
        if not _os_scraper.path.exists(_PROGRESS_FILE):
            return _EMPTY
        try:
            with open(_PROGRESS_FILE, "r", encoding="utf-8") as fh:
                if _fcntl_sc is not None:
                    try:
                        _fcntl_sc.flock(fh, _fcntl_sc.LOCK_SH | _fcntl_sc.LOCK_NB)
                    except OSError:
                        pass
                raw = fh.read()
                if not raw or not raw.strip():
                    return _EMPTY
                data = _json_sc.loads(raw)
                return data if isinstance(data, dict) else _EMPTY
        except (_json_sc.JSONDecodeError, OSError):
            return _EMPTY
        except Exception:
            return _EMPTY

    def _write_progress_safe(data: dict) -> None:
        """كتابة آمنة لملف التقدم عبر ملف مؤقت ثم استبدال ذري."""
        _os_scraper.makedirs(_DATA_SC, exist_ok=True)
        content = _json_sc.dumps(data, ensure_ascii=False, indent=2)
        dir_path = _os_scraper.path.dirname(_os_scraper.path.abspath(_PROGRESS_FILE))
        try:
            fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp", prefix="prog_")
            try:
                with _os_scraper.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(content)
                    fh.flush()
                    _os_scraper.fsync(fh.fileno())
                _os_scraper.replace(tmp_path, _PROGRESS_FILE)
            except Exception:
                try:
                    _os_scraper.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception:
            # fallback مباشر بدون ملف مؤقت
            with open(_PROGRESS_FILE, "w", encoding="utf-8") as fh:
                fh.write(content)

    def _cleanup_stale_state() -> None:
        """
        ينظف الحالة العالقة:
        - يكتب running=False + phase=stopped في JSON
        - يحذف PID file
        يُستدعى تلقائياً عند اكتشاف: JSON يقول running=True لكن العملية ميتة.
        """
        try:
            prog = _load_progress_raw()
            prog["running"] = False
            prog["phase"] = "stopped"
            if not prog.get("finished_at"):
                prog["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            _write_progress_safe(prog)
        except Exception:
            pass
        try:
            if _os_scraper.path.exists(_PID_FILE):
                _os_scraper.remove(_PID_FILE)
        except OSError:
            pass

    def _get_true_scraper_status() -> dict:
        """
        ═══════════════════════════════════════════════════
        SINGLE SOURCE OF TRUTH لحالة الكاشط
        ═══════════════════════════════════════════════════
        يقرأ JSON + يتحقق من PID فعلياً على مستوى OS.
        إذا اكتشف حالة عالقة → ينظفها فوراً.

        يُعيد dict يحتوي على:
          is_alive  : bool — الكاشط حي فعلاً (PID موجود + JSON يقول running)
          phase     : str  — discovering/scraping/retrying/stale/completed/failed/stopped
          data      : dict — بيانات التقدم الكاملة من JSON
          pid       : int  — PID العملية الحالية (0 إذا لا يوجد)
          was_stale : bool — هل كانت حالة عالقة تم تنظيفها
        """
        prog = _load_progress_raw()
        json_says_running = bool(prog.get("running", False))
        pid = _read_pid_file()
        process_alive = _is_process_alive(pid) if pid > 0 else False
        was_stale = False

        # ── تحقق الحالة العالقة ──────────────────────────────────────────
        if json_says_running and not process_alive:
            # JSON يقول running لكن العملية ميتة → حالة عالقة
            _cleanup_stale_state()
            prog["running"] = False
            prog["phase"] = "stopped"
            was_stale = True
            is_alive = False
        else:
            is_alive = json_says_running and process_alive

        # ── استنتاج الـ phase ─────────────────────────────────────────────
        phase = str(prog.get("phase", "")).strip()
        if not phase:
            if is_alive:
                phase = "scraping"
            elif prog.get("finished_at"):
                phase = "completed"
            else:
                phase = "stopped"

        # ── كشف التجميد: last_updated ثابت منذ +5 دقائق رغم is_alive ─────
        if is_alive and not was_stale:
            last_upd_str = str(prog.get("last_updated", "")).strip()
            if last_upd_str:
                try:
                    last_upd = datetime.strptime(last_upd_str[:19], "%Y-%m-%d %H:%M:%S")
                    age_sec = (datetime.now() - last_upd).total_seconds()
                    if age_sec > 300:   # 5 دقائق بدون تحديث = مشبوه
                        phase = "stale"
                except Exception:
                    pass

        return {
            "is_alive":  is_alive,
            "phase":     phase,
            "data":      prog,
            "pid":       pid,
            "was_stale": was_stale,
        }

    def _load_stores() -> list:
        try:
            with open(_COMPETITORS_FILE, encoding="utf-8") as _cf:
                raw = _json_sc.loads(_cf.read())
            if not isinstance(raw, list):
                return []
            # Normalize: entries may be plain URL strings or dicts with
            # keys like "domain", "sitemap_url", "url", "name".
            result = []
            for item in raw:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    # Prefer explicit URL fields; fall back to domain
                    url = (
                        item.get("url")
                        or item.get("sitemap_url")
                        or item.get("link")
                    )
                    if url and isinstance(url, str):
                        result.append(url.strip())
                    elif item.get("domain"):
                        result.append("https://" + str(item["domain"]).strip())
                    # Skip entries that have no usable URL/domain
            return result
        except Exception:
            return []

    def _save_stores(lst: list) -> None:
        """حفظ آمن لقائمة المتاجر عبر ملف مؤقت ثم استبدال ذري."""
        _os_scraper.makedirs(_DATA_SC, exist_ok=True)
        content = _json_sc.dumps(lst, ensure_ascii=False, indent=2)
        dir_path = _os_scraper.path.dirname(_os_scraper.path.abspath(_COMPETITORS_FILE))
        try:
            fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp", prefix="stores_")
            try:
                with _os_scraper.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(content)
                    fh.flush()
                    _os_scraper.fsync(fh.fileno())
                _os_scraper.replace(tmp_path, _COMPETITORS_FILE)
            except Exception:
                try:
                    _os_scraper.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception:
            with open(_COMPETITORS_FILE, "w", encoding="utf-8") as fh:
                fh.write(content)

    def _load_scraper_state_map() -> dict:
        _state_file = _os_scraper.path.join(_DATA_SC, "scraper_state.json")
        try:
            if not _os_scraper.path.exists(_state_file):
                return {}
            with open(_state_file, "r", encoding="utf-8") as sf:
                data = _json_sc.loads(sf.read() or "{}")
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    @st.cache_data(ttl=5, show_spinner=False)
    def _load_csv_rows_by_store(_csv_path: str) -> dict:
        try:
            if not _os_scraper.path.exists(_csv_path):
                return {}
            _df_store = pd.read_csv(_csv_path, usecols=["store"], encoding="utf-8-sig", low_memory=False)
            if "store" not in _df_store.columns:
                return {}
            _counts = _df_store["store"].astype(str).value_counts(dropna=False)
            return {str(k): int(v) for k, v in _counts.to_dict().items()}
        except Exception:
            return {}

    def _read_live_store_progress(domain: str) -> dict:
        _live_file = _os_scraper.path.join(_DATA_SC, f"_sc_live_{domain}.json")
        try:
            if not _os_scraper.path.exists(_live_file):
                return {}
            with open(_live_file, "r", encoding="utf-8") as lf:
                data = _json_sc.loads(lf.read() or "{}")
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    # ════════════════════════════════════════════════════════════════════════
    #  الحصول على الحالة الحقيقية — مرة واحدة فقط لكل render cycle
    # ════════════════════════════════════════════════════════════════════════
    _status   = _get_true_scraper_status()
    _is_alive = _status["is_alive"]
    _phase    = _status["phase"]
    _prog     = _status["data"]
    _pid      = _status["pid"]

    # تنبيه بالحالة العالقة إذا اكتُشفت ونُظِّفت
    if _status["was_stale"]:
        st.warning(
            "⚠️ **تم اكتشاف حالة عالقة** — الكاشط انتهى بشكل غير طبيعي لكن الحالة لم تُحدَّث. "
            "تم التنظيف التلقائي. يمكنك الآن إعادة التشغيل."
        )

    # ════════════════════════════════════════════════════════════════════════
    #  Callbacks (جميعها تعمل على on_click لتجنب rerun issues)
    # ════════════════════════════════════════════════════════════════════════

    def _cb_add_store():
        """إضافة متجر مع تطبيع الرابط والتحقق من صحته."""
        url = (st.session_state.get("sc_new_url") or "").strip()
        if not url:
            return
        if not url.startswith("http"):
            url = "https://" + url
        # تحقق بسيط: الرابط يجب أن يحتوي نقطة
        _host = url.replace("https://", "").replace("http://", "").split("/")[0]
        if "." not in _host or len(_host) < 4:
            st.session_state["_sc_msg"] = ("error", "❌ رابط غير صحيح — مثال: https://store.com")
            return
        lst = _load_stores()
        if url not in lst:
            lst.append(url)
            _save_stores(lst)
            st.session_state["_sc_msg"] = ("success", f"✅ تمت الإضافة: {url}")
        else:
            st.session_state["_sc_msg"] = ("warning", "⚠️ الرابط موجود مسبقاً")
        st.session_state["sc_new_url"] = ""

    def _cb_remove_store(idx_to_remove: int):
        lst = _load_stores()
        if 0 <= idx_to_remove < len(lst):
            removed = lst.pop(idx_to_remove)
            _save_stores(lst)
            st.session_state["_sc_msg"] = ("success", f"🗑️ تم حذف: {removed}")

    def _cb_stop_scraper():
        """
        إيقاف الكاشط الجاري بأمان:
        1. SIGTERM للعملية
        2. تنظيف الحالة
        """
        _cur_pid = _read_pid_file()
        if _cur_pid and _is_process_alive(_cur_pid):
            try:
                import platform as _plat_mod
                if _plat_mod.system() == "Windows":
                    import subprocess as _sp_mod
                    _sp_mod.run(["taskkill", "/PID", str(_cur_pid), "/T", "/F"],
                                capture_output=True)
                else:
                    import signal as _sig_mod
                    _os_scraper.kill(_cur_pid, _sig_mod.SIGTERM)
                st.session_state["_sc_msg"] = (
                    "warning",
                    f"⏹️ تم إرسال إشارة إيقاف للكاشط (PID: {_cur_pid})"
                )
            except (ProcessLookupError, ValueError, OSError, PermissionError):
                st.session_state["_sc_msg"] = ("info", "العملية انتهت بالفعل")
            except Exception as e:
                st.session_state["_sc_msg"] = ("error", f"❌ فشل الإيقاف: {e}")
        _cleanup_stale_state()

    def _start_scraper_bg():
        """
        تشغيل الكاشط في الخلفية بحارس PID كامل:
        1. تحقق من وجود متاجر
        2. تحقق من PID القديم (هل هو حي؟)
        3. نظف الحالة العالقة إذا وجدت
        4. أطلق العملية الجديدة + سجل PID فوراً
        5. ابدأ ملف التقدم بحالة نظيفة
        """
        stores = _load_stores()
        if not stores:
            st.session_state["_sc_err"] = "لا توجد متاجر — أضف رابطاً أولاً"
            return

        if not _os_scraper.path.exists(_SCRAPER_SCRIPT):
            st.session_state["_sc_err"] = f"ملف الكاشط غير موجود: {_SCRAPER_SCRIPT}"
            return

        # ── حارس PID: منع التشغيل المتداخل ──────────────────────────────
        old_pid = _read_pid_file()
        if old_pid and _is_process_alive(old_pid):
            st.session_state["_sc_err"] = (
                f"⚠️ الكاشط يعمل بالفعل (PID: {old_pid}). "
                "اضغط «إيقاف» إذا أردت إعادة التشغيل."
            )
            return

        # تنظيف الحالة العالقة إذا وجدت
        if old_pid and not _is_process_alive(old_pid):
            _cleanup_stale_state()

        _os_scraper.makedirs(_DATA_SC, exist_ok=True)

        try:
            max_prod = (
                0 if st.session_state.get("sc_all_products", True)
                else int(st.session_state.get("sc_max_prod", 0) or 0)
            )
            concurrency = int(st.session_state.get("sc_concurrency", 3))
            concurrency = max(1, min(concurrency, 4))  # auto-clamp to 2-4 safe range

            log_fh = open(_LOG_FILE, "w", encoding="utf-8")
            # Parallelism: run every registered competitor at the same time.
            # parallel_stores=25 covers the current 18 stores + headroom for growth.
            _parallel_stores_arg = int(st.session_state.get("sc_parallel_stores", 25))
            # try/finally: يضمن إغلاق log_fh حتى لو فشل Popen — لمنع تسرب file descriptors
            try:
                proc = subprocess.Popen(
                    [
                        _sys_sc.executable, _SCRAPER_SCRIPT,
                        "--max-products",    str(max_prod),
                        "--concurrency",     str(concurrency),
                        "--parallel-stores", str(_parallel_stores_arg),
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=log_fh,
                    start_new_session=True,  # عملية مستقلة تماماً عن Streamlit
                )
            finally:
                # إغلاق مقبض الملف بعد تمريره للعملية الفرعية (أو عند فشلها)
                try:
                    log_fh.close()
                except Exception:
                    pass
            # حفظ PID فوراً قبل أي شيء آخر
            with open(_PID_FILE, "w", encoding="utf-8") as pf:
                pf.write(str(proc.pid))

            # تهيئة ملف التقدم بحالة نظيفة
            _write_progress_safe({
                "running":           True,
                "phase":             "discovering",
                "pid":               proc.pid,
                "started_at":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_updated":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "stores_total":      len(stores),
                "stores_done":       0,
                "urls_total":        0,
                "urls_processed":    0,
                "rows_in_csv":       0,
                "fetch_exceptions":  0,
                "success_rate_pct":  0.0,
                "current_store":     "",
                "store_urls_done":   0,
                "store_urls_total":  0,
                "stores_results":    {},
                "last_error":        "",
                "finished_at":       "",
            })

            st.session_state["_sc_started"] = True
            st.session_state["_sc_pid"]     = proc.pid

        except FileNotFoundError:
            st.session_state["_sc_err"] = f"Python غير موجود: {_sys_sc.executable}"
        except PermissionError:
            st.session_state["_sc_err"] = "رُفض الإذن لتشغيل العملية — تحقق من صلاحيات النظام"
        except Exception as _exc:
            st.session_state["_sc_err"] = f"فشل التشغيل: {str(_exc)[:150]}"

    # ════════════════════════════════════════════════════════════════════════
    #  عرض الرسائل الآنية من Callbacks
    # ════════════════════════════════════════════════════════════════════════
    if _sc_msg := st.session_state.pop("_sc_msg", None):
        getattr(st, _sc_msg[0], st.info)(_sc_msg[1])
    if st.session_state.pop("_sc_started", False):
        st.success(
            f"✅ بدأ الكاشط في الخلفية (PID: {st.session_state.get('_sc_pid','?')}) "
            "— التقدم يتحدث تلقائياً كل 3 ثوانٍ"
        )
    if _sc_err := st.session_state.pop("_sc_err", None):
        st.error(f"❌ {_sc_err}")

    # ════════════════════════════════════════════════════════════════════════
    #  القسم 1 — إدارة متاجر المنافسين
    # ════════════════════════════════════════════════════════════════════════
    with st.expander("🌐 إدارة متاجر المنافسين", expanded=not _is_alive):
        _col_url, _col_add = st.columns([5, 1])
        with _col_url:
            st.text_input(
                "رابط متجر المنافس",
                placeholder="https://example.com  ← أدخل الرابط ثم اضغط إضافة",
                key="sc_new_url",
                label_visibility="collapsed",
                help="يقبل أي متجر: سلة، زد، Shopify — النظام يكتشف المنصة تلقائياً",
                disabled=_is_alive,
            )
        with _col_add:
            st.button(
                "➕ إضافة",
                on_click=_cb_add_store,
                key="btn_add_store",
                use_container_width=True,
                disabled=_is_alive,
            )

        _stores_list = _load_stores()
        if _stores_list:
            st.caption(f"**{len(_stores_list)} متجر مستهدف:**")
            for _si, _surl in enumerate(_stores_list):
                _domain = (
                    _surl.replace("https://", "").replace("http://", "")
                    .rstrip("/").split("/")[0]
                )
                _r1, _r2 = st.columns([7, 1])
                with _r1:
                    st.markdown(
                        f'<div style="padding:5px 10px;background:#1a1a2e;border-radius:6px;'
                        f'font-size:.85rem;margin-bottom:2px">'
                        f'{_si + 1}. <b>{_domain}</b>'
                        f'<span style="color:#444;font-size:.75rem"> — {_surl}</span>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with _r2:
                    st.button(
                        "🗑️",
                        key=f"del_store_{_si}",
                        on_click=_cb_remove_store,
                        args=(_si,),
                        use_container_width=True,
                        help=f"حذف {_surl}",
                        disabled=_is_alive,  # لا حذف أثناء الكشط
                    )
        else:
            st.info(
                "💡 **أضف رابط متجر** — النظام يتولى تلقائياً:\n"
                "اكتشاف المنصة ← جمع الروابط ← الكشط ← حفظ النتائج"
            )

    # ════════════════════════════════════════════════════════════════════════
    #  القسم 2 — الإعدادات والجدولة
    # ════════════════════════════════════════════════════════════════════════
    with st.expander("⚙️ إعدادات الكشط والجدولة", expanded=False):
        _sc_c1, _sc_c2, _sc_c3 = st.columns(3)
        with _sc_c1:
            st.checkbox(
                "🔄 جميع المنتجات (بلا سقف)",
                value=True,
                key="sc_all_products",
                help="يكشط كل منتج موجود في Sitemap — موصى به",
                disabled=_is_alive,
            )
        with _sc_c2:
            st.number_input(
                "أقصى منتجات / متجر",
                0, 50000,
                0 if st.session_state.get("sc_all_products", True) else 1000,
                step=500,
                key="sc_max_prod",
                disabled=_is_alive or bool(st.session_state.get("sc_all_products", True)),
                help="0 = جميع المنتجات",
            )
        with _sc_c3:
            st.number_input(
                "طلبات متزامنة",
                1, 8, 3,
                step=1,
                key="sc_concurrency",
                help="تلقائي 2–4 لتجنّب 403 من Cloudflare. لا تتخطَّ 4 إلا إذا كان عندك بروكسيات.",
                disabled=_is_alive,
            )

        # ── الجدولة التلقائية ────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**⏰ الجدولة التلقائية**")

        try:
            from scrapers.scheduler import (
                get_scheduler_status, enable_scheduler, disable_scheduler,
                trigger_now as _trigger_now,
            )
            _sch        = get_scheduler_status()
            _sch_enabled  = bool(_sch.get("enabled", False))
            _sch_interval = int(_sch.get("interval_hours", 12))
            _sch_runs     = int(_sch.get("runs_count", 0))
            _sch_last     = str(_sch.get("last_run", "") or "لم يعمل بعد")[:19]
            _sch_next     = _sch.get("next_run_label", "—")
            _sch_ok       = True
        except Exception:
            _sch_ok      = False
            _sch_enabled = False

        if _sch_ok:
            _sh1, _sh2 = st.columns([4, 2])
            with _sh1:
                if _sch_enabled:
                    st.success(
                        f"🤖 مُفعَّلة — كل {_sch_interval}h "
                        f"| التالي: **{_sch_next}** "
                        f"| التشغيلات: {_sch_runs}"
                    )
                else:
                    st.caption("⏸️ الجدولة التلقائية معطَّلة — فعّلها لكشط المنافسين آلياً")
            with _sh2:
                st.number_input(
                    "تكرار (ساعات)", 1, 168, _sch_interval,
                    step=1, key="sc_interval_h",
                )

            def _cb_toggle_scheduler():
                _h = int(st.session_state.get("sc_interval_h", 12))
                if not _sch_enabled:
                    enable_scheduler(interval_hours=_h)
                    st.session_state["_sc_msg"] = (
                        "success", f"✅ الجدولة مُفعَّلة — كشط كل {_h} ساعة"
                    )
                else:
                    disable_scheduler()
                    st.session_state["_sc_msg"] = ("warning", "⏸️ الجدولة معطَّلة")

            def _cb_run_now_sched():
                """
                تشغيل فوري من الجدولة — مع حارس PID لمنع التداخل.
                """
                _old_pid = _read_pid_file()
                if _old_pid and _is_process_alive(_old_pid):
                    st.session_state["_sc_msg"] = (
                        "error",
                        f"⚠️ الكاشط يعمل بالفعل (PID: {_old_pid}) — انتظر أو أوقفه أولاً"
                    )
                    return
                # تنظيف العالق إن وجد
                if _old_pid and not _is_process_alive(_old_pid):
                    _cleanup_stale_state()
                _mp = (
                    0 if st.session_state.get("sc_all_products", True)
                    else int(st.session_state.get("sc_max_prod", 0) or 0)
                )
                _cc = int(st.session_state.get("sc_concurrency", 3))
                _cc = max(1, min(_cc, 4))  # auto-clamp to 2-4 safe range
                try:
                    ok = _trigger_now(max_products=_mp, concurrency=_cc)
                    if ok:
                        st.session_state["_sc_msg"] = ("success", "🚀 تم إطلاق الكشط الآن!")
                    else:
                        st.session_state["_sc_msg"] = ("error", "❌ فشل تشغيل الكاشط من الجدولة")
                except Exception as _te:
                    st.session_state["_sc_msg"] = ("error", f"❌ خطأ في trigger_now: {_te}")

            _sb1, _sb2 = st.columns(2)
            with _sb1:
                st.button(
                    "⏸️ تعطيل الجدولة" if _sch_enabled else "🤖 تفعيل الجدولة",
                    on_click=_cb_toggle_scheduler,
                    key="btn_toggle_sched",
                    use_container_width=True,
                    type="secondary" if _sch_enabled else "primary",
                )
            with _sb2:
                st.button(
                    "🚀 تشغيل الآن (جدولة)",
                    on_click=_cb_run_now_sched,
                    key="btn_run_now_sched",
                    use_container_width=True,
                    disabled=_is_alive,
                )
        else:
            st.caption("⚠️ وحدة الجدولة غير متاحة (scrapers/scheduler.py)")

    # ════════════════════════════════════════════════════════════════════════
    #  القسم 3 — أزرار التشغيل الرئيسية + تقدير الحجم
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    _stores_count = len(_load_stores())

    _btn_c1, _btn_c2 = st.columns([3, 2])
    with _btn_c1:
        if _is_alive:
            st.button(
                f"⏹️ إيقاف الكاشط (PID: {_pid})",
                on_click=_cb_stop_scraper,
                key="btn_stop_scraper",
                use_container_width=True,
                type="secondary",
            )
        else:
            _start_label = (
                "🚀 بدء الكشط" if _stores_count > 0
                else "🚀 بدء الكشط — أضف متجراً أولاً"
            )
            st.button(
                _start_label,
                type="primary",
                on_click=_start_scraper_bg,
                key="btn_start_scraper",
                use_container_width=True,
                disabled=(_stores_count == 0),
            )

    with _btn_c2:
        if _stores_count > 0:
            _all_flag = bool(st.session_state.get("sc_all_products", True))
            _limit    = int(st.session_state.get("sc_max_prod", 0) or 0)
            _est_txt  = (
                f"جميع المنتجات من **{_stores_count}** متجر"
                if (_all_flag or _limit == 0)
                else f"حتى **{_stores_count * _limit:,}** منتج"
            )
            st.info(f"📊 {_est_txt}")

    # ════════════════════════════════════════════════════════════════════════
    #  القسم 4 — لوحة المراقبة الحية
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("📊 لوحة المراقبة")

    # ── تحديث تلقائي أثناء التشغيل (بدون مكوّن خارجي) ─────────────────────
    if _is_alive:
        st.session_state["_app_scraper_live_tick_n"] = 0
        _scraper_main_tab_live_rerun_tick()
    else:
        st.session_state.pop("_app_scraper_live_tick_n", None)

    # ── تعريف labels لكل حالة ─────────────────────────────────────────────
    _PHASE_META = {
        "discovering": ("🔍 اكتشاف الروابط...",      "#1a2a3a", "#4fc3f7"),
        "scraping":    ("🔄 جاري الكشط...",           "#0a2a0a", "#00C853"),
        "retrying":    ("⏳ إعادة محاولة (backoff)...", "#2a1a00", "#FFA000"),
        "stale":       ("⚠️ يبدو معلقاً — يجري التحقق (5+ دق بدون تحديث)", "#2a1800", "#FF6F00"),
        "completed":   ("✅ اكتمل بنجاح",              "#0a2a0a", "#00C853"),
        "partial":     ("⚠️ اكتمل جزئياً (أخطاء مرتفعة)", "#2a1800", "#FF9800"),
        "failed":      ("❌ فشل — لم تُحفظ منتجات",    "#2a0a0a", "#EF5350"),
        "timeout":     ("⏰ انتهت المهلة",             "#2a1800", "#FF6F00"),
        "stopped":     ("⏹️ موقوف",                   "#1a1a1a", "#9e9e9e"),
    }
    _plabel, _pbg, _pcolor = _PHASE_META.get(_phase, ("◻️ غير معروف", "#111", "#666"))

    # ── استخراج أرقام التقدم ─────────────────────────────────────────────
    _rows        = int(_prog.get("rows_in_csv", 0))
    _errors      = int(_prog.get("fetch_exceptions", 0))
    _success_raw = float(_prog.get("success_rate_pct", 0))
    _success     = min(_success_raw, 100.0)           # لا تتجاوز 100%
    _current     = str(_prog.get("current_store", ""))
    _last_err    = str(_prog.get("last_error", ""))
    _stores_done = int(_prog.get("stores_done", 0))
    _stores_tot  = max(int(_prog.get("stores_total", 1)), 1)
    _s_urls_done = int(_prog.get("store_urls_done", 0))
    _s_urls_tot  = max(int(_prog.get("store_urls_total", 1)), 1)
    _stores_res  = dict(_prog.get("stores_results") or {})
    _finished    = str(_prog.get("finished_at", ""))
    _started     = str(_prog.get("started_at", ""))

    # ── توحيد عداد المنتجات مع تفاصيل المتاجر (منع تعارض KPI) ────────────
    try:
        _state_map_top = _load_scraper_state_map()
    except Exception:
        _state_map_top = {}
    try:
        _csv_counts_top = _load_csv_rows_by_store(_OUTPUT_CSV)
    except Exception:
        _csv_counts_top = {}
    _sum_store_results = 0
    try:
        for _d_all in [ (s.replace("https://","").replace("http://","").rstrip("/").split("/")[0])
                         for s in _load_stores() ]:
            _cands = [
                _stores_res.get(_d_all),
                (_state_map_top.get(_d_all, {}) or {}).get("rows_saved"),
                _read_live_store_progress(_d_all).get("rows_saved"),
                _csv_counts_top.get(_d_all),
            ]
            _best = 0
            for _c in _cands:
                try:
                    if _c is not None:
                        _best = max(_best, int(_c))
                except Exception:
                    pass
            _sum_store_results += _best
    except Exception:
        _sum_store_results = 0
    # الرقم الموحّد: الأكبر من (CSV counter) و (مجموع تفاصيل المتاجر)
    _rows_unified = max(_rows, _sum_store_results)
    _rows = _rows_unified

    if not _os_scraper.path.exists(_PROGRESS_FILE) and not _is_alive:
        # لم يبدأ أي كشط بعد
        if _stores_count > 0:
            st.info(
                f"💡 **{_stores_count} متجر جاهز** — اضغط «بدء الكشط» للانطلاق.\n\n"
                "النظام يتولى تلقائياً: اكتشاف الروابط ← الكشط ← حفظ النتائج ← إدارة الحظر"
            )
        else:
            st.info("💡 أضف متجر منافس أولاً من القسم الأول.")
    else:
        # ── شارة الحالة ──────────────────────────────────────────────────
        _status_extra = ""
        if _is_alive and _current:
            _status_extra = (
                f' — المتجر: <b style="color:{_pcolor}">{_current}</b>'
                f'<span style="color:#555;font-size:.78rem;margin-right:8px"> PID:{_pid}</span>'
            )
        elif _finished and not _is_alive:
            _status_extra = f'<span style="color:#555;font-size:.78rem"> — انتهى: {_finished[:16]}</span>'

        st.markdown(
            f'<div style="background:{_pbg};border:1px solid {_pcolor};'
            f'border-radius:8px;padding:10px 16px;margin-bottom:10px">'
            f'<b style="color:{_pcolor}">{_plabel}</b>'
            f'{_status_extra}'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── أشرطة التقدم ─────────────────────────────────────────────────
        _store_pct = min(_stores_done / _stores_tot, 1.0)
        st.progress(
            _store_pct,
            text=f"🏪 المتاجر: {_stores_done} / {_stores_tot}  ({_store_pct * 100:.0f}%)",
        )

        if _is_alive and _current and _s_urls_tot > 1:
            _cur_pct = min(_s_urls_done / _s_urls_tot, 1.0)
            st.progress(
                _cur_pct,
                text=f"🔗 {_current}: {_s_urls_done:,} / {_s_urls_tot:,} رابط  ({_cur_pct * 100:.0f}%)",
            )

        # ── بطاقات الأرقام ────────────────────────────────────────────────
        _rows_run = int(_prog.get("rows_saved_run", 0))
        _urls_proc = int(_prog.get("urls_processed", 0))
        _mc1, _mc2, _mc3, _mc4 = st.columns(4)
        _mc1.metric("🏪 متاجر",     f"{_stores_done}/{_stores_tot}")
        _mc2.metric("📦 محفوظ (هذا الجري)", f"{_rows_run:,}")
        _mc3.metric("📈 نجاح",      f"{_success:.1f}%")
        _mc4.metric("⚠️ أخطاء",    str(_errors))
        if _rows > _rows_run:
            st.caption(f"📊 إجمالي في ملف CSV: {_rows:,} منتج  |  🔗 روابط مفحوصة: {_urls_proc:,}")

        # ── قائمة المتاجر التفصيلية ──────────────────────────────────────
        _all_stores_list = _load_stores()
        _state_map = _load_scraper_state_map()
        _csv_counts = _load_csv_rows_by_store(_OUTPUT_CSV)
        if _all_stores_list:
            st.markdown("**📋 تفاصيل المتاجر:**")
            _html_items = []
            for _si, _surl in enumerate(_all_stores_list):
                _d = (
                    _surl.replace("https://", "").replace("http://", "")
                    .rstrip("/").split("/")[0]
                )
                _cp = _state_map.get(_d, {}) if isinstance(_state_map, dict) else {}
                _live = _read_live_store_progress(_d)
                _cnt_candidates = [
                    _stores_res.get(_d),
                    _cp.get("rows_saved"),
                    _live.get("rows_saved"),
                    _csv_counts.get(_d),
                ]
                _cnt = None
                for _candidate in _cnt_candidates:
                    try:
                        if _candidate is not None:
                            _candidate_int = int(_candidate)
                            _cnt = max(_cnt or 0, _candidate_int)
                    except Exception:
                        continue

                if _d == _current and _is_alive:
                    _live_urls_done = int(_live.get("urls_done", _s_urls_done) or 0)
                    _live_urls_total = max(int(_live.get("urls_total", _s_urls_tot) or 1), 1)
                    _live_rows = max(int(_live.get("rows_saved", 0) or 0), int(_cnt or 0))
                    _cbar = int(min(_live_urls_done / _live_urls_total, 1.0) * 100) if _live_urls_total > 1 else 0
                    _item = (
                        f'<div style="background:#0a1a2a;border:1px solid #4fc3f7;'
                        f'border-radius:6px;padding:7px 12px;font-size:.82rem">'
                        f'🔄 <b style="color:#4fc3f7">{_si+1}. {_d}</b>'
                        f'<span style="color:#9e9e9e"> — {_live_urls_done:,}/{_live_urls_total:,} رابط</span>'
                        f'<span style="color:#4fc3f7"> — {_live_rows:,} منتج محفوظ</span>'
                        f'<div style="margin-top:4px;height:4px;background:#1a2a3a;border-radius:2px">'
                        f'<div style="width:{_cbar}%;height:100%;background:#4fc3f7;border-radius:2px"></div>'
                        f'</div></div>'
                    )
                elif _cnt is not None:
                    _item = (
                        f'<div style="background:#0a1a0a;border:1px solid #1e3a1e;'
                        f'border-radius:6px;padding:7px 12px;font-size:.82rem">'
                        f'✅ <span style="color:#9e9e9e">{_si+1}. {_d}</span>'
                        f'<span style="color:#00C853"> — {_cnt:,} منتج</span>'
                        f'</div>'
                    )
                elif _cp.get("status") == "done" or _si < _stores_done:
                    _item = (
                        f'<div style="background:#0a1a0a;border:1px solid #1e3a1e;'
                        f'border-radius:6px;padding:7px 12px;font-size:.82rem">'
                        f'✅ <span style="color:#777">{_si+1}. {_d}</span>'
                        f'<span style="color:#90a4ae"> — اكتمل، جارِ مزامنة العدد</span>'
                        f'</div>'
                    )
                elif _cp.get("status") == "error":
                    _item = (
                        f'<div style="background:#2a0a0a;border:1px solid #7f1d1d;'
                        f'border-radius:6px;padding:7px 12px;font-size:.82rem">'
                        f'❌ <span style="color:#ef9a9a">{_si+1}. {_d}</span>'
                        f'</div>'
                    )
                elif _is_alive:
                    _item = (
                        f'<div style="background:#111;border:1px dashed #333;'
                        f'border-radius:6px;padding:7px 12px;font-size:.82rem">'
                        f'⏳ <span style="color:#555">{_si+1}. {_d}</span>'
                        f'</div>'
                    )
                else:
                    _item = (
                        f'<div style="background:#111;border:1px solid #222;'
                        f'border-radius:6px;padding:7px 12px;font-size:.82rem">'
                        f'⬜ <span style="color:#777">{_si+1}. {_d}</span>'
                        f'</div>'
                    )
                _html_items.append(_item)

            st.markdown(
                '<div style="display:flex;flex-direction:column;gap:4px;margin-top:6px">'
                + "".join(_html_items)
                + "</div>",
                unsafe_allow_html=True,
            )

        # ── تشخيص: الفشل / الاكتمال الجزئي ───────────────────────────────
        if (not _is_alive) and _phase in ("failed", "partial", "timeout") :
            _urls_proc = int(_prog.get("urls_processed", 0) or 0)
            _err_ratio = (_errors / max(_urls_proc, 1)) * 100 if _urls_proc else 100.0
            # تجميع مؤشرات الحجب HTTP من stores_http_errors
            _http_err_map = _prog.get("stores_http_errors") or {}
            _sum_403 = 0
            _sum_429 = 0
            if isinstance(_http_err_map, dict):
                for _v in _http_err_map.values():
                    try:
                        _sum_403 += int((_v or {}).get("403", 0) or 0)
                        _sum_429 += int((_v or {}).get("429", 0) or 0)
                    except Exception:
                        pass

            # ── Evidence-backed failure-class selection ───────────────────
            # Trust persisted counters (urls_discovered/enqueued/attempted +
            # skipped_reason histogram). Never claim "sitemap empty" unless
            # urls_discovered == 0.
            _discovered = int(_prog.get("urls_discovered", 0) or 0)
            _enqueued   = int(_prog.get("urls_enqueued",   0) or 0)
            _attempted  = int(_prog.get("urls_attempted",  0) or 0)
            _skipmap    = _prog.get("urls_skipped_reason") or {}
            if not isinstance(_skipmap, dict):
                _skipmap = {}

            _hints = []
            # Class 1 — HTTP blocks dominate (Cloudflare / WAF / 429 rate-limit)
            if _sum_403 > 0 or _sum_429 > 0:
                _hints.append(
                    f"🛡️ **حجب HTTP مرصود**: 403×{_sum_403} · 429×{_sum_429} — "
                    "غالباً Cloudflare/Rate-Limit. قلّل «طلبات متزامنة» إلى 2–4 "
                    "أو فعّل بروكسي عبر متغيرات البيئة `SCRAPER_PROXIES`."
                )

            # Class 2 — sitemap/discovery failure (truly no URLs found)
            if _discovered == 0:
                _sm_to  = int(_skipmap.get("sitemap_timeout", 0) or 0)
                _sm_blk = int(_skipmap.get("sitemap_blocked", 0) or 0)
                _sm_emp = int(_skipmap.get("empty_sitemap",   0) or 0)
                if _sm_blk:
                    _hints.append("🗺️ **Sitemap محجوب** — المضيف يرفض `/sitemap.xml` (WAF/403). جرّب بروكسي.")
                elif _sm_to:
                    _hints.append("🗺️ **انتهت مهلة Sitemap** — المضيف بطيء أو يعلق. أعد المحاولة لاحقاً.")
                elif _sm_emp:
                    _hints.append("🗺️ **Sitemap فارغ** — لم يُرجع أي روابط منتج، و `products.json` أيضاً فشل.")
                else:
                    _hints.append("🗺️ **لم تُكتشف روابط** — تعذّر حلّ أي مسار منتج لهذا المتجر.")

            # Class 3 — discovered URLs but nothing was attempted (logic bug)
            elif _attempted == 0:
                _hints.append(
                    f"🐛 **اكتُشف {_discovered:,} رابط لكن لم تُحاوَل معالجة أيّها** — "
                    "خلل في قائمة الانتظار أو جميع الروابط قد تم تخطّيها."
                )
                if _skipmap:
                    _top = ", ".join(f"{k}:{v}" for k, v in
                                     sorted(_skipmap.items(), key=lambda x: -int(x[1] or 0))[:4])
                    _hints.append(f"• أسباب التخطّي المرصودة: {_top}")

            # Class 4 — attempted but 0 rows and 0 HTTP blocks and 0 exceptions
            #          => parse-empty (JS-rendered / no Structured Data)
            elif _rows == 0 and _errors == 0 and _sum_403 == 0 and _sum_429 == 0:
                _hints.append(
                    f"🧩 **{_attempted:,} محاولة دون استخراج** — الصفحات لا تحتوي "
                    "JSON-LD/OpenGraph أو تستخدم تحميلاً ديناميكياً (JS). "
                    "فعّل المستخرج الاحتياطي (AI last-resort)."
                )

            # Class 5 — exceptions dominate (network / parsing errors)
            elif _rows == 0 and _errors > 0:
                _hints.append(
                    f"⏱️ **{_errors} خطأ شبكة/تحليل** على {_attempted:,} محاولة — "
                    "تحقّق من التزامن ومهلة الطلب."
                )

            # Transparent evidence footer so the user sees raw counters
            _hints.append(
                f"📊 اكتُشف {_discovered:,} · أُدرج {_enqueued:,} · "
                f"حُوول {_attempted:,} · حُفظ {_rows:,}"
            )

            if not _hints:
                _hints.append("⏱️ سبب غير مصنّف — راجع السجلات.")

            _head_color = "#EF5350" if _phase == "failed" else "#FF9800"
            _head_icon  = "❌" if _phase == "failed" else ("⚠️" if _phase == "partial" else "⏰")
            _head_txt = {
                "failed":  f"{_head_icon} انتهى الكشط دون حفظ أي منتج",
                "partial": f"{_head_icon} اكتمل جزئياً — {_rows:,} منتج محفوظ لكن نسبة الأخطاء عالية",
                "timeout": f"{_head_icon} انتهت المهلة قبل اكتمال الكشط",
            }[_phase]
            st.markdown(
                f"<div style='background:#2a0a0a;border:1px solid {_head_color};"
                f"border-radius:8px;padding:10px 14px;color:{_head_color};"
                f"font-weight:700;margin-bottom:6px'>{_head_txt} — "
                f"{_errors} خطأ (≈ {_err_ratio:.0f}%)</div>",
                unsafe_allow_html=True,
            )
            for _h in _hints:
                st.markdown(f"- {_h}")

        # ── سجل الأخطاء ──────────────────────────────────────────────────
        if _last_err:
            with st.expander(f"⚠️ آخر خطأ مسجل ({_errors} حادث)", expanded=False):
                st.error(_last_err)

        # ── سجل stderr ───────────────────────────────────────────────────
        if _os_scraper.path.exists(_LOG_FILE):
            _log_size_bytes = _os_scraper.path.getsize(_LOG_FILE)
            if _log_size_bytes > 0:
                with st.expander(
                    f"📄 سجل التشغيل ({_log_size_bytes // 1024 + 1} KB)",
                    expanded=False,
                ):
                    try:
                        with open(_LOG_FILE, "r", encoding="utf-8", errors="replace") as _lf:
                            _log_content = _lf.read()
                        # آخر 3000 حرف فقط
                        _log_tail = _log_content[-3000:] if len(_log_content) > 3000 else _log_content
                        st.code(_log_tail, language=None)
                    except Exception:
                        st.caption("تعذّر قراءة السجل")

        # زر تحديث يدوي فقط إذا لم يكن التحديث تلقائياً
        if not _is_alive:
            st.button("🔄 تحديث يدوي", key="sc_manual_refresh")

    # ════════════════════════════════════════════════════════════════════════
    #  Spider Dashboard — Unified (Phase 4: merged Sections 5+5.5+6)
    # ════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.subheader("🕷️ Spider Dashboard")

    # ── Metrics Row ──────────────────────────────────────────────────────
    _store_stats = get_competitor_store_stats()
    _sp_total = _store_stats.get("total_products", 0)
    _sp_with_price = _store_stats.get("with_price", 0)
    _sp_no_price = max(0, _sp_total - _sp_with_price)

    _sp_c1, _sp_c2, _sp_c3, _sp_c4 = st.columns(4)
    _sp_c1.metric("📦 إجمالي", f"{_sp_total:,}")
    _sp_c2.metric("💰 بسعر", f"{_sp_with_price:,}")
    _sp_c3.metric("🔍 بدون سعر", f"{_sp_no_price:,}")
    _sp_c4.metric("📊 تغطية", f"{_sp_with_price*100//max(_sp_total,1)}%")

    # ── Product Table ────────────────────────────────────────────────────
    if _sp_total > 0:
        _sel_comp = st.selectbox(
            "المنافس",
            ["الكل"] + list(_store_stats.get("by_competitor", {}).keys()),
            key="spider_comp_filter",
        )
        _comp_filter = "" if _sel_comp == "الكل" else _sel_comp
        _local_prods_df = get_competitor_products_df(_comp_filter)

        if not _local_prods_df.empty:
            _display_cols = [c for c in ("product_name", "competitor", "price", "brand", "updated_at") if c in _local_prods_df.columns]
            _col_rename = {"product_name": "المنتج", "competitor": "المنافس", "price": "السعر (ر.س)", "brand": "الماركة", "updated_at": "آخر تحديث"}
            _show_df = _local_prods_df[_display_cols].rename(columns=_col_rename) if _display_cols else _local_prods_df
            st.dataframe(_show_df, use_container_width=True, height=400, hide_index=True)

            # ── 🧹 تنظيف الصفوف الفاسدة (اسم=ID + سعر=0) ───────────────
            with st.expander("🧹 تنظيف البيانات الفاسدة", expanded=False):
                st.caption(
                    "يحذف الصفوف التي فشل كشطها: السعر = 0 والاسم على شكل ID "
                    "(مثل « منتج P12345 » أو هاش عشوائي)، ويحرّر أي مهام تحليل "
                    "عالقة. آمن ولا يلمس البيانات الصحيحة."
                )
                if st.button("🗑️ احذف الصفوف الفاسدة الآن", key="btn_clean_corrupt",
                             type="secondary", use_container_width=True):
                    try:
                        from utils.db_manager import (
                            get_db,
                            trigger_gcs_sync,
                            release_stale_running_jobs,
                        )
                        _conn = get_db()
                        _cur = _conn.cursor()
                        _n_before = _cur.execute(
                            "SELECT COUNT(*) FROM competitor_products_store"
                        ).fetchone()[0]
                        # كل صف سعره ≤ 0 واسمه على شكل placeholder
                        # «منتج P…» / «P123…» / «pngrandom» يُحذف بشكل جذري
                        # (ROOT CAUSE DELETE) — لا يلمس أي صف بسعر حقيقي.
                        _cur.execute("""
                            DELETE FROM competitor_products_store
                            WHERE (price IS NULL OR price <= 0)
                              AND (
                                product_name LIKE 'منتج P%'
                                OR product_name LIKE 'منتج p%'
                                OR product_name GLOB 'P[0-9]*'
                                OR product_name GLOB 'p[0-9]*'
                                OR product_name GLOB 'P[A-Za-z0-9]*[Pp]ng'
                                OR product_name GLOB 'P[A-Za-z0-9]*[Jj]pg'
                                OR product_name GLOB 'منتج P[A-Za-z0-9]*[Pp]ng'
                                OR product_name GLOB 'منتج P[A-Za-z0-9]*[Jj]pg'
                                OR product_name IS NULL
                                OR TRIM(product_name) = ''
                              )
                        """)
                        _deleted = _cur.rowcount
                        _conn.commit()
                        _n_after = _cur.execute(
                            "SELECT COUNT(*) FROM competitor_products_store"
                        ).fetchone()[0]
                        _conn.close()

                        # حرّر أي مهمة تحليل عالقة (stuck job) — ≥ 5 دقائق
                        # بدون تحديث → تُعلَّم stopped. هذا يُحرّر الواجهة فوراً
                        # عند الضغط على الزر.
                        try:
                            _unstuck = release_stale_running_jobs(stale_after_seconds=300)
                        except Exception:
                            _unstuck = 0

                        # احذف أي ملفات قفل خلفية معروفة
                        _removed_locks = 0
                        try:
                            import glob as _glob
                            _data_dir = os.environ.get("DATA_DIR", "data")
                            for _pat in ("*.lock", "_lock_*", "scraper.pid"):
                                for _lp in _glob.glob(os.path.join(_data_dir, _pat)):
                                    try:
                                        os.remove(_lp)
                                        _removed_locks += 1
                                    except Exception:
                                        pass
                        except Exception:
                            pass

                        try:
                            trigger_gcs_sync(force=True)
                        except Exception:
                            pass
                        st.success(
                            f"✅ تم حذف {_deleted} صف فاسد | "
                            f"قبل: {_n_before} → بعد: {_n_after} | "
                            f"مهام عالقة مُحرَّرة: {_unstuck} | "
                            f"قفل مُزال: {_removed_locks}"
                        )
                        st.rerun()
                    except Exception as _e_clean:
                        st.error(f"❌ تعذّر التنظيف: {_e_clean}")
        else:
            st.info("لا توجد منتجات لهذا المنافس.")

        # ── زر: إرسال المنتجات المكشوطة للتحليل ──────────────────────────
        if st.button(
            "📤 إرسال المنتجات المكشوطة للتحليل",
            key="btn_send_scraped_to_analysis",
            type="primary",
            use_container_width=True,
            help="ينقل كل المنتجات المكشوطة إلى لوحة التحكم للمقارنة والتحليل",
        ):
            try:
                _full_df = get_competitor_products_df("")  # كل المنافسين
                if _full_df is None or _full_df.empty:
                    # fallback: CSV
                    try:
                        if _os_scraper.path.exists(_OUTPUT_CSV):
                            _full_df = pd.read_csv(
                                _OUTPUT_CSV, encoding="utf-8-sig", low_memory=False
                            )
                    except Exception:
                        _full_df = None

                if _full_df is None or _full_df.empty:
                    st.warning("⚠️ لا توجد منتجات مكشوطة بعد — ابدأ الكشط أولاً.")
                else:
                    _rename_map = {
                        "product_name": "المنتج", "name": "المنتج",
                        "price":        "السعر",
                        "image_url":    "صورة_المنافس",
                        "product_url":  "رابط_المنافس",
                        "brand":        "الماركة",
                    }
                    _df_norm = _full_df.rename(
                        columns={k: v for k, v in _rename_map.items() if k in _full_df.columns}
                    ).copy()

                    # العمود الذي يُعرّف المنافس
                    _comp_col = (
                        "competitor" if "competitor" in _df_norm.columns
                        else ("store" if "store" in _df_norm.columns else None)
                    )

                    _comp_dfs: dict = {}
                    if _comp_col is None:
                        _comp_dfs["كل المنتجات"] = _df_norm
                    else:
                        for _comp, _g in _df_norm.groupby(_comp_col):
                            if not _comp or str(_comp).lower() == "nan":
                                continue
                            _gdf = _g.copy()
                            _gdf["المنافس"]       = _comp
                            _gdf["منتج_المنافس"] = _gdf.get("المنتج", "")
                            _gdf["سعر_المنافس"]  = _gdf.get("السعر", 0)
                            _comp_dfs[str(_comp)] = _gdf

                    if not _comp_dfs:
                        st.warning("⚠️ تعذر تجهيز البيانات للتحليل.")
                    else:
                        st.session_state["comp_dfs"]            = _comp_dfs
                        st.session_state["_use_auto_scraper"]   = True
                        st.session_state["_nav_pending"]        = "📊 لوحة التحكم"
                        st.session_state["nav_flash"]           = (
                            f"✅ أُرسل {len(_df_norm):,} منتج من "
                            f"{len(_comp_dfs)} منافس للتحليل"
                        )
                        st.success(
                            f"✅ تم تجهيز {len(_df_norm):,} منتج من "
                            f"{len(_comp_dfs)} منافس — جاري الانتقال للوحة التحكم..."
                        )
                        st.rerun()
            except Exception as _send_err:
                st.error(f"❌ فشل الإرسال: {_send_err}")
    else:
        st.info("📭 قاعدة البيانات المحلية فارغة. ابدأ الكشط لجلب البيانات.")

    # ── Advanced Price Scraper (v30.2) ───────────────────────────────────
    with st.expander("🕷️ كشط الأسعار المفقودة (v30.2)", expanded=_sp_no_price > 0):
        if _sp_no_price > 0:
            st.caption(f"🔍 {_sp_no_price:,} منتج بدون سعر — يمكن كشط أسعارها تلقائياً.")
        _adv_c1, _adv_c2 = st.columns([2, 1])
        with _adv_c1:
            _adv_store = st.text_input(
                "المنافس (فارغ = الكل)", value="",
                key="adv_scraper_store_filter", placeholder="مثال: قولدن سنت",
            )
        with _adv_c2:
            _adv_limit = st.number_input(
                "الحد الأقصى", min_value=100, max_value=10000,
                value=2000, step=500, key="adv_scraper_limit",
            )

        if st.button("🚀 بدء كشط الأسعار (موازي – كل المنافسين)", key="btn_adv_scraper_v30", type="primary", use_container_width=True):
            _adv_prog   = st.progress(0, text="جاري الكشط...")
            _adv_status = st.empty()   # Live per-store counter panel
            _adv_metric = st.empty()   # Totals row

            def _adv_progress(snapshot):
                """Live progress callback — called from the async scraper as
                each product finishes. Accepts both the new dict shape and the
                legacy (done, total) tuple for backwards compatibility."""
                # Legacy signature fallback
                if not isinstance(snapshot, dict):
                    return
                _done   = snapshot.get("total_done", 0)
                _target = snapshot.get("total_target", 1)
                _found  = snapshot.get("prices_found", 0)
                _errs   = snapshot.get("errors", 0)
                _saved  = snapshot.get("updated_in_db", 0)
                _by     = snapshot.get("by_store", {})

                _adv_prog.progress(
                    min(_done / max(_target, 1), 1.0),
                    text=f"🕷️ {_done}/{_target} | أسعار: {_found} | محفوظ: {_saved} | أخطاء: {_errs}",
                )
                # Per-store counter rows
                try:
                    _lines = []
                    for _s, _v in _by.items():
                        _pct = _v["done"] * 100 // max(_v["total"], 1)
                        _lines.append(
                            f"• **{_s}** — {_v['done']:,}/{_v['total']:,} ({_pct}%) · "
                            f"أسعار: {_v['prices']:,}"
                        )
                    _adv_status.markdown("\n".join(_lines))
                except Exception:
                    pass

            try:
                import asyncio as _aio
                from engines.scraper_v30_advanced import run_advanced_price_scraping

                # ── تشغيل الكشط في thread منفصل لعدم حظر Streamlit ──
                def _run_scraper():
                    loop = _aio.new_event_loop()
                    _aio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(run_advanced_price_scraping(
                            store_filter=_adv_store.strip(),
                            limit=int(_adv_limit),
                            progress_cb=_adv_progress,
                            max_parallel_stores=25,
                        ))
                    finally:
                        loop.close()

                import threading
                _t = threading.Thread(target=_run_scraper, daemon=True)
                _t.start()
                st.toast("⏳ جاري العمل في الخلفية...")
                _adv_result = None

                # Final summary metrics (only if a synchronous result is available)
                if _adv_result:
                    _adv_prog.progress(1.0, text="✅ اكتمل")
                    _m1, _m2, _m3, _m4 = _adv_metric.columns(4)
                    _m1.metric("✅ مكشوط", f"{_adv_result.get('total_scraped', 0):,}")
                    _m2.metric("💰 أسعار", f"{_adv_result.get('prices_found', 0):,}")
                    _m3.metric("💾 محفوظ", f"{_adv_result.get('updated_in_db', 0):,}")
                    _m4.metric("❌ أخطاء", f"{_adv_result.get('errors', 0):,}")

                    if _adv_result.get("prices_found", 0) > 0:
                        st.success(_adv_result["message"])
                        # Auto-flow to full analysis — routes products to matching cards
                        st.session_state["_use_auto_scraper"]       = True
                        st.session_state["_sc_auto_analysis_pending"] = True
                        st.session_state["_nav_pending"]            = "📊 لوحة التحكم"
                        st.session_state["nav_flash"]               = (
                            f"🤖 {_adv_result['prices_found']:,} منتج بسعر — جاري التحليل..."
                        )
                        st.rerun()
                    else:
                        st.info(_adv_result["message"])
            except Exception as _adv_err:
                _adv_prog.progress(1.0, text="❌ خطأ")
                st.error(f"❌ خطأ: {_adv_err}")

    # ── Export & Analysis Trigger ────────────────────────────────────────
    if _os_scraper.path.exists(_OUTPUT_CSV):
        _csv_size_kb = round(_os_scraper.path.getsize(_OUTPUT_CSV) / 1024, 1)
        _csv_rows = 0
        try:
            with open(_OUTPUT_CSV, encoding="utf-8-sig") as _f:
                _csv_rows = sum(1 for _ in _f) - 1
        except Exception:
            pass

        _dl_col, _go_col = st.columns(2)
        with _dl_col:
            with open(_OUTPUT_CSV, "rb") as _fout:
                st.download_button(
                    f"📥 CSV ({_csv_size_kb} KB · {_csv_rows:,} منتج)",
                    data=_fout.read(), file_name="competitors_latest.csv",
                    mime="text/csv", key="sc_download_csv", use_container_width=True,
                )
        with _go_col:
            if st.button("🚀 تحليل شامل", key="sc_go_match", type="primary", use_container_width=True):
                st.session_state._nav_pending = "📊 لوحة التحكم"
                st.session_state["_use_auto_scraper"] = True
                st.session_state.results = None
                st.session_state.analysis_df = None
                st.session_state.last_audit_stats = None
                st.session_state.nav_flash = "🤖 تم تفعيل البيانات الآلية"
                st.rerun()

    # ── Auto-Analysis Trigger (fires ONCE per completed scrape) ──────────
    if (
        _phase in ("completed", "partial")
        and not _is_alive
        and _rows > 0
        and _finished
        and st.session_state.get("_sc_auto_triggered_job") != _finished
        and not st.session_state.get("job_running", False)
    ):
        st.session_state["_sc_auto_triggered_job"] = _finished
        st.success(f"🤖 الكشط اكتمل — {_rows:,} منتج. جاري التحليل...")
        st.session_state["_nav_pending"] = "📊 لوحة التحكم"
        st.session_state["_use_auto_scraper"] = True
        st.session_state["_sc_auto_analysis_pending"] = True
        st.session_state["nav_flash"] = f"🤖 اكتمل الكشط ({_rows:,} منتج)"
        st.rerun()

    # ── Bootstrap: if no scraper running & products missing prices ──
    if (
        not _is_alive
        and _sp_no_price > 50
        and not st.session_state.get("job_running", False)
    ):
        st.warning(f"⚠️ يوجد {_sp_no_price:,} منتج بدون سعر")
        if st.button("🚀 ابدأ الفحص", key="auto_bootstrap_btn"):
            try:
                import asyncio as _aio
                from engines.scraper_v30_advanced import run_advanced_price_scraping

                def _run_auto_scraper():
                    loop = _aio.new_event_loop()
                    _aio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(run_advanced_price_scraping(
                            store_filter="", limit=min(_sp_no_price, 500),
                        ))
                    finally:
                        loop.close()

                import threading
                _t = threading.Thread(target=_run_auto_scraper, daemon=True)
                _t.start()
                st.toast("⏳ جاري العمل في الخلفية...")
            except Exception as _auto_err:
                st.caption(f"Auto-Bootstrap: {_auto_err}")

elif page == "⚙️ الإعدادات":
    st.header("⚙️ الإعدادات")
    db_log("settings", "view")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["🔑 المفاتيح", "⚙️ المطابقة", "📋 قرارات المنتجات", "📜 السجل الكامل"]
    )

    with tab1:
        # ── الحالة الحالية ────────────────────────────────────────────────
        st.success(
            "✅ **مسار AI جاهز** (Gemini و/أو OpenRouter و/أو Cohere)"
            if ANY_AI_PROVIDER_CONFIGURED
            else "❌ **لا يوجد أي مزود** — أضف مفتاحاً على الأقل"
        )
        gemini_s = f"✅ {len(GEMINI_API_KEYS)} مفتاح" if GEMINI_API_KEYS else "❌ لا توجد مفاتيح"
        or_s     = "✅ مفعل" if OPENROUTER_API_KEY else "❌ غير موجود"
        co_s     = "✅ مفعل" if COHERE_API_KEY else "❌ غير موجود"
        # صندوق واحد بدل 5 صناديق منفصلة (تقليل التكدّس البصري)
        st.info(
            f"**Gemini API:** {gemini_s}  \n"
            f"**OpenRouter:** {or_s}  \n"
            f"**Cohere:** {co_s}  \n"
            f"**Webhook أسعار:** {'✅' if WEBHOOK_UPDATE_PRICES else '❌'}  \n"
            f"**Webhook منتجات:** {'✅' if WEBHOOK_NEW_PRODUCTS else '❌'}"
        )

        st.markdown("---")

        # ── تشخيص شامل ───────────────────────────────────────────────────
        st.subheader("🔬 تشخيص AI")
        st.caption("يختبر الاتصال الفعلي بكل مزود ويُظهر الخطأ الحقيقي")

        if st.button("🔬 تشخيص شامل لجميع المزودين", type="primary", key="ai_diag_all_providers"):
            with st.spinner("يختبر الاتصال بـ Gemini, OpenRouter, Cohere..."):
                from engines.ai_engine import diagnose_ai_providers
                diag = diagnose_ai_providers()

            # ── نتائج Gemini ──────────────────────────────────────────────
            st.markdown("**Gemini API:**")
            any_gemini_ok = False
            for g in diag.get("gemini", []):
                status = g["status"]
                if "✅" in status:
                    st.success(f"مفتاح {g['key']}: {status}")
                    any_gemini_ok = True
                elif "⚠️" in status:
                    st.warning(f"مفتاح {g['key']}: {status}")
                else:
                    st.error(f"مفتاح {g['key']}: {status}")
                _gd = (g.get("detail") or "").strip()
                if _gd and ("❌" in status or "⚠️" in status):
                    st.caption(f"تفاصيل API: {_gd[:500]}")

            # ── نتائج OpenRouter ──────────────────────────────────────────
            or_res = diag.get("openrouter","")
            st.markdown("**OpenRouter:**")
            if "✅" in or_res: st.success(or_res)
            elif "⚠️" in or_res: st.warning(or_res)
            else: st.error(or_res)

            # ── نتائج Cohere ──────────────────────────────────────────────
            co_res = diag.get("cohere","")
            st.markdown("**Cohere:**")
            if "✅" in co_res: st.success(co_res)
            elif "⚠️" in co_res: st.warning(co_res)
            else: st.error(co_res)

            # ── تحليل وتوصية ─────────────────────────────────────────────
            or_ok = "✅" in or_res
            co_ok = "✅" in co_res

            _recs = diag.get("recommendations") or []
            if _recs:
                st.markdown("**💡 توصيات تلقائية (حسب نتيجة التشخيص)**")
                for _r in _recs:
                    st.info(_r)

            st.markdown("---")
            if any_gemini_ok or or_ok or co_ok:
                working = []
                if any_gemini_ok: working.append("Gemini")
                if or_ok: working.append("OpenRouter")
                if co_ok: working.append("Cohere")
                st.success(f"✅ AI يعمل عبر: {' + '.join(working)}")
            else:
                st.error("❌ جميع المزودين فاشلون")
                # تحليل السبب
                _all_errs = [g["status"] for g in diag.get("gemini",[]) if "❌" in g.get("status","")]
                if any("اتصال" in e or "ConnectionError" in e or "Pool" in e for e in _all_errs + [or_res, co_res]):
                    st.warning("""
**🔴 السبب المحتمل: Streamlit Cloud يحجب الطلبات الخارجية**

الحل: في صفحة تطبيقك على Streamlit Cloud:
1. اذهب إلى ⚙️ Settings → General
2. ابحث عن **"Network"** أو **"Egress"**
3. تأكد أن Outbound connections مسموح بها

أو جرب نشر التطبيق على **Railway** بدلاً من Streamlit Cloud.
                    """)
                elif any("403" in e or "IP" in e for e in _all_errs):
                    st.warning("🔴 مفاتيح Gemini محظورة من IP هذا الخادم — جرب OpenRouter")
                elif any("401" in e for e in _all_errs + [or_res, co_res]):
                    st.warning("🔴 مفتاح غير صحيح — تحقق من المفاتيح في Secrets")

        st.markdown("---")

        # ── سجل الأخطاء الأخيرة ──────────────────────────────────────────
        st.subheader("📋 آخر أخطاء AI")
        from engines.ai_engine import get_last_errors
        errs = get_last_errors()
        if errs:
            for e in errs:
                st.code(e, language=None)
        else:
            st.caption("لا أخطاء مسجلة بعد — جرب أي زر AI ثم ارجع هنا")

        st.markdown("---")

        # ── اختبار سريع ──────────────────────────────────────────────────
        if st.button("🧪 اختبار سريع", key="ai_quick_test"):
            with st.spinner("يتصل بـ AI..."):
                r = call_ai("أجب بكلمة واحدة فقط: يعمل", "general")
            if r["success"]:
                st.success(f"✅ AI يعمل عبر {r['source']}: {r['response'][:80]}")
            else:
                st.error("❌ فشل — اضغط 'تشخيص شامل' لمعرفة السبب الدقيق")
                from engines.ai_engine import get_last_errors
                for e in get_last_errors()[:5]:
                    st.code(e, language=None)

    with tab2:
        # صندوق واحد بدل 3 (تقليل التكدّس البصري)
        st.info(
            f"**حد التطابق الأدنى:** {MATCH_THRESHOLD}%  \n"
            f"**حد التطابق العالي:** {HIGH_CONFIDENCE}%  \n"
            f"**هامش فرق السعر:** {PRICE_TOLERANCE} ر.س"
        )

    with tab3:
        decisions = get_decisions(limit=30)
        if decisions:
            df_dec = pd.DataFrame(decisions)
            st.dataframe(df_dec[["timestamp","product_name","old_status",
                                  "new_status","reason","competitor"]].rename(columns={
                "timestamp":"التاريخ","product_name":"المنتج",
                "old_status":"من","new_status":"إلى",
                "reason":"السبب","competitor":"المنافس"
            }).head(200), use_container_width=True)
        else:
            st.info("لا توجد قرارات مسجلة")

    with tab4:
        db_log("settings", "full_log")
        st.caption("سجل التحليلات، تتبع الأسعار، وأحداث التنقل — مدمج مع الإعدادات")
        log_t1, log_t2, log_t3 = st.tabs(["📊 التحليلات", "💰 تغييرات الأسعار", "📝 الأحداث"])

        with log_t1:
            history = get_analysis_history(20)
            if history:
                df_h = pd.DataFrame(history)
                st.dataframe(df_h[["timestamp","our_file","comp_file",
                                    "total_products","matched","missing"]].rename(columns={
                    "timestamp":"التاريخ","our_file":"ملف منتجاتنا",
                    "comp_file":"ملف المنافس","total_products":"الإجمالي",
                    "matched":"متطابق","missing":"مفقود"
                }).head(200), use_container_width=True)
            else:
                st.info("لا يوجد تاريخ")

        with log_t2:
            days = st.slider("آخر X يوم", 1, 30, 7, key="settings_price_changes_days")
            changes = get_price_changes(days)
            if changes:
                df_c = pd.DataFrame(changes)
                st.dataframe(df_c.rename(columns={
                    "product_name":"المنتج","competitor":"المنافس",
                    "old_price":"السعر السابق","new_price":"السعر الجديد",
                    "price_diff":"التغيير","new_date":"تاريخ التغيير"
                }).head(200), use_container_width=True)
            else:
                st.info(f"لا توجد تغييرات في آخر {days} يوم")

        with log_t3:
            events = get_events(limit=50)
            if events:
                df_e = pd.DataFrame(events)
                st.dataframe(df_e[["timestamp","page","event_type","details"]].rename(columns={
                    "timestamp":"التاريخ","page":"الصفحة",
                    "event_type":"الحدث","details":"التفاصيل"
                }).head(200), use_container_width=True)
            else:
                st.info("لا توجد أحداث")



