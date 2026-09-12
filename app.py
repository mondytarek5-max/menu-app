import streamlit as st
import pandas as pd
import io
import json
from google import genai
from google.genai import types

st.set_page_config(page_title="منصة معالجة المنيو الآلية", page_icon="🍔", layout="wide")

MASTER_SYSTEM_INSTRUCTION = """
أنت محرك معالجة منيو آلي يعمل وفق نظام "المرآة الصارم" (Strict Mirror Protocol).
القواعد الإلزامية:
1. المرجعية: الإمارات/الخليج الإنجليزية أصل، مصر/الأردن العربية أصل.
2. نظام المرآة: ترجمة كلمة مقابل كلمة بدقة متناهية دون حشو.
3. معجم المصطلحات: Lime->حامض, Bun->كيزر, Patty->قطعة, Tangy->منعش, Simmered->على البخار, Steamed->على البخار, Fritters->فطير مقلي, Flatbread->خبز مسطح, Gravy->جريفي, Dip->تغميس / صوص.
4. الأرقام بصيغة إنجليزية (1, 2, 3...) في النصوص العربية والإنجليزية.
"""

st.title("🍔 منصة معالجة المنيو الآلية")
st.caption("نظام معالجة المنيو وفق نظام المرآة الصارم وإخراج الشيتات الـ 6")

with st.sidebar:
    st.header("⚙️ إعدادات المنصة")
    raw_api_key = st.text_input("مفتاح API Key (Gemini):", type="password")
    country = st.selectbox("الدولة المستهدفة:", ["الإمارات / GCC", "مصر / الأردن"])

def apply_local_rules(df):
    clarifications, cleaned_rows = [], []
    for idx, row in df.iterrows():
        item_name = str(row.get('Item', row.get('Item name', row.get('Name', '')))).strip()
        desc = str(row.get('Description', '')).strip()
        price = row.get('Price', row.get('Price ', 0))
        cat = str(row.get('Category', 'Main')).strip()
        text_full = f"{item_name} {desc}".lower()
        
        if any(w in text_full for w in ['bacon', 'pork', 'wine', 'alcohol']):
            clarifications.append({"Item Name": item_name, "Action": "Removed", "Reason": "Forbidden ingredients"})
            continue
        try:
            if float(price) <= 0:
                clarifications.append({"Item Name": item_name, "Action": "Removed", "Reason": "Suspicious price (0)"})
                continue
        except: pass

        cleaned_rows.append({'Category': cat if cat != 'nan' else 'Main', 'Item': item_name, 'Description': desc, 'Price': price})
    return pd.DataFrame(cleaned_rows), pd.DataFrame(clarifications)

uploaded_file = st.file_uploader("ارفع ملف المنيو الخام (Excel / CSV):", type=["xlsx", "csv"])

if uploaded_file and st.button("🚀 ابدأ معالجة المنيو"):
    api_key = raw_api_key.strip() if raw_api_key else ""
    if not api_key:
        st.error("يرجى إدخال مفتاح API Key في القائمة الجانبية أولاً!")
    else:
        with st.spinner("جاري تطبيق قواعد الدستور الصارم والترجمة..."):
            try:
                raw_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                cleaned_df, clarifications_df = apply_local_rules(raw_df)
                
                client = genai.Client(api_key=api_key)
                prompt = f"قم بترجمة المنيو وفق نظام المرآة الصارم وتنسيق JSON:\n{cleaned_df.to_json(orient='records')}"
                
                response = client.models.generate_content(
                    model='gemini-3.6-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(system_instruction=MASTER_SYSTEM_INSTRUCTION, response_mime_type="application/json")
                )
                processed_data = json.loads(response.text)
                
                sections, items = [], []
                sec_map, sec_counter = {}, 1
                for seq, row in enumerate(processed_data, 1):
                    cat_e, cat_a = row.get('category_eng', 'Main'), row.get('category_arb', 'الرئيسية')
                    if cat_e not in sec_map:
                        sec_map[cat_e] = sec_counter
                        sections.append({"Menu Section ID": sec_counter, "Name(Eng)": cat_e, "Name(Arb)": cat_a, "Sort Order": sec_counter})
                        sec_counter += 1
                    items.append({
                        "Menu Section ID": sec_map[cat_e], "Menu Section Name": cat_e, "Menu Item ID": seq,
                        "Name(Eng)": row.get('item_eng', ''), "Name(Arb)": row.get('item_arb', ''),
                        "Description(Eng)": row.get('desc_eng', ''), "Description(Arb)": row.get('desc_arb', ''),
                        "Price": float(row.get('price', 0)), "Sort Order": seq
                    })
                
                df_sec, df_item = pd.DataFrame(sections), pd.DataFrame(items)
                df_empty = pd.DataFrame()

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_sec.to_excel(writer, sheet_name='Menu_Sections', index=False)
                    df_item.to_excel(writer, sheet_name='Menu_Items', index=False)
                    df_empty.to_excel(writer, sheet_name='Menu_Label_Header', index=False)
                    df_empty.to_excel(writer, sheet_name='Menu_Label_Choices', index=False)
                    df_empty.to_excel(writer, sheet_name='Menu_Label_Header_L2', index=False)
                    df_empty.to_excel(writer, sheet_name='Menu_Label_Choices_L2', index=False)

                st.success("تمت المعالجة بنجاح!")
                t1, t2, t3 = st.tabs(["📋 الأصناف Mapped", "⚠️ المحذوفات", "📥 التحميل"])
                with t1: st.dataframe(df_item, use_container_width=True)
                with t2: st.dataframe(clarifications_df, use_container_width=True)
                with t3: st.download_button("📥 تحميل الإكسيل النهائي (6 الشيتات)", output.getvalue(), "Processed_Menu.xlsx")
            except Exception as e:
                st.error(f"حدث خطأ أثناء المعالجة: {str(e)}")
