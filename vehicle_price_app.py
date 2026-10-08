from io import BytesIO
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="مؤشر السعر العادل للمركبات", page_icon="🚘", layout="centered")
st.markdown("""<style>
.stApp {background: #f5f7fb; direction: rtl;}
[data-testid="stMainBlockContainer"] {max-width: 920px;}
h1,h2,h3,p,label,[data-testid="stAlert"] {direction:rtl; text-align:right;}
[data-testid="stNumberInput"] input {direction:ltr; text-align:right;}
.stButton button {width:100%; border-radius:12px; min-height:48px; font-weight:700;}
[data-testid="stAlert"] {border-radius:14px;}
</style>""", unsafe_allow_html=True)

REQUIRED = ["العلامة التجارية", "الموديل", "سنة الصنع", "الفئة", "العداد / الممشى", "المنطقة", "عدد الملاك السابقين", "سعر المبايعة الفعلي"]

@st.cache_data(show_spinner=False)
def load_data(content):
    df = pd.read_excel(BytesIO(content), sheet_name="Transaction_Data", engine="openpyxl")
    df.columns = df.columns.astype(str).str.strip()
    missing = set(REQUIRED) - set(df.columns)
    if missing:
        raise ValueError("أعمدة مفقودة: " + "، ".join(sorted(missing)))
    df = df.drop(columns=["رقم العملية"], errors="ignore").copy()
    for c in ["العلامة التجارية", "الموديل", "الفئة", "المنطقة"]:
        df[c] = df[c].astype("string").str.strip().replace("", pd.NA)
    for c in ["سنة الصنع", "العداد / الممشى", "عدد الملاك السابقين", "سعر المبايعة الفعلي"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=REQUIRED)
    numeric = ["سنة الصنع", "العداد / الممشى", "عدد الملاك السابقين", "سعر المبايعة الفعلي"]
    df = df[np.isfinite(df[numeric]).all(axis=1)]
    df = df[(df["سعر المبايعة الفعلي"] > 0) & (df["العداد / الممشى"] >= 0) & (df["عدد الملاك السابقين"] >= 0)]
    for c in ["سنة الصنع", "عدد الملاك السابقين"]:
        df = df[df[c] % 1 == 0]
        df[c] = df[c].astype(int)
    if df.empty:
        raise ValueError("لا توجد سجلات صالحة للتقييم.")
    return df

def evaluate(df, brand, model, year, trim, mileage, region, owners, proposed):
    base = df[(df["العلامة التجارية"] == brand) & (df["الموديل"] == model) & (df["سنة الصنع"] == year)]
    if base.empty:
        raise ValueError("لا توجد مبايعات تطابق العلامة والموديل وسنة الصنع؛ لا يمكن حساب تقييم موثوق.")
    # Same method as the prototype: mileage ±20%, owners ±1, exact trim.
    tolerance = mileage * 0.20
    similar = base[(base["الفئة"] == trim) & ((base["العداد / الممشى"] - mileage).abs() <= tolerance) & ((base["عدد الملاك السابقين"] - owners).abs() <= 1)].copy()
    fallback = similar.empty
    if fallback:
        fair = float(base["سعر المبايعة الفعلي"].mean())
        count = len(base)
    else:
        distance = (similar["العداد / الممشى"] - mileage).abs()
        weights = np.exp(-distance / max(tolerance, 1.0)) / (1 + (similar["عدد الملاك السابقين"] - owners).abs())
        # All regions remain included; matching region receives only 2% extra weight.
        weights *= np.where(similar["المنطقة"] == region, 1.02, 1.0)
        fair = float(np.average(similar["سعر المبايعة الفعلي"], weights=weights))
        count = len(similar)
    lower, upper = fair * 0.92, fair * 1.08
    if proposed > upper:
        status = "warning"
        message = f"السعر المقترح أعلى من سعر السوق العادل بنسبة {(proposed / fair - 1) * 100:.2f}%."
    elif proposed < lower:
        status = "warning"
        message = f"السعر المقترح أقل من سعر السوق العادل بنسبة {(1 - proposed / fair) * 100:.2f}%."
    else:
        status = "success"
        message = "السعر المقترح عادل وضمن نطاق السوق الحقيقي."
    return {"mean": fair, "lower": lower, "upper": upper, "status": status, "message": message, "count": count, "fallback": fallback}

