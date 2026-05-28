import cv2
import streamlit as st
import re

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="RecAipt - Receipt scanning tools",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from llm_engine import call_typhoon_llm
from ocr_engine import (
    deskew_image,
    load_image_or_pdf,
    process_method_4_sharpening,
    run_typhoon_ocr,
)

# =========================================================
# CUSTOM CSS (RecAipt Pastel Pink Theme)
# =========================================================
st.markdown("""
<style>

/* =========================================================
   HIDE STREAMLIT DEFAULT UI
========================================================= */
header,
footer,
[data-testid="stToolbar"],
[data-testid="stSidebar"],
#MainMenu {
    visibility: hidden !important;
    display: none !important;
    height: 0 !important;
}

/* =========================================================
   🔥 บังคับล้างเศษปุ่มดั้งเดิม โครงไอคอน และตัวอักษรส่วนเกิน 100%
========================================================= */
[data-testid="stFileUploaderDropzoneInputButton"],
[data-testid="stFileUploaderFileSize"],
[data-testid="stFileUploaderFileHeader"],
[data-testid="stFileUploaderDeleteBtn"],
[data-testid="stFileUploaderFileName"],
[data-testid="stFileUploaderFile"],
[data-testid="stFileUploaderDropzone"] svg,
small[data-testid="stWidgetLabel-help"],
.stFileUploaderSection,
.st-emotion-cache-12w0qpk, 
.st-emotion-cache-9ycgxx,
.st-emotion-cache-167576q,
.st-emotion-cache-1er4887,
div[data-testid="stFileUploaderDropzone"] > div {
    display: none !important;
}

/* =========================================================
   GLOBAL APP STYLE
========================================================= */
.stApp {
    background-color: #FFF3F7 !important;
}

/* ปรับแต่งระยะขอบหน้าจอหลัก */
.block-container {
    max-width: 100% !important;
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
    padding-left: 3rem !important;
    padding-right: 3rem !important;
}

/* =========================================================
   HEADER BAR
========================================================= */
.header-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 15px 30px;
    margin-bottom: 50px;
    background-color: #FFFFFF;
    border-radius: 20px;
    box-shadow: 0 4px 20px rgba(74, 46, 53, 0.02);
}

.logo-text {
    color: #4A2E35;
    font-size: 22px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 10px;
}

.lang-dropdown {
    background-color: #C97D98;
    color: white;
    padding: 8px 16px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 500;
}

/* =========================================================
   HERO SECTION
========================================================= */
.hero-title {
    text-align: center;
    color: #4A2E35;
    font-size: 34px;
    font-weight: 500;
    margin-top: 30px;
    margin-bottom: 10px;
}

.hero-subtitle {
    text-align: center;
    color: #C29BA4;
    font-size: 15px;
    margin-bottom: 45px;
}

/* =========================================================
   FILE UPLOADER FRAME
========================================================= */
section[data-testid="stFileUploader"] {
    max-width: 850px;
    margin: auto;
}

section[data-testid="stFileUploader"] > div {
    background-color: white !important;
    border: 2px dashed #F4C6D5 !important;
    border-radius: 30px !important;
    min-height: 320px !important;
    padding: 100px 20px !important;
    box-shadow: 0 12px 40px rgba(0,0,0,0.03);
}

[data-testid="stFileUploaderDropzone"] {
    background: transparent !important;
    border: none !important;
}

/* =========================================================
   CUSTOM UPLOAD CONTENT (หน้ากากมินิมอลจำลอง)
========================================================= */
.upload-overlay {
    position: relative;
    margin-top: -215px;
    margin-bottom: 75px;
    z-index: 10;
    pointer-events: none;
}

.custom-upload-box {
    text-align: center;
}

.upload-icon {
    font-size: 54px;
    margin-bottom: 12px;
}

.upload-text {
    color: #A3858C;
    font-size: 15px;
}

/* =========================================================
   RESULT WRAPPER & LAYOUT
========================================================= */
.result-wrapper {
    background: white;
    border-radius: 32px;
    padding: 35px;
    max-width: 1400px;
    margin: auto;
    box-shadow: 0 10px 35px rgba(0,0,0,0.04);
}

div[data-testid="stHorizontalBlock"] {
    gap: 40px !important;
    align-items: flex-start !important;
}

/* การ์ดรายละเอียดฟอร์มฝั่งขวา */
.receipt-card {
    background-color: #FFF6F8;
    border-radius: 24px;
    padding: 28px;
    border: 1px solid #F8D7E3;
}

/* =========================================================
   TEXT & NUMBER INPUTS
========================================================= */
.stTextInput input,
.stNumberInput input {
    background-color: white !important;
    border: 1px solid #E8B4C5 !important;
    border-radius: 12px !important;
    color: #4A2E35 !important;
    height: 46px !important;
    font-size: 14px !important;
    box-shadow: none !important;
}

.stTextInput label,
.stNumberInput label {
    color: #7A5A63 !important;
    font-weight: 500 !important;
}

div[data-testid="stForm"] {
    border: none !important;
    background: transparent !important;
    padding: 0 !important;
}

/* =========================================================
   FORM SUBMIT & BACK BUTTONS
========================================================= */
button[kind="formSubmit"] {
    background-color: #F8D7E3 !important;
    color: #A35271 !important;
    border-radius: 14px !important;
    border: none !important;
    width: 100% !important;
    height: 48px !important;
    font-weight: bold !important;
    font-size: 15px !important;
    transition: all 0.2s ease !important;
}

button[kind="formSubmit"]:hover {
    background-color: #D47A9A !important;
    color: white !important;
}

div.stButton > button {
    background-color: #F8D7E3 !important;
    color: #A35271 !important;
    border-radius: 12px !important;
    width: 42px !important;
    height: 42px !important;
    border: none !important;
    font-weight: bold !important;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# HEADER BAR COMPONENT
# =========================================================
st.markdown("""
<div class="header-bar">
    <div class="logo-text">
        📄 RecAipt
    </div>
    <div class="lang-dropdown">
        English ▾
    </div>
</div>
""", unsafe_allow_html=True)


# ฟังก์ชันสำหรับล้างค่าระบบเมื่อกดย้อนกลับ
def reset_app():
    st.session_state.clear()


# =========================================================
# PAGE 1 : UPLOAD PAGE
# =========================================================
if "processed_img" not in st.session_state or st.session_state.get("file_uploaded") is None:

    st.markdown("<div class='hero-title'>Receipt scanning and data collection tools</div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>Upload an image or PDF of your receipt to store it using OCR</div>",
                unsafe_allow_html=True)

    uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png", "pdf"], key="uploader_widget")

    # ส่วนซ้อนทับเพื่อสร้างฟอนต์และไอคอนมินิมอลจำลอง
    st.markdown("""
    <div class="upload-overlay">
        <div class="custom-upload-box">
            <div class="upload-icon">📄</div>
            <div class="upload-text">Choose or paste a file here (image or PDF)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # =====================================================
    # OCR PIPELINE PROCESS
    # =====================================================
    if uploaded_file is not None:
        st.session_state["file_uploaded"] = uploaded_file
        file_bytes = uploaded_file.read()
        file_name = uploaded_file.name

        with st.spinner("⏳ Processing image..."):
            img = load_image_or_pdf(file_bytes, file_name)
            if img is None:
                st.error("❌ Unsupported file format")
                st.stop()

            deskewed_img = deskew_image(img)
            processed = process_method_4_sharpening(deskewed_img)
            st.session_state["processed_img"] = processed

        with st.spinner("⚡ Running OCR..."):
            raw_text = run_typhoon_ocr(st.session_state["processed_img"])
            st.session_state["raw_text"] = raw_text

        if "[ERROR]" in raw_text or not raw_text.strip():
            st.error("❌ OCR Operation Failed")
            st.session_state.clear()
        else:
            with st.spinner("🤖 Structuring data..."):
                extracted_json = call_typhoon_llm(raw_text)
                st.session_state["extracted_json"] = extracted_json
            st.rerun()

# =========================================================
# PAGE 2 : RESULT DASHBOARD
# =========================================================
else:
    processed_img = st.session_state["processed_img"]
    raw_text = st.session_state["raw_text"]
    extracted_json = st.session_state["extracted_json"]

    # ปุ่มกดย้อนกลับสไตล์มินิมอลแบบจำลองตามข้อกำหนด
    st.button("←", key="back_to_upload", on_click=reset_app)

    st.markdown('<div class="result-wrapper">', unsafe_allow_html=True)
    col_left, col_right = st.columns([1, 1])

    # -----------------------------------------------------
    # ฝั่งซ้าย: แสดงผลรูปภาพเอกสารอ้างอิง
    # -----------------------------------------------------
    with col_left:
        if len(processed_img.shape) == 2:
            display_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2RGB)
        else:
            display_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)

        st.image(display_img, use_container_width=True)

        with st.expander("📄 Raw OCR Text"):
            st.code(raw_text, language="text")

    # -----------------------------------------------------
    # ฝั่งขวา: การ์ดฟอร์มดิจิทัล (รายละเอียดใบเสร็จ)
    # -----------------------------------------------------
    with col_right:
        st.markdown('<div class="receipt-card">', unsafe_allow_html=True)
        st.markdown('<h3 style="text-align:center; color:#4A2E35; margin-bottom:25px;">รายละเอียดใบเสร็จ</h3>',
                    unsafe_allow_html=True)

        if "error" in extracted_json:
            st.error(extracted_json["error"])
        else:
            with st.form("verified_receipt_form"):
                merchant = st.text_input("🏪 ร้านค้า / ผู้ขาย", value=extracted_json.get("store_name", ""))
                receipt_no = st.text_input("🧾 เลขที่ใบเสร็จ", value=extracted_json.get("receipt_no", ""))
                date_val = st.text_input("📅 วันที่", value=extracted_json.get("date", ""))

                st.markdown("---")

                items_list = extracted_json.get("items", []) or []
                edited_items = []

                for idx, item in enumerate(items_list):
                    c1, c2, c3 = st.columns([5, 2, 3])
                    with c1:
                        i_name = st.text_input(f"รายการ #{idx + 1}", value=item.get("name", ""), key=f"n_{idx}")
                    with c2:
                        i_qty = st.number_input("จำนวน", value=int(float(item.get("qty", 1))), step=1, key=f"q_{idx}")
                    with c3:
                        i_price = st.number_input("ราคา", value=float(item.get("unit_price", 0)), step=0.5,
                                                  key=f"p_{idx}")

                    edited_items.append({
                        "name": i_name,
                        "qty": i_qty,
                        "unit_price": i_price,
                        "amount": i_qty * i_price
                    })

                st.markdown("---")

                subtotal = st.number_input("ยอดรวมก่อนภาษี", value=float(extracted_json.get("subtotal", 0)), step=0.5)
                vat = st.number_input("VAT 7%", value=float(extracted_json.get("vat", 0)), step=0.1)
                total = st.number_input("ยอดรวมทั้งหมด", value=float(extracted_json.get("total", 0)), step=0.5)

                save_btn = st.form_submit_button("📤 ส่งออก")

            if save_btn:
                st.success("🎉 บันทึกข้อมูลเรียบร้อยแล้ว")
                st.json({
                    "store_name": merchant,
                    "receipt_no": receipt_no,
                    "date": date_val,
                    "items": edited_items,
                    "subtotal": subtotal,
                    "vat": vat,
                    "total": total
                })

        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)