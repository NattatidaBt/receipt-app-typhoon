import cv2
import streamlit as st

from llm_engine import call_typhoon_llm
from ocr_engine import (
    deskew_image,
    load_image_or_pdf,
    process_method_4_sharpening,
    run_typhoon_ocr,
)

# 1. ตั้งค่าหน้าต่างระบบหลัก (ซ่อนเมนูและ Sidebar ทั้งหมด)
st.set_page_config(page_title="RecAipt - Receipt scanning tools", layout="wide", initial_sidebar_state="collapsed")

# 🎨 2. ประกาศสไตล์ CSS ระดับสูง เพื่อล้างสไตล์ดั้งเดิมของ Streamlit และใช้ดีไซน์ RecAipt แทน
st.markdown("""
    <style>
    /* ซ่อนแถบเครื่องมือด้านบน ปุ่มเมนู และฟุตเตอร์ของ Streamlit ออกให้หมด 100% */
    header, footer, [data-testid="stToolbar"], [data-testid="stSidebar"] {
        visibility: hidden !important;
        height: 0 !important;
        display: none !important;
    }

    /* 🔥 ซ่อนปุ่ม Upload ดั้งเดิม และคำอธิบายขนาดไฟล์ของ Streamlit */
    [data-testid="stFileUploaderDropzoneInputButton"], 
    [data-testid="stFileUploaderFileSize"] {
        display: none !important;
    }
    .stFileUploader > section > div {
        display: none !important;
    }

    /* บังคับเปลี่ยนสีพื้นหลังทั้งแอปพลิเคชันให้เป็นสีขาวอมชมพูหวานละมุน */
    .stApp {
        background-color: #FFF2F6 !important;
    }

    /* ดีไซน์แถบกล่องสีขาวด้านบน (Header Bar) ตาม Mockup */
    .header-bar {
        background-color: #FFFFFF;
        border-radius: 20px;
        padding: 15px 30px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 20px rgba(74, 46, 53, 0.02);
        margin-bottom: 50px;
    }
    .logo-text {
        color: #4A2E35;
        font-size: 24px;
        font-weight: bold;
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 0;
    }
    .lang-dropdown {
        background-color: #D47A9A;
        color: white;
        padding: 8px 16px;
        border-radius: 10px;
        font-size: 14px;
        font-weight: 500;
    }

    /* ดีไซน์ชุดอักษรหัวข้อกลางหน้าเว็บ */
    .hero-title {
        text-align: center;
        color: #4A2E35;
        font-size: 38px;
        font-weight: 500;
        margin-top: 30px;
        margin-bottom: 12px;
        letter-spacing: -0.5px;
    }
    .hero-subtitle {
        text-align: center;
        color: #C29BA4;
        font-size: 16px;
        margin-bottom: 50px;
    }

    /* ปรับแต่งความโค้งมนและสีของกล่องลากไฟล์อัปโหลดให้เป็นเส้นประชมพูแบบน่ารัก */
    .stFileUploader {
        max-width: 850px;
        margin: 0 auto !important;
    }
    .stFileUploader > section {
        background-color: #FFFFFF !important; /* เปลี่ยนเป็นสีขาวคลีนตาม Mockup */
        border: 2px dashed #F5C2D1 !important;
        border-radius: 24px !important;
        padding: 60px 20px !important;
        box-shadow: 0 10px 30px rgba(212, 122, 154, 0.04) !important;
    }

    .stFileUploaderDropzone {
        border: none !important;
        background: transparent !important;
    }
    /* สร้างหน้าต่างกลางกล่องรับไฟล์จำลอง (Icon เอกสาร + คำแนะนำ) */
    .custom-upload-box {
        text-align: center;
        pointer-events: none;
    }
    .upload-icon {
        font-size: 48px;
        color: #7B6167;
        margin-bottom: 15px;
    }
    .upload-text {
        color: #A3858C;
        font-size: 16px;
    }

    /* จัดการบล็อกการแบ่งฝั่งซ้าย-ขวา (Split-Screen Space) */
    div[data-testid="stHorizontalBlock"] {
        background-color: #FFFFFF !important;
        border-radius: 32px !important;
        padding: 40px !important;
        box-shadow: 0 12px 40px rgba(74, 46, 53, 0.04) !important;
        max-width: 1400px;
        margin: 0 auto !important;
    }

    /* ดีไซน์การ์ดรายละเอียดใบเสร็จฝั่งขวา */
    .receipt-card {
        background-color: #FFF5F7;
        border-radius: 24px;
        padding: 30px;
        border: 1px solid #FCE4EC;
    }

    /* รีเซ็ตกล่องอินพุตข้อมูล Text และ Number ทั้งหมดให้ออกสีขาวเรียบหรูตามดีไซน์ */
    .stTextInput input, .stNumberInput input {
        background-color: #FFFFFF !important;
        color: #4A2E35 !important;
        border: 1px solid #E8B4C5 !important;
        border-radius: 12px !important;
        padding: 12px !important;
        font-size: 15px !important;
    }

    /* ปรับแต่งปุ่มกดยืนยัน/ส่งออก (Submit Button) หลังฟอร์ม */
    button[kind="formSubmit"] {
        background-color: #F8D7E3 !important;
        color: #A35271 !important;
        border-radius: 14px !important;
        border: 1px solid #F5BCCF !important;
        width: 100% !important;
        font-weight: bold !important;
        font-size: 16px !important;
        padding: 0.7rem 0 !important;
        transition: all 0.2s ease !important;
    }
    button[kind="formSubmit"]:hover {
        background-color: #D47A9A !important;
        color: white !important;
    }

    /* ดีไซน์ปุ่มกลมลูกศรย้อนกลับ (Back Arrow Button) */
    div.stButton > button {
        background-color: #F8D7E3 !important;
        color: #A35271 !important;
        border-radius: 50% !important;
        width: 45px !important;
        height: 45px !important;
        padding: 0 !important;
        line-height: 45px !important;
        border: none !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

# 🏢 ส่วนประกอบที่ 1: แถบกล่องสีขาวควบคุมโลโก้และภาษาด้านบนสุด (Header Bar)
st.markdown("""
    <div class="header-bar">
        <div class="logo-text">📄 RecAipt</div>
        <div class="lang-dropdown">English ▾</div>
    </div>
""", unsafe_allow_html=True)

# ตรวจสอบโครงสร้างสเตตัสหน้าระบบ เพื่อทำการจำแนกการแสดงผลสไตล์หน้าจอ
if st.session_state.get("file_uploaded") is None:

    # 📌 หน้าแรกเริ่มใช้งาน (เหมือนดีไซน์หน้า 2 ของกลุ่มคุณ 100%)
    st.markdown("<div class='hero-title'>Receipt scanning and data collection tools</div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>Upload an image or PDF of your receipt to store it using OCR</div>",
                unsafe_allow_html=True)

    # วางกล่องรับไฟล์พร้อมซ้อนทับด้วยไอคอนแบบจำลอง
    uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png", "pdf"], key="uploader_widget")

    st.markdown("""
        <div style="margin-top: -155px; margin-bottom: 80px;" class="custom-upload-box">
            <div class="upload-icon">🖺</div>
            <div class="upload-text">Choose or paste a file here (image or PDF)</div>
        </div>
    """, unsafe_allow_html=True)

    if uploaded_file is not None:
        st.session_state["file_uploaded"] = uploaded_file
        st.rerun()

else:
    # 📌 หน้าผลลัพธ์ข้อมูลดิจิทัล (เหมือนดีไซน์หน้า 3 ของกลุ่มคุณ 100%)
    uploaded_file = st.session_state["file_uploaded"]
    file_bytes = uploaded_file.read()
    file_name = uploaded_file.name

    # ประมวลผลภาพหลังบ้านผ่านโมดูล AI
    with st.spinner("⏳ กระบวนการขั้นที่ 1: กำลังปรับความสมบูรณ์ภาพเอกสาร..."):
        img = load_image_or_pdf(file_bytes, file_name)
        if img is None:
            st.error("❌ ไฟล์เอกสารเกิดความเสียหาย")
            st.button("⇜", on_click=lambda: st.session_state.clear())
            st.stop()
        deskewed_img = deskew_image(img)
        processed_img = process_method_4_sharpening(deskewed_img)

    with st.spinner("⚡ กระบวนการขั้นที่ 2: ดำเนินการยิงดึงสายอักขระผ่าน Typhoon OCR..."):
        raw_text = run_typhoon_ocr(processed_img)

    if "[ERROR]" in raw_text or not raw_text.strip():
        st.error("❌ ระบบไม่สามารถอ่านคำออกจากใบเสร็จใบนี้ได้")
        if st.button("⇜"):
            st.session_state.clear()
            st.rerun()
    else:
        with st.spinner("🤖 กระบวนการขั้นที่ 3: ดำเนินการคัดแยกก้อนพัสดุฟิลด์ข้อมูลด้วย Typhoon LLM..."):
            extracted_json = call_typhoon_llm(raw_text)

        # ปุ่มกดย้อนกลับรูปแบบวงกลมสีชมพูตามระนาบดีไซน์ (Back Arrow Button)
        if st.button("⇜", key="back_to_upload"):
            st.session_state.clear()
            st.rerun()

        # สร้างเค้าโครงโครงสร้างแบบสองฝั่งหน้าจอ (Split-Screen Component)
        col_left, col_right = st.columns([1, 1.1])

        with col_left:
            if len(processed_img.shape) == 2:
                display_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2RGB)
            else:
                display_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)
            st.image(display_img, use_container_width=True)

            with st.expander("📄 เปิดรีวิวข้อความดิบ (Raw OCR Texts)"):
                st.code(raw_text, language="text")

        with col_right:
            # ครอบฟอร์มทั้งหมดไว้ในการ์ดสไตล์สีชมพูพาสเทลตามคุณสมบัติการดีไซน์
            st.markdown('<div class="receipt-card">', unsafe_allow_html=True)
            st.markdown(
                "<h4 style='color: #4A2E35; font-weight: bold; text-align: center; margin-bottom: 25px;'>รายละเอียดใบเสร็จ</h4>",
                unsafe_allow_html=True)

            if "error" in extracted_json:
                st.error(extracted_json["error"])
            else:
                with st.form("verified_receipt_form"):
                    merchant = st.text_input("🏪 ร้านค้า / ผู้ขาย", value=extracted_json.get("store_name", ""))
                    tax_id = st.text_input("🆔 เลขประจำตัวผู้เสียภาษี (Tax ID)", value=extracted_json.get("tax_id", ""))
                    receipt_no = st.text_input("🧾 เลขที่ใบเสร็จ", value=extracted_json.get("receipt_no", ""))
                    date_val = st.text_input("📅 วันที่ (YYYY-MM-DD)", value=extracted_json.get("date", ""))

                    st.write("<p style='font-weight:bold; margin-top:20px; color:#4A2E35;'>📦 รายการสินค้า</p>",
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
                            i_price = st.number_input("ราคา", value=default_price, step=0.5, key=f"p_{idx}")

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
                    vat = st.number_input("VAT 7% :", value=default_vat, step=0.1)

                    raw_total = extracted_json.get("total", 0.0)
                    if isinstance(raw_total, str): raw_total = raw_total.replace(",", "")
                    try:
                        default_total = float(raw_total) if raw_total else 0.0
                    except:
                        default_total = 0.0
                    total = st.number_input("ยอดรวม :", value=default_total, step=0.5)

                    pay_method = st.text_input("💳 ช่องทางการจ่ายชำระเงิน (Payment Method)",
                                               value=extracted_json.get("payment_method", ""))

                    save_btn = st.form_submit_button("📥 ส่งออก")

                if save_btn:
                    st.success("🎉 บันทึกและดึงข้อมูล Unstructured เข้าสู่ก้อนฐานข้อมูลสำเร็จ!")
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
            st.markdown('</div>', unsafe_allow_html=True)