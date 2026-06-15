# مهووس — نظام التسعير الذكي (دليل المشروع للمساعد)

> هذا الملف يُحمَّل تلقائياً في كل جلسة. **اقرأه أولاً.** الخطة التفصيلية وحالة التقدّم في `PROJECT_PLAN.md`.

## ما هو المشروع
تطبيق **Streamlit** لمتجر عطور «مهووس»: يكشط أسعار المنافسين، يقارنها بكتالوجنا، يصنّف
(🔴 أعلى / 🟢 أقل / ✅ موافق / 🔍 مفقود / ⚠️ مراجعة / ⚪ مستبعد)، ويصدّر المفقودات لقالب سلة.
يُنشر على **Railway** من GitHub (`origin/master`، repo: `nwtsrash-lgtm/mahwous-scraper-32`).

## ⛔ بروتوكول صارم (تجاهلُه سبق أن كسر التطبيق على Railway)
1. **ملف واحد لكل commit.** لا تعدّل عدة ملفات في commit واحد.
2. **لا ملفات كود جديدة** إلا لضرورة قصوى (محاولة سابقة بإنشاء module + تعديل 5 ملفات كسرت النشر). الإصلاح داخل الملفات الموجودة.
3. **لا إعادة هيكلة ولا نقل كود** بين الملفات.
4. **تحقّق قبل كل commit:** `python -c "import ast; ast.parse(open('app.py',encoding='utf-8').read())"` ثم `python -c "import app"` بلا أخطاء (تجاهل تحذيرات Streamlit/Railway).
5. **المستخدم وحده يدفع (push) ويتحقق على Railway** بعد كل commit. **لا تدفع أنت.** انتظر تأكيده «يعمل» قبل التغيير التالي.
6. **لا فقدان بيانات أبداً.** عند الشك في تصنيف منتج → «مراجعة» (يبقى ظاهراً)، لا حذف ولا إخفاء صامت.
7. **رسائل commit بالعربية** + تنتهي بسطر `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
8. **لا تبدأ التعديل قبل عرض تشخيص المرحلة** والحصول على موافقة المستخدم.

## 🔧 حقائق تقنية (لا تُعِد اكتشافها — مكلف ووقت ضائع)
- الكود في المجلد المتداخل `mahwous-scraper-32-master/`. **`app.py` ضخم (~8,600 سطر).** فيه توجيه الصفحات `if/elif page ==`.
- **قاعدة بيانات واحدة: `data/pricing_v18.db` (~265MB)** — تحوي: `competitor_products_store` (~115K صف، 19 متجراً)، `our_catalog` (كتالوجنا)، `job_progress`، `hidden_products`، `processed_products`، `force_links`. المسار عبر `DATA_DIR` (Railway volume = `/data`). `utils/db_manager.py` يزامن GCS عند الاستيراد.
- كتالوجنا أيضاً في **`data/our_catalog_saved.csv` (~7,863 منتج)** — هذا ما يستخدمه قسم المفقودات (لا `our_catalog` في DB دائماً).
- **التطبيع:** `engine.normalize_name` (280+ مرادف عربي↔إنجليزي). **`utils/missing_match.miss_bare` = المُطبِّع الجيد** (يزيل عطر/او دو بارفيوم/مل/للجنسين + هيكل عظمي للنسخ الإملائية كاشريل↔كاشاريل). **استخدم miss_bare دائماً للمطابقة** — لا `_norm_dup_text` ولا تطبيع ضعيف (يسبب إيجابيات كاذبة جماعية).
- **مسار المفقودات الحيّ:** `app.py::_compute_missing_from_store` → مرشّحون من `engines/competitor_intelligence.py::CompetitorIntelligence.find_missing_products` ثم حجب بالكلمات+الهيكل العظمي ثم `utils/missing_match.classify` (ثلاثي: owned تُخفى / review تبقى ظاهرة / green مفقود مؤكد). العتبات في `config.py` (`MISSING_CONFIRMED_THRESHOLD=82`, `MISSING_REVIEW_THRESHOLD=70`, `MISSING_BARRIER_THRESHOLD=85`).
- **تصدير سلة:** `utils/salla_shamel_export.py::export_to_salla_shamel` يُنتج **40 عمود مطابق لقالب سلة** + تجهيز مهووس (اسم/وصف HTML/ماركة/تصنيف هرمي/«منتج جاهز») + بوابة جودة. `verify_truly_missing` = تحقق عدم التكرار مقابل الكتالوج. الأساسي في الواجهة: زر **«🚀 تجهيز سريع — المؤكدة»**. قالب سلة الرسمي عند المستخدم: `Downloads/Salla Products Template (1).xlsx` (40 عمود + ورقة تصنيفات/أنواع/ماركات).
- **المراقبة:** `observability/ledger.py` — فحص الثابت `ingested == confirmed+missing+rejected+...`. استخدمه للتأكد أن لا صفوف تُفقد صامتةً.
- **الاختبارات:** `tests/test_missing_accuracy.py` · `tests/test_ledger_invariant.py` · `tests/baseline_missing.py` (قياس دقة المفقودات على البيانات الحقيقية).

## ⚠️ دروس مؤلمة (لا تُكرّرها)
- **نداء AI متزامن عند الإقلاع** (`_auto_resolve_review`) = تعليق/شاشة سوداء على Railway. AI **بزر يدوي فقط**، بحدّ أقصى للعدد لكل ضغطة، لا في مسار الرسم/الإقلاع.
- **مطابقة token_set على أسماء بلا تطبيع جيد** = مئات المنتجات المختلفة تُصنّف «مكرر» (كلها ≈ «هوت بارفيوم للنساء» 89%). استخدم `miss_bare`.
- **تحميل DB كاملة في الذاكرة على Railway المحدود** = OOM. عالج بدفعات (chunks) + فهارس + cache. **هذا أكبر خطر عند حجم مئات الآلاف من المنتجات.**
- **«الإرجاع الذكي»** كان يعيد المنتج المُعالَج لقسمه. مُطفأ افتراضياً عبر `_REEVAL_PROCESSED_ON_PRICE_DROP=False`.

## 🤖 قواعد الذكاء الاصطناعي
- AI **مساعد لا حَكَم نهائي.** عند فشله/غموضه → «مراجعة» (لا حذف). **خزّن نتائجه (cache)** لتفادي إعادة الطلب والتكلفة. **إنسان في الحلقة قبل الإضافة** للمتجر (فعل لا رجعة فيه).
- مزوّدات: Gemini ثم OpenRouter ثم Cohere (تدوير مفاتيح في `engine._ai_batch`). أي مزوّد يكفي.
