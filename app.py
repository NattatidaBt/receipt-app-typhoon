import cv2
import streamlit as st

from llm_engine import call_typhoon_llm
from ocr_engine import (
    deskew_image,
    load_image_or_pdf,
    process_method_4_sharpening,
    run_typhoon_ocr,
)

# 1. ตั้งค่าหน้าต่างโปรแกรมแบบเปิดกว้างเต็มจอ
st.set_page_config(page_title="RecAipt - Receipt scanning tools", layout="wide")

# 🎨 2. บังคับสไตล์ระบบระดับลึก (Global CSS Override) เปลี่ยนสีพื้นหลัง ตัวอักษร และลบแถบดำด้านบนออก
st.markdown("""
    <style>
    /* ลบแถบเมนูสีดำและปุ่มดั้งเดิมของ Streamlit ออกเพื่อความคลีน */
    header, footer, [data-testid="stToolbar"] {
        visibility: hidden !important;
        height: 0 !important;
    }

    /* บังคับเปลี่ยนสีพื้นหลังทั้งแอปพลิเคชันให้เป็นสีขาวอมชมพูหวานละมุน */
    .stApp {
        background-color: #FFF2F6 !important;
    }

    /* ดีไซน์ปุ่มสลับภาษาด้านขวาบน (Mockup Language Button) */
    .lang-container {
        position: absolute;
        top: -50px;
        right: 10px;
        background-color: #D47A9A;
        color: white;
        padding: 6px 14px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: bold;
    }

    /* ดีไซน์หัวข้อ Title ตรงกลางหน้าเว็บ */
    .main-title {
        text-align: center;
        color: #4A2E35;
        font-family: 'Inter', sans-serif;
        font-size: 36px;
        font-weight: 500;
        margin-top: 40px;
        margin-bottom: 8px;
    }
    .main-subtitle {
        text-align: center;
        color: #A3858C;
        font-family: 'Inter', sans-serif;
        font-size: 16px;
        margin-bottom: 40px;
    }

    /* ปรับแต่งความโค้งมนและสีของกล่องลากไฟล์อัปโหลดให้เป็นเส้นประชมพูแบบน่ารัก */
    .stFileUploader {
        max-width: 800px;
        margin: 0 auto !important;
        border: 2px dashed #E8B4C5 !important;
        border-radius: 20px !important;
        background-color: #FFF9FA !important;
        padding: 30px !important;
        box-shadow: 0 4px 12px rgba(212, 122, 154, 0.05);
    }

    /* จัดการการแสดงผลกรอบการแบ่งฝั่ง Split-Screen */
    div[data-testid="stHorizontalBlock"] {
        background-color: #FFFFFF !important;
        border-radius: 24px !important;
        padding: 30px !important;
        box-shadow: 0 10px 30px rgba(74, 46, 53, 0.05) !important;
        margin-top: 20px !important;
    }

    /* ดีไซน์ส่วนประกอบฟอร์มฝั่งขวา (รายละเอียดใบเสร็จ) */
    div[data-testid="stForm"] {
        border: none !important;
        background-color: #FFF6F8 !important;
        border-radius: 18px !important;
        padding: 20px !important;
    }

    /* เปลี่ยนสไตล์ช่องกล่องพิมพ์ข้อมูลตัวหนังสือและตัวเลขทั้งหมด */
    .stTextInput input, .stNumberInput input {
        background-color: #FFFFFF !important;
        color: #4A2E35 !important;
        border: 1px solid #E8B4C5 !important;
        border-radius: 10px !important;
        padding: 10px !important;
    }

    /* ดีไซน์ปุ่มกดสีชมพูสำหรับส่งออกหรือบันทึกข้อมูล (Submit Button) */
    button[kind="formSubmit"] {
        background-color: #D47A9A !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        width: 100% !important;
        font-weight: bold !important;
        font-size: 16px !important;
        padding: 0.7rem 0 !important;
        box-shadow: 0 4px 12px rgba(212, 122, 154, 0.2) !important;
        transition: all 0.3s ease !important;
    }
    button[kind="formSubmit"]:hover {
        background-color: #B55F7E !important;
        color: white !important;
        box-shadow: 0 6px 16px rgba(212, 122, 154, 0.3) !important;
    }
    </style>
""", unsafe_allow_html=True)