st.title("🚘 مؤشر السعر العادل للمركبات")
st.caption("أدخل بيانات مركبتك لتقدير نطاق السعر ومقارنة السعر المقترح.")
st.info("نسخة تجريبية: الملف المرفق يحتوي على بيانات اصطناعية، والنتائج ليست أسعار سوق فعلية أو ضماناً للدقة.")
with st.sidebar:
    st.header("مصدر البيانات")
    uploaded = st.file_uploader("رفع ملف المبايعات (اختياري)", type=["xlsx"])
    st.caption("يُستخدم الملف المرفق افتراضياً، أو ملفك البديل الذي يحتوي على ورقة Transaction_Data والأعمدة المطلوبة.")
try:
    path = Path(__file__).resolve().parent / "Vehicle_Fair_Price_POC.xlsx"
    content = uploaded.getvalue() if uploaded is not None else path.read_bytes()
    df = load_data(content)
except FileNotFoundError:
    st.error("يرجى رفع ملف المبايعات من الشريط الجانبي أو وضعه بجوار كود التطبيق.")
    st.stop()
except Exception as exc:
    st.error(f"تعذر قراءة البيانات: {exc}")
    st.stop()

def choices(frame, column):
    return sorted(frame[column].dropna().unique().tolist())

def preferred(options, value):
    return options.index(value) if value in options else 0

# Outside a form so the cascading dropdowns refresh immediately.
left, right = st.columns(2)
with right:
    brands = choices(df, "العلامة التجارية")
    brand = st.selectbox("العلامة التجارية", brands, index=preferred(brands, "Hyundai"))
with left:
    brand_rows = df[df["العلامة التجارية"] == brand]
    models = choices(brand_rows, "الموديل")
    model = st.selectbox("الموديل", models, index=preferred(models, "Elantra"))
rows = brand_rows[brand_rows["الموديل"] == model]
with right:
    years = choices(rows, "سنة الصنع")
    year = st.selectbox("سنة الصنع", years, index=preferred(years, 2022))
with left:
    trims = choices(rows[rows["سنة الصنع"] == year], "الفئة")
    trim = st.selectbox("الفئة", trims, index=preferred(trims, "Premium"))
with right:
    mileage = st.number_input("العداد / الممشى الحالي (كيلومتر)", min_value=0, value=35000, step=1000)
    owners = st.number_input("عدد الملاك السابقين", min_value=0, value=1, step=1)
with left:
    regions = choices(df, "المنطقة")
    region = st.selectbox("المنطقة", regions, index=preferred(regions, "المنطقة الشرقية"))
    proposed = st.number_input("السعر المقترح من قبلك (ريال سعودي)", min_value=1, value=40000, step=500)

if st.button("احسب التقييم السعري", type="primary", use_container_width=True):
    try:
        result = evaluate(df, brand, model, year, trim, mileage, region, owners, proposed)
        text = f"نطاق السعر العادل لمركبتك هو بين {result['lower']:,.0f} ريال و {result['upper']:,.0f} ريال.\n\n{result['message']}"
        if result["status"] == "success":
            st.success(text)
        else:
            st.warning(text)
        if result["fallback"]:
            st.caption("لم تتوفر حالات مشابهة بالتفاصيل؛ استُخدم متوسط العلامة والموديل وسنة الصنع.")
        if result["count"] < 5:
            st.caption("عدد المقارنات محدود؛ التقدير أولي ولا يضمن دقة عالية.")
    except ValueError as exc:
        st.error(str(exc))
