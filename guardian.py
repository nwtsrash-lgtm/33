"""
guardian.py - حارس مهووس الذكي 🛡️
يراقب التطبيق ويعيد تشغيله تلقائياً عند التوقف
يمنع الخمول ويحفظ البيانات باستمرار
"""
import subprocess
import time
import sys
import os
import shutil
import signal
import webbrowser
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Fix Windows console encoding
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except:
        pass

# ─── إعدادات ───
APP_FILE = "app.py"
PORT = 8501
BACKUP_INTERVAL = 300        # نسخ احتياطي كل 5 دقائق
KEEPALIVE_INTERVAL = 60      # نبض كل 60 ثانية
RESTART_DELAY = 3            # انتظار 3 ثوانٍ قبل إعادة التشغيل
MAX_CRASHES = 100            # أقصى عدد إعادات تشغيل
DATA_DIR = Path(__file__).parent / "data"
BACKUP_DIR = Path(__file__).parent / "data_backup"

# ─── لوق ───
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [حارس] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            Path(__file__).parent / "guardian.log",
            encoding="utf-8"
        )
    ]
)
log = logging.getLogger("guardian")


def backup_data():
    """نسخ احتياطي تلقائي لمجلد البيانات"""
    if not DATA_DIR.exists():
        return
    try:
        BACKUP_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # نسخ قاعدة البيانات الرئيسية
        db_file = DATA_DIR / "pricing_v18.db"
        if db_file.exists():
            backup_file = BACKUP_DIR / f"pricing_v18_backup_{timestamp}.db"
            # احتفظ بآخر 3 نسخ فقط
            old_backups = sorted(BACKUP_DIR.glob("pricing_v18_backup_*.db"))
            for old in old_backups[:-2]:  # احذف ما قبل آخر 2
                try:
                    old.unlink()
                except:
                    pass
            shutil.copy2(db_file, backup_file)
            log.info(f"✅ نسخة احتياطية: {backup_file.name}")
        
        # نسخ الملفات المهمة الأخرى
        for pattern in ["*.json", "*.csv", "*.pkl"]:
            for f in DATA_DIR.glob(pattern):
                try:
                    dest = BACKUP_DIR / f.name
                    shutil.copy2(f, dest)
                except:
                    pass
                    
    except Exception as e:
        log.warning(f"⚠️ خطأ في النسخ الاحتياطي: {e}")


def restore_data():
    """استعادة البيانات من النسخة الاحتياطية إذا فُقدت"""
    if not BACKUP_DIR.exists():
        return
    
    db_file = DATA_DIR / "pricing_v18.db"
    if not db_file.exists() or db_file.stat().st_size == 0:
        # ابحث عن أحدث نسخة
        backups = sorted(BACKUP_DIR.glob("pricing_v18_backup_*.db"))
        if backups:
            latest = backups[-1]
            DATA_DIR.mkdir(exist_ok=True)
            shutil.copy2(latest, db_file)
            log.info(f"🔄 تم استعادة قاعدة البيانات من: {latest.name}")
        
        # استعادة الملفات الأخرى
        for f in BACKUP_DIR.glob("*"):
            if f.name.startswith("pricing_v18_backup"):
                continue
            dest = DATA_DIR / f.name
            if not dest.exists():
                shutil.copy2(f, dest)
                log.info(f"🔄 تم استعادة: {f.name}")


def keepalive_ping():
    """إرسال نبض للتطبيق لمنع الخمول"""
    try:
        import urllib.request
        url = f"http://localhost:{PORT}/_stcore/health"
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "MahwousGuardian/1.0")
        urllib.request.urlopen(req, timeout=10)
        return True
    except:
        try:
            import urllib.request
            url = f"http://localhost:{PORT}"
            urllib.request.urlopen(url, timeout=10)
            return True
        except:
            return False


def is_app_running():
    """تحقق إذا التطبيق يعمل"""
    return keepalive_ping()


def kill_port(port):
    """إيقاف أي عملية تستخدم البورت"""
    try:
        result = subprocess.run(
            f'netstat -ano | findstr :{port}',
            shell=True, capture_output=True, text=True
        )
        for line in result.stdout.strip().split('\n'):
            if 'LISTENING' in line:
                pid = line.strip().split()[-1]
                subprocess.run(f'taskkill /F /PID {pid}', shell=True,
                             capture_output=True)
                log.info(f"🔪 تم إيقاف العملية على البورت {port} (PID: {pid})")
    except:
        pass