# โลโก้แบรนด์ และปุ่มเลือกภาษาจำลองที่มุมขวาบนตาม Mockup
c_logo, c_lang = st.columns([8, 2])
with c_logo:
    st.markdown("<h3 style='color: #4A2E35; font-weight: bold;'>📋 RecAipt</h3>", unsafe_allow_html=True)
with c_lang:
    st.markdown("<div class='lang-container'>English ▾</div>", unsafe_allow_html=True)

# ตรวจสอบสเตตัสการอัปโหลดไฟล์ เพื่อสลับหน้าตา UI โดยอัตโนมัติ
if st.session_state.get("uploaded_file") is None:
    # 📌 หน้าตาแรก (หน้าแรกเริ่มอัปโหลดไฟล์ - เหมือนรูป image_e4ebac.png)
    st.markdown("<div class='main-title'>Receipt scanning and data collection tools</div>", unsafe_allow_html=True)
    st.markdown("<div class='main-subtitle'>Upload an image or PDF of your receipt to store it using OCR</div>",
                unsafe_allow_html=True)

    uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png", "pdf"])
    if uploaded_file is not None:
        st.session_state["uploaded_file"] = uploaded_file
        st.rerun()

else:
    # 📌 หน้าตาที่สอง (หน้าจัดการผลลัพธ์ข้อมูลดิจิทัล - เหมือนรูป image_e4ebcd.png)
    uploaded_file = st.session_state["uploaded_file"]
    file_bytes = uploaded_file.read()
    file_name = uploaded_file.name

    # ดำเนินกระบวนการวิเคราะห์หลังบ้าน
    with st.spinner("⏳ กระบวนการขั้นที่ 1: กำลังปรับความคมชัดภาพเอกสารใบเสร็จ..."):
        img = load_image_or_pdf(file_bytes, file_name)
        if img is None:
            st.error("❌ ไฟล์เอกสารเกิดความเสียหาย")
            st.button("🔄 ย้อนกลับหน้าแรก", on_click=lambda: st.session_state.clear())
            st.stop()
        deskewed_img = deskew_image(img)
        processed_img = process_method_4_sharpening(deskewed_img)

    with st.spinner("⚡ กระบวนการขั้นที่ 2: ดำเนินการแกะสายคำอักขระดิบด้วย Typhoon OCR..."):
        raw_text = run_typhoon_ocr(processed_img)

    if "[ERROR]" in raw_text or not raw_text.strip():
        st.error("❌ ไม่สามารถสกัดข้อความออกจากเอกสารใบเสร็จใบนี้ได้")
        if st.button("🔄 ย้อนกลับหน้าแรก"):
            st.session_state.clear()
            st.rerun()
    else:
        with st.spinner("🤖 กระบวนการขั้นที่ 3: กำลังสกัดความหมายตัวเลข JSON ด้วย Typhoon LLM..."):
            extracted_json = call_typhoon_llm(raw_text)

        # ปุ่มกดย้อนกลับไปหน้าอัปโหลดใหม่ (สัญลักษณ์ลูกศรซ้ายชี้กลับตามดีไซน์)
        if st.button("⇜ ย้อนกลับเพื่ออัปโหลดใหม่", key="back_btn"):
            st.session_state.clear()
            st.rerun()

        # แบ่งสัดส่วนออกเป็น 2 ช่องใหญ่ ซ้าย (รูปภาพ) ขวา (แบบฟอร์มแก้ไข)
        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown(
                "<h4 style='color: #4A2E35; font-weight: bold; margin-bottom:15px;'>🖼️ ไฟล์เอกสารใบเสร็จอ้างอิง</h4>",
                unsafe_allow_html=True)
            if len(processed_img.shape) == 2:
                display_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2RGB)
            else:
                display_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)
            st.image(display_img, use_container_width=True)

            with st.expander("📄 ดูข้อความดิบที่ส่งผ่านระบบคลาวด์"):
                st.code(raw_text, language="text")

        with col_right:
            st.markdown(
                "<h4 style='color: #4A2E35; font-weight: bold; text-align: center;'>📝 รายละเอียดใบเสร็จรับเงิน</h4>",
                unsafe_allow_html=True)

            if "error" in extracted_json:
                st.error(extracted_json["error"])
            else:
                with st.form("verified_receipt_form"):
                    merchant = st.text_input("🏪 ชื่อร้านค้า / บริษัทผู้ชำระเงิน",
                                             value=extracted_json.get("store_name", ""))
                    tax_id = st.text_input("🆔 เลขประจำตัวผู้เสียภาษี (Tax ID)", value=extracted_json.get("tax_id", ""))
                    receipt_no = st.text_input("🧾 หมายเลขเลขที่เอกสาร (Receipt No.)",
                                               value=extracted_json.get("receipt_no", ""))
                    date_val = st.text_input("📅 วันเวลาบันทึกรายการ (YYYY-MM-DD)", value=extracted_json.get("date", ""))

                    st.write("<p style='font-weight:bold; margin-top:15px; color:#4A2E35;'>📦 รายการสินค้าและบริการ</p>",
                             unsafe_allow_html=True)
                    items_list = extracted_json.get("items", []) or []
                    edited_items = []

                    for idx, item in enumerate(items_list):
                        c1, c2, c3 = st.columns([5, 2, 3])
                        with c1:
                            i_name = st.text_input(f"รายการ #{idx + 1}", value=item.get("name", ""), key=f"n_{idx}")

                        import re

                        raw_qty = item.get("qty", 1)
                        if isinstance(raw_qty, str): raw_qty = re.sub(r"[^\d.]", "", raw_qty)
                        try:
                            default_qty = int(float(raw_qty)) if raw_qty else 1
                        except:
                            default_qty = 1
                        with c2:
                            i_qty = st.number_input("จำนวน", value=default_qty, step=1, key=f"q_{idx}")

                        raw_price = item.get("unit_price", 0.0)
                        if isinstance(raw_price, str): raw_price = raw_price.replace(",", "")
                        try:
                            default_price = float(raw_price) if raw_price else 0.0
                        except:
                            default_price = 0.0
                        with c3:
                            i_price = st.number_input("ราคาต่อหน่วย", value=default_price, step=0.5, key=f"p_{idx}")

                        edited_items.append(
                            {"name": i_name, "qty": i_qty, "unit_price": i_price, "amount": i_qty * i_price})

                    st.write("---")

                    raw_subtotal = extracted_json.get("subtotal", 0.0)
                    if isinstance(raw_subtotal, str): raw_subtotal = raw_subtotal.replace(",", "")
                    try:
                        default_subtotal = float(raw_subtotal) if raw_subtotal else 0.0
                    except:
                        default_subtotal = 0.0
                    subtotal = st.number_input("ยอดรวมก่อนคิดภาษี (Subtotal)", value=default_subtotal, step=0.5)

                    raw_vat = extracted_json.get("vat", 0.0)
                    if isinstance(raw_vat, str): raw_vat = raw_vat.replace(",", "")
                    try:
                        default_vat = float(raw_vat) if raw_vat else 0.0
                    except:
                        default_vat = 0.0
                    vat = st.number_input("ภาษีมูลค่าเพิ่มสะสม (VAT 7%)", value=default_vat, step=0.1)

                    raw_total = extracted_json.get("total", 0.0)
                    if isinstance(raw_total, str): raw_total = raw_total.replace(",", "")
                    try:
                        default_total = float(raw_total) if raw_total else 0.0
                    except:
                        default_total = 0.0
                    total = st.number_input("ยอดชำระเงินรวมทั้งสิ้นสุทธิ (Grand Total)", value=default_total, step=0.5)

                    pay_method = st.text_input("💳 ช่องทางการชำระเงิน (Payment Method)",
                                               value=extracted_json.get("payment_method", ""))

                    save_btn = st.form_submit_button("📤 ยืนยันข้อมูลและส่งออกไฟล์ดิจิทัล")

                if save_btn:
                    st.success("🎉 บันทึกและดึงข้อมูล Unstructured เข้าสู่ก้อนพัสดุฐานข้อมูลสำเร็จ!")
                    st.json({
                        "store_name": merchant,
                        "tax_id": tax_id,
                        "receipt_no": receipt_no,
                        "date": date_val,
                        "items": edited_items,
                        "subtotal": subtotal,
                        "vat": vat,
                        "total": total,
                        "payment_method": pay_method
                    })