"""
pages/competitor_intelligence_page.py — واجهة ذكاء المنافسين v31
================================================================
5 تبويبات: كل المنتجات | الجديد | الأكثر مبيعاً | غير متوفر | مقارنة المتاجر
"""
import streamlit as st
import pandas as pd
import os
import time
import logging

log = logging.getLogger(__name__)
_CI = None


def _get_ci():
    global _CI
    if _CI is None:
        try:
            from engines.competitor_intelligence import CompetitorIntelligence
            db_path = os.path.join(os.environ.get("DATA_DIR", "data"), "pricing_v18.db")
            _CI = CompetitorIntelligence(db_path=db_path)
        except Exception as e:
            log.error("فشل تحميل CompetitorIntelligence: %s", e)
            return None
    return _CI


def _fmt(p):
    try:
        return f"{float(p):,.0f} ر.س"
    except Exception:
        return "—"


def _render_filters(ci, key_prefix="ci"):
    f1, f2, f3, f4 = st.columns(4)
    filters = {}
    with f1:
        comps = ["الكل"] + (ci.get_available_competitors() or [])
        sel = st.selectbox("🏪 المتجر", comps, key=f"{key_prefix}_comp")
        if sel != "الكل":
            filters["competitor"] = sel
    with f2:
        brands = ["الكل"] + (ci.get_available_brands()[:50] or [])
        sel = st.selectbox("🏷️ الماركة", brands, key=f"{key_prefix}_brand")
        if sel != "الكل":
            filters["brand"] = sel
    with f3:
        search = st.text_input("🔍 بحث", key=f"{key_prefix}_search")
        if search:
            filters["search"] = search
    with f4:
        sort_map = {"الأحدث": "newest", "سعر ↑": "price_asc", "سعر ↓": "price_desc", "الأكثر تقييماً": "rating"}
        sel = st.selectbox("📊 ترتيب", list(sort_map.keys()), key=f"{key_prefix}_sort")
        filters["sort_by"] = sort_map[sel]
    return filters