def start_app():
    """تشغيل تطبيق Streamlit"""
    kill_port(PORT)
    time.sleep(1)
    
    cmd = [
        sys.executable, "-m", "streamlit", "run", APP_FILE,
        "--server.headless", "true",
        "--server.port", str(PORT),
        "--server.fileWatcherType", "none",
        "--server.runOnSave", "false",
        "--browser.gatherUsageStats", "false",
    ]
    
    process = subprocess.Popen(
        cmd,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace"
    )
    
    log.info(f"🚀 تم تشغيل التطبيق (PID: {process.pid})")
    return process


def open_browser():
    """فتح المتصفح تلقائياً"""
    time.sleep(5)
    try:
        webbrowser.open(f"http://localhost:{PORT}")
        log.info("🌐 تم فتح المتصفح")
    except:
        pass


def prevent_sleep():
    """منع Windows من الدخول في وضع السكون"""
    try:
        import ctypes
        # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000002 | 0x00000001)
        log.info("💡 تم منع وضع السكون")
    except:
        pass


def main():
    print("""
╔══════════════════════════════════════════════════╗
║     🛡️  حارس مهووس الذكي — Guardian v1.0       ║
║     ─────────────────────────────────────        ║
║     ✅ إعادة تشغيل تلقائي عند التوقف            ║
║     ✅ نسخ احتياطي كل 5 دقائق                   ║
║     ✅ منع الخمول والسكون                        ║
║     ✅ فتح المتصفح تلقائياً                      ║
╚══════════════════════════════════════════════════╝
    """)
    
    # منع السكون
    prevent_sleep()
    
    # استعادة البيانات إذا فُقدت
    restore_data()
    
    # نسخة احتياطية أولية
    backup_data()
    
    crash_count = 0
    last_backup = time.time()
    last_keepalive = time.time()
    browser_opened = False
    
    while crash_count < MAX_CRASHES:
        log.info(f"🔄 بدء التشغيل (المحاولة #{crash_count + 1})")
        
        process = start_app()
        
        # انتظر بدء التطبيق
        for _ in range(30):
            time.sleep(1)
            if is_app_running():
                break
        
        if is_app_running():
            log.info(f"✅ التطبيق يعمل على:")
            log.info(f"   🖥️  محلي: http://localhost:{PORT}")
            log.info(f"   🌐 شبكة: http://192.168.1.2:{PORT}")
            
            if not browser_opened:
                open_browser()
                browser_opened = True
        
        # حلقة المراقبة
        while True:
            time.sleep(10)
            
            # تحقق من العملية
            if process.poll() is not None:
                log.warning("⚠️ التطبيق توقف! سيتم إعادة التشغيل...")
                crash_count += 1
                break
            
            # نبض لمنع الخمول
            now = time.time()
            if now - last_keepalive >= KEEPALIVE_INTERVAL:
                alive = keepalive_ping()
                last_keepalive = now
                if not alive:
                    log.warning("⚠️ التطبيق لا يستجيب! إعادة تشغيل...")
                    try:
                        process.terminate()
                        process.wait(timeout=10)
                    except:
                        process.kill()
                    crash_count += 1
                    break
            
            # نسخ احتياطي دوري
            if now - last_backup >= BACKUP_INTERVAL:
                backup_data()
                last_backup = now
            
            # إعادة ضبط عداد الأخطاء كل ساعة من التشغيل المستقر
            if crash_count > 0 and now - last_backup > 3600:
                crash_count = 0
        
        # تأخير قبل إعادة التشغيل
        log.info(f"⏳ انتظار {RESTART_DELAY} ثوانٍ قبل إعادة التشغيل...")
        time.sleep(RESTART_DELAY)
        
        # نسخ احتياطي قبل إعادة التشغيل
        backup_data()
    
    log.error(f"❌ تجاوز الحد الأقصى للمحاولات ({MAX_CRASHES})")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("👋 تم إيقاف الحارس يدوياً")
        backup_data()
