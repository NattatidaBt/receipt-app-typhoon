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
# CUSTOM CSS (RecAipt Pixel-Perfect Overlay)
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
   GLOBAL APP STYLE
========================================================= */
.stApp {
    background-color: #FFF3F7 !important;
}

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
   🔥 FILE UPLOADER RE-ARCHITECT (แก้ไขกล่องหายและปุ่มโผล่)
========================================================= */
section[data-testid="stFileUploader"] {
    max-width: 850px;
    margin: auto;
    position: relative;
}

/* ดีไซน์กล่องสีขาวใบใหญ่ให้กางตัวออกและมีเส้นประสีชมพู */
section[data-testid="stFileUploader"] > div {
    background-color: white !important;
    border: 2px dashed #F4C6D5 !important;
    border-radius: 30px !important;
    min-height: 260px !important;
    position: relative !important;
    box-shadow: 0 12px 40px rgba(74, 46, 53, 0.03) !important;
    padding: 0 !important;
}

/* ซ่อนคำอธิบายและไอคอนเดิมที่หลุดธีม */
[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploaderDropzone"] svg,
.stFileUploaderSection,
small[data-testid="stWidgetLabel-help"] {
    display: none !important;
}

/* ยืดพื้นที่ Dropzone ให้เต็มกรอบสีขาว */
[data-testid="stFileUploaderDropzone"] {
    background: transparent !important;
    border: none !important;
    min-height: 260px !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* ขยายปุ่ม Browse และข้อความเดิมให้ใหญ่เต็มกล่อง แล้วปรับให้โปร่งแสง 100% */
[data-testid="stFileUploaderDropzone"] button,
[data-testid="stFileUploaderDropzone"] div,
[data-testid="stFileUploaderFileSize"] {
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    width: 100% !important;
    height: 100% !important;
    opacity: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    cursor: pointer !important;
    z-index: 20 !important;
}

/* =========================================================
   CUSTOM UPLOAD CONTENT LAYER (หน้ากากข้อความจำลอง)
========================================================= */
.upload-overlay {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 10;
    pointer-events: none;
    width: 100%;
    text-align: center;
}

.custom-upload-box {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
}

.upload-icon {
    font-size: 50px;
    margin-bottom: 15px;
    color: #4A2E35;
}

.upload-text {
    color: #A3858C;
    font-size: 15px;
    font-weight: 400;
}

/* =========================================================
   RESULT CONTAINER & LAYOUT
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

.receipt-card {
    background-color: #FFF6F8;
    border-radius: 24px;
    padding: 28px;
    border: 1px solid #F8D7E3;
}

/* =========================================================
   INPUT ELEMENTS
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
   BUTTON ACTIONS
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
# HEADER COMPONENT
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


def reset_app():
    st.session_state.clear()


def safe_float(value, default=0.0):
    try:
        return float(str(value).replace(",", "").strip())
    except:
        return default


def safe_int(value, default=1):
    try:
        return int(float(str(value).replace(",", "").strip()))
    except:
        return default


# =========================================================
# PAGE 1 : UPLOAD PAGE
# =========================================================
if "processed_img" not in st.session_state or st.session_state.get("file_uploaded") is None:

    st.markdown("<div class='hero-title'>Receipt scanning and data collection tools</div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>Upload an image or PDF of your receipt to store it using OCR</div>",
                unsafe_allow_html=True)

    # วาง uploader ตัวหลัก
    uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png", "pdf"], key="uploader_widget")

    # หน้ากากจำลองจัดให้อยู่ตำแหน่งกึ่งกลางกล่องขาวอย่างเที่ยงตรงด้วยสิทธิ์ควบคุม Absolute Z-Index
    st.markdown("""
    <div class="upload-overlay">
        <div class="custom-upload-box">
            <div class="upload-icon">📄</div>
            <div class="upload-text">Choose or paste a file here (image or PDF)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -----------------------------------------------------
    # PIPELINE ENGINE EXECUTION
    # -----------------------------------------------------
    if uploaded_file is not None:
        st.session_state["file_uploaded"] = uploaded_file
        file_bytes = uploaded_file.read()
        file_name = uploaded_file.name

        with st.spinner("⏳ Processing image..."):
            img = load_image_or_pdf(file_bytes, file_name)
            if img is None:
                st.error("❌ Unsupported file")
                st.stop()

            deskewed_img = deskew_image(img)
            processed = process_method_4_sharpening(deskewed_img)
            st.session_state["processed_img"] = processed

        with st.spinner("⚡ Running OCR..."):
            raw_text = run_typhoon_ocr(st.session_state["processed_img"])
            st.session_state["raw_text"] = raw_text

        if "[ERROR]" in raw_text or not raw_text.strip():
            st.error("❌ OCR failed")
            st.session_state.clear()
        else:
            with st.spinner("🤖 Structuring data..."):
                extracted_json = call_typhoon_llm(raw_text)
                st.session_state["extracted_json"] = extracted_json
            st.rerun()

# =========================================================
# PAGE 2 : RESULT PAGE
# =========================================================
else:
    processed_img = st.session_state["processed_img"]
    raw_text = st.session_state["raw_text"]
    extracted_json = st.session_state["extracted_json"]

    st.button("←", key="back_to_upload", on_click=reset_app)

    st.markdown('<div class="result-wrapper">', unsafe_allow_html=True)
    col_left, col_right = st.columns([1, 1])

    with col_left:
        if len(processed_img.shape) == 2:
            display_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2RGB)
        else:
            display_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)

        st.image(display_img, use_container_width=True)

        with st.expander("📄 Raw OCR Text"):
            st.code(raw_text, language="text")

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

                    raw_qty = item.get("qty", 1)
                    qty_value = safe_int(raw_qty)
                    with c2:
                        i_qty = st.number_input("จำนวน", value=qty_value, step=1, key=f"q_{idx}")

                    raw_price = item.get("unit_price", 0)
                    price_value = safe_float(raw_price)
                    with c3:
                        i_price = st.number_input("ราคา", value=price_value, step=0.5, key=f"p_{idx}")

                    edited_items.append({
                        "name": i_name,
                        "qty": i_qty,
                        "unit_price": i_price,
                        "amount": i_qty * i_price
                    })

                st.markdown("---")
                subtotal_value = safe_float(extracted_json.get("subtotal", 0))
                subtotal = st.number_input("ยอดรวมก่อนภาษี", value=subtotal_value, step=0.5)

                vat_value = safe_float(extracted_json.get("vat", 0))
                vat = st.number_input("VAT 7%", value=vat_value, step=0.1)

                total_value = safe_float(extracted_json.get("total", 0))
                total = st.number_input("ยอดรวมทั้งหมด", value=total_value, step=0.5)

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