def render_competitor_intelligence():
    """النقطة الرئيسية — تُستدعى من app.py"""
    st.markdown("## 🧠 ذكاء المنافسين")
    st.caption("تحليل شامل لمنتجات المنافسين — بيانات مباشرة من قاعدة البيانات")

    ci = _get_ci()
    if ci is None:
        st.error("⚠️ فشل تحميل محرك ذكاء المنافسين. تأكد من وجود قاعدة البيانات.")
        return

    # ── إحصائيات ──
    try:
        stats = ci.get_stats()
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("📦 المنتجات", f"{stats.get('total_products', 0):,}")
        m2.metric("🏪 المتاجر", f"{stats.get('total_competitors', 0)}")
        m3.metric("🏷️ الماركات", f"{stats.get('total_brands', 0)}")
        m4.metric("📉 خصومات", f"{stats.get('products_on_sale', 0):,}")
        m5.metric("🆕 جديد (7 أيام)", f"{stats.get('new_7d', 0):,}")
    except Exception as e:
        st.warning(f"فشل تحميل الإحصائيات: {e}")

    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 كل المنتجات", "🆕 جديد عند المنافسين",
        "🔥 الأكثر مبيعاً", "❌ غير متوفر لدينا", "📊 مقارنة المتاجر",
    ])

    # ══ Tab 1: كل المنتجات ══
    with tab1:
        st.markdown("### 📋 جميع منتجات المنافسين")
        filters = _render_filters(ci, "tab1")
        page = st.number_input("الصفحة", min_value=1, value=1, step=1, key="tab1_page")
        try:
            products, total = ci.get_products_page(page=page-1, per_page=25, filters=filters)
            total_pages = max(1, (total + 24) // 25)
            st.caption(f"📊 {total:,} منتج — صفحة {page}/{total_pages}")
            if products:
                df = pd.DataFrame(products)
                cols = [c for c in ["product_name","price","brand","competitor","category","discount_pct"] if c in df.columns]
                rename = {"product_name":"المنتج","price":"السعر","brand":"الماركة","competitor":"المتجر","category":"التصنيف","discount_pct":"الخصم%"}
                st.dataframe(df[cols].rename(columns=rename), use_container_width=True, height=min(700, 40+len(products)*35))
            else:
                st.info("لا توجد منتجات مطابقة للفلاتر")
        except Exception as e:
            st.error(f"خطأ: {e}")

    # ══ Tab 2: الجديد ══
    with tab2:
        st.markdown("### 🆕 منتجات جديدة عند المنافسين")
        dc, fc = st.columns([1, 3])
        with dc:
            days = st.selectbox("الفترة", [3, 7, 14, 30], index=1, key="new_days")
        with fc:
            nf = _render_filters(ci, "tab2")
        page2 = st.number_input("الصفحة", min_value=1, value=1, step=1, key="tab2_page")
        try:
            products, total = ci.get_new_products(days=days, page=page2-1, per_page=25, filters=nf)
            st.caption(f"🆕 {total:,} منتج جديد في آخر {days} أيام")
            if products:
                df = pd.DataFrame(products)
                cols = [c for c in ["product_name","price","brand","competitor","first_seen_at"] if c in df.columns]
                rename = {"product_name":"المنتج","price":"السعر","brand":"الماركة","competitor":"المتجر","first_seen_at":"تاريخ الإضافة"}
                st.dataframe(df[cols].rename(columns=rename), use_container_width=True, height=min(700, 40+len(products)*35))
            else:
                st.info(f"لا توجد منتجات جديدة في آخر {days} أيام")
        except Exception as e:
            st.error(f"خطأ: {e}")

    # ══ Tab 3: الأكثر مبيعاً ══
    with tab3:
        st.markdown("### 🔥 الأكثر مبيعاً / أعلى خصم")
        bf = _render_filters(ci, "tab3")
        page3 = st.number_input("الصفحة", min_value=1, value=1, step=1, key="tab3_page")
        try:
            products, total = ci.get_best_sellers(page=page3-1, per_page=25, filters=bf)
            st.caption(f"🔥 {total:,} منتج مميز")
            if products:
                df = pd.DataFrame(products)
                cols = [c for c in ["product_name","price","brand","competitor","rating_count","discount_pct"] if c in df.columns]
                rename = {"product_name":"المنتج","price":"السعر","brand":"الماركة","competitor":"المتجر","rating_count":"التقييمات","discount_pct":"الخصم%"}
                st.dataframe(df[cols].rename(columns=rename), use_container_width=True, height=min(700, 40+len(products)*35))
            else:
                st.info("لا توجد بيانات تقييم أو خصومات")
        except Exception as e:
            st.error(f"خطأ: {e}")

    # ══ Tab 4: غير متوفر لدينا ══
    with tab4:
        st.markdown("### ❌ منتجات غير متوفرة لدينا")
        st.caption("كشف بالبصمة الذكية — بدون تكرار — مجمّعة من كل المنافسين")

        our_df = st.session_state.get("our_df")
        if our_df is None or (isinstance(our_df, pd.DataFrame) and our_df.empty):
            st.warning("⚠️ يرجى رفع كتالوج منتجاتنا أولاً (من لوحة التحكم)")
            uploaded = st.file_uploader("📂 رفع كتالوج منتجاتنا", type=["csv", "xlsx"], key="ci_catalog")
            if uploaded:
                try:
                    if uploaded.name.endswith(".xlsx"):
                        our_df = pd.read_excel(uploaded)
                    else:
                        our_df = pd.read_csv(uploaded, encoding="utf-8-sig")
                    st.session_state.our_df = our_df
                    st.success(f"✅ تم تحميل {len(our_df):,} منتج")
                    st.rerun()
                except Exception as e:
                    st.error(f"خطأ: {e}")
        else:
            mf = _render_filters(ci, "tab4")
            page4 = st.number_input("الصفحة", min_value=1, value=1, step=1, key="tab4_page")

            with st.spinner("🔍 تحليل المنتجات المفقودة..."):
                try:
                    t0 = time.time()
                    products, total = ci.find_missing_products(our_df, page=page4-1, per_page=25, filters=mf)
                    elapsed = time.time() - t0
                    st.caption(f"❌ {total:,} منتج غير متوفر — ({elapsed:.1f}s)")

                    if products:
                        for i, p in enumerate(products):
                            with st.container():
                                c1, c2, c3 = st.columns([3, 1, 1])
                                with c1:
                                    name = p.get("product_name", "—")
                                    brand = p.get("brand", "")
                                    st.markdown(f"**{name[:100]}**")
                                    parts = []
                                    if brand:
                                        parts.append(f"🏷️ {brand}")
                                    parts.append(f"💰 أقل: {_fmt(p.get('min_price', 0))}")
                                    parts.append(f"📊 عند {p.get('competitor_count', 1)} منافسين")
                                    parts.append(f"💵 المقترح: {_fmt(p.get('suggested_price', 0))}")
                                    st.caption(" | ".join(parts))
                                with c2:
                                    if st.button("🤖 تجهيز", key=f"prep_{i}_{page4}"):
                                        with st.spinner("جاري التجهيز..."):
                                            try:
                                                prepared = ci.prepare_for_make(p)
                                                st.session_state[f"prepared_{i}"] = prepared
                                                st.success("✅ تم التجهيز")
                                            except Exception as e:
                                                st.error(f"خطأ: {e}")
                                with c3:
                                    if st.button("📤 Make", key=f"send_{i}_{page4}"):
                                        prep = st.session_state.get(f"prepared_{i}")
                                        if prep:
                                            try:
                                                from utils.make_helper import send_new_products
                                                result = send_new_products([prep])
                                                if result.get("success"):
                                                    st.success("✅ تم الإرسال")
                                                else:
                                                    st.error(f"فشل: {result.get('error', '')}")
                                            except Exception as e:
                                                st.error(f"خطأ: {e}")
                                        else:
                                            st.warning("جهّز المنتج أولاً")
                                st.divider()
                    else:
                        st.success("🎉 كل منتجات المنافسين متوفرة لديك!")
                except Exception as e:
                    st.error(f"خطأ في تحليل المفقود: {e}")

    # ══ Tab 5: مقارنة المتاجر ══
    with tab5:
        st.markdown("### 📊 مقارنة المتاجر المنافسة")
        try:
            stores = ci.compare_stores()
            if stores:
                df = pd.DataFrame(stores)
                rename = {"competitor":"المتجر","total_products":"المنتجات","avg_price":"متوسط السعر","min_price":"أقل سعر","max_price":"أعلى سعر","on_sale":"خصومات","new_7d":"جديد (7 أيام)"}
                cols = [c for c in rename if c in df.columns]
                st.dataframe(df[cols].rename(columns=rename), use_container_width=True, hide_index=True)
                if "total_products" in df.columns and "competitor" in df.columns:
                    st.bar_chart(df.set_index("competitor")["total_products"], use_container_width=True)
            else:
                st.info("لا توجد بيانات متاجر")
        except Exception as e:
            st.error(f"خطأ: {e}")
