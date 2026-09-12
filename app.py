import streamlit as st
import pandas as pd

st.set_page_config(page_title="Menu Processor", layout="wide")
st.title("🍔 برنامج معالجة المنيو الآلي")

uploaded_file = st.file_uploader("ارفع ملف المنيو هنا (Excel/CSV):", type=["xlsx", "csv"])

if uploaded_file and st.button("🚀 ابدأ المعالجة"):
    st.info("جاري المعالجة...")
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    st.success("تمت قراءة الملف بنجاح!")
    st.dataframe(df)
