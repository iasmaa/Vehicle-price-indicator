import streamlit as st
import pandas as pd
import numpy as np

# إعداد الصفحة وتنسيقها ودعم اللغة العربية
st.set_page_config(page_title="مؤشر السعر العادل للمركبات", page_icon="🚗", layout="centered")

st.markdown("""
<style>
    .stApp {background: #f5f7fb; direction: rtl;}
    [data-testid="stMainBlockContainer"] {max-width: 920px;}
    h1, h2, h3, p, label, [data-testid="stText"] {direction: rtl; text-align: right;}
    div.stButton > button {width: 100%; border-radius: 12px; min-height: 48px; font-weight: 700; background-color: #ff4b4b; color: white;}
    .reportview-container .main .block-container{padding-top: 2rem;}
</style>
""", unsafe_allow_html=True)

st.title("🚗 مؤشر أسعار المركبات التفاعلي")
st.caption("نسخة تجريبية  - أدخل البيانات ثم اضغط على زر التقييم")

# قراءة الملف مع تفعيل الكاش لسرعة التحميل
@st.cache_data
def load_data():
    df = pd.read_excel("Vehicle_Fair_Price_POC.xlsx")
    return df

try:
    df = load_data()
    
    # تجهيز القوائم المنسدلة بناءً على البيانات الفعلية في الملف
    brands = sorted(df['العلامة التجارية'].dropna().unique())
    
    col1, col2 = st.columns(2)
    with col1:
        selected_brand = st.selectbox("العلامة التجارية", brands)
    with col2:
        available_models = sorted(df[df['العلامة التجارية'] == selected_brand]['الموديل'].dropna().unique())
        selected_model = st.selectbox("الموديل", available_models)
        
    col3, col4 = st.columns(2)
    with col3:
        available_years = sorted(df[(df['العلامة التجارية'] == selected_brand) & (df['الموديل'] == selected_model)]['سنة الصنع'].dropna().unique(), reverse=True)
        selected_year = st.selectbox("سنة الصنع", available_years)
    with col4:
        available_trims = sorted(df[(df['العلامة التجارية'] == selected_brand) & (df['الموديل'] == selected_model)]['الفئة'].dropna().unique())
        selected_trim = st.selectbox("الفئة", available_trims)

    col5, col6 = st.columns(2)
    with col5:
        selected_mileage = st.number_input("العداد / الممشى الحالي (كيلومتر)", min_value=0, value=50000, step=5000)
    with col6:
        regions = sorted(df['المنطقة'].dropna().unique())
        selected_region = st.selectbox("المنطقة", regions)

    col7, col8 = st.columns(2)
    with col7:
        selected_owners = st.number_input("عدد الملاك السابقين", min_value=1, max_value=10, value=1)
    with col8:
        proposed_price = st.number_input("السعر المقترح من قبلك (ريال سعودي)", min_value=0, value=30000, step=1000)

    st.markdown("---")

    # زر حساب التقييم السعري
    submit_button = st.button("احسب التقييم السعري")

    # تنفيذ الحساب فقط عند الضغط على الزر
    if submit_button:
        filtered_df = df[
            (df['العلامة التجارية'] == selected_brand) & 
            (df['الموديل'] == selected_model) & 
            (df['سنة الصنع'] == selected_year)
        ]
        
        if not filtered_df.empty:
            base_avg = filtered_df['سعر المبايعة الفعلي'].mean()
            
            # موازنة الفئة والممشى والملاك
            trim_df = filtered_df[filtered_df['الفئة'] == selected_trim]
            if not trim_df.empty:
                base_avg = trim_df['سعر المبايعة الفعلي'].mean()
                
            avg_mileage = filtered_df['العداد / الممشى'].mean() if 'العداد / الممشى' in filtered_df.columns else 80000
            if selected_mileage < avg_mileage:
                base_avg *= 1.05
            elif selected_mileage > avg_mileage:
                base_avg *= 0.95
                
            if selected_owners > 2:
                base_avg *= 0.97

            # تحديد النطاق العادل
            low_bound = round(base_avg * 0.92)
            high_bound = round(base_avg * 1.08)
            
            st.subheader("📊 نتيجة التحليل:")
            st.info(f"📍 نطاق السعر العادل لمركبتك هو بين **{low_bound:,} ريال** و **{high_bound:,} ريال**.")
            
            if low_bound <= proposed_price <= high_bound:
                st.success("✅ السعر المقترح عادل وضمن نطاق السوق الحقيقي.")
            elif proposed_price > high_bound:
                diff_pct = round(((proposed_price - base_avg) / base_avg) * 100, 2)
                st.warning(f"⚠️ السعر المقترح أعلى من سعر السوق العادل بنسبة {diff_pct}%.")
            else:
                diff_pct = round(((base_avg - proposed_price) / base_avg) * 100, 2)
                st.error(f"📉 السعر المقترح أقل من سعر السوق العادل بنسبة {diff_pct}%.")
                
        else:
            st.warning("⚠️ لا توجد بيانات كافية لهذه المركبة بالتحديد في الملف المرفق، يرجى تجربة خيارات أخرى.")

except Exception as e:
    st.error(f"حدث خطأ أثناء تحميل البيانات أو الحساب: {e}")
