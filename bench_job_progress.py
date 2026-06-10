"""قياس أداء get_job_progress: الثقيل (SELECT * + json.loads 71MB) مقابل light.
يعمل على قاعدة بيانات حقيقية مع وظيفة محمّلة فعلياً (ليست جلسة فارغة)."""
import os, sys, time
os.environ.setdefault("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
# data dir غير موجود في الـ worktree — وجّه للقاعدة الحقيقية في المشروع الرئيسي
_real_data = r"C:\Users\Hp\Downloads\32\data"
if os.path.exists(os.path.join(_real_data, "pricing_v18.db")):
    os.environ["DATA_DIR"] = _real_data
sys.path.insert(0, os.path.dirname(__file__))
from utils.db_manager import get_job_progress, DB_PATH
import sqlite3

print("DB_PATH =", DB_PATH)
c = sqlite3.connect(DB_PATH)
row = c.execute(
    "SELECT job_id, length(results_json) FROM job_progress "
    "WHERE results_json IS NOT NULL ORDER BY length(results_json) DESC LIMIT 1"
).fetchone()
c.close()
jid, rlen = row
print(f"job_id={jid}  results_json={rlen/1e6:.1f} MB\n")

def bench(fn, n):
    fn()  # warm
    t = time.perf_counter()
    for _ in range(n):
        fn()
    return (time.perf_counter() - t) / n

N_HEAVY, N_LIGHT = 5, 50
heavy = bench(lambda: get_job_progress(jid), N_HEAVY)
light = bench(lambda: get_job_progress(jid, light=True), N_LIGHT)

print(f"HEAVY get_job_progress(jid)            : {heavy*1000:8.1f} ms/call")
print(f"LIGHT get_job_progress(jid, light=True): {light*1000:8.1f} ms/call")
print(f"تحسّن: ×{heavy/light:.0f}  (وفّر {(heavy-light)*1000:.0f} ms لكل استدعاء)")
