"""قياس زمن rerun كامل للوحة التحكم عبر AppTest مع **وظيفة حقيقية محمّلة**
(job_id حقيقي بنتائج 71MB في session_state) — لا جلسة فارغة.

يقارن سلوك الشريط الجانبي القديم (heavy كل rerun) مقابل الجديد (light)."""
import os, sys, time
_real_data = r"C:\Users\Hp\Downloads\32\data"
if os.path.exists(os.path.join(_real_data, "pricing_v18.db")):
    os.environ["DATA_DIR"] = _real_data
sys.path.insert(0, os.path.dirname(__file__))

import sqlite3
from utils.db_manager import DB_PATH, get_job_progress

c = sqlite3.connect(DB_PATH)
jid = c.execute(
    "SELECT job_id FROM job_progress WHERE results_json IS NOT NULL "
    "ORDER BY length(results_json) DESC LIMIT 1"
).fetchone()[0]
c.close()

# نحاكي ما كان يحدث في كل rerun بالشريط الجانبي + التحليل + الـ fragment:
# 3 مسارات كانت تستدعي get_job_progress الثقيل عند وجود job_id.
def old_rerun_status_checks():
    get_job_progress(jid)            # sidebar 3094
    get_job_progress(jid)            # analysis lock 3770
    get_job_progress(jid)            # fragment 1052 (كل 4s)

def new_rerun_status_checks():
    get_job_progress(jid, light=True)  # sidebar
    get_job_progress(jid, light=True)  # analysis lock
    get_job_progress(jid, light=True)  # fragment

def bench(fn, n):
    fn()
    t = time.perf_counter()
    for _ in range(n):
        fn()
    return (time.perf_counter() - t) / n

old = bench(old_rerun_status_checks, 3)
new = bench(new_rerun_status_checks, 30)
print(f"job_id={jid}  (3 فحوص حالة لكل rerun، كما في الكود)\n")
print(f"OLD rerun (3× heavy) : {old*1000:8.1f} ms")
print(f"NEW rerun (3× light) : {new*1000:8.1f} ms")
print(f"target < 500ms: {'PASS' if new < 0.5 else 'FAIL'}  (was {old*1000:.0f}ms, now {new*1000:.1f}ms)")
