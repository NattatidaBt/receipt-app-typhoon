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
# CUSTOM CSS
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
   FILE UPLOADER FRAME
========================================================= */
section[data-testid="stFileUploader"] {
    max-width: 850px;
    margin: auto;
    position: relative;
}

section[data-testid="stFileUploader"] > div {
    background-color: white !important;
    border: 2px dashed #F4C6D5 !important;
    border-radius: 30px !important;
    min-height: 280px !important;
    box-shadow: 0 12px 40px rgba(0,0,0,0.03);
}

[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploaderDropzone"] svg,
.stFileUploaderSection,
small[data-testid="stWidgetLabel-help"] {
    display: none !important;
    visibility: hidden !important;
}

[data-testid="stFileUploaderDropzoneInputButton"],
[data-testid="stFileUploaderFileSize"],
[data-testid="stFileUploaderFileHeader"],
[data-testid="stFileUploaderDeleteBtn"],
[data-testid="stFileUploaderFileName"],
[data-testid="stFileUploaderFile"] {
    opacity: 0 !important;
    position: absolute !important;
    z-index: -1 !important;
    height: 0 !important;
    width: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
}

[data-testid="stFileUploaderDropzone"] {
    background: transparent !important;
    border: none !important;
    min-height: 280px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

/* =========================================================
   CUSTOM UPLOAD CONTENT OVERLAY
========================================================= */
.upload-overlay {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    z-index: 5;
    pointer-events: none;
    width: 100%;
}

.custom-upload-box {
    text-align: center;
}

.upload-icon {
    font-size: 54px;
    margin-bottom: 14px;
    color: #4A2E35;
}

.upload-text {
    color: #A3858C;
    font-size: 15px;
    font-weight: 400;
}

/* =========================================================
   RESULT PAGE WRAPPER
========================================================= */
.result-wrapper {
    background: white;
    border-radius: 28px;
    padding: 28px;
    max-width: 1400px;
    margin: auto;
    border: 1px solid #F4E0E8;
    box-shadow: 0 10px 35px rgba(0,0,0,0.03);
}

div[data-testid="stHorizontalBlock"] {
    gap: 28px !important;
    align-items: flex-start !important;
}

/* =========================================================
   LEFT COLUMN: IMAGE CARD
========================================================= */
.img-card-wrap {
    background: #FAFAFA;
    border-radius: 20px;
    padding: 16px;
    border: 1px solid #F4C6D5;
}

/* =========================================================
   RIGHT COLUMN: DETAIL CARD
========================================================= */
.detail-card {
    background: white;
    border-radius: 20px;
    border: 1px solid #F4C6D5;
    overflow: hidden;
}

.detail-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px 14px;
    border-bottom: 1px solid #F4E0E8;
}

.detail-card-title {
    font-size: 16px;
    font-weight: 600;
    color: #4A2E35;
}

.header-icon-btns {
    display: flex;
    gap: 6px;
}

.header-icon-btn {
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 18px;
    padding: 4px 7px;
    border-radius: 7px;
    color: #C97D98;
    line-height: 1;
}

.header-icon-btn:hover {
    background: #FFF0F5;
}

.detail-card-body {
    padding: 16px 20px;
}

/* Receipt type badge */
.receipt-type-badge {
    display: inline-block;
    background: #FFF0F5;
    color: #A35271;
    border: 1px solid #F4C6D5;
    border-radius: 8px;
    font-size: 12px;
    padding: 4px 12px;
    margin-bottom: 16px;
}

/* Info rows */
.info-rows {
    margin-bottom: 4px;
}

.info-row {
    display: flex;
    align-items: baseline;
    gap: 8px;
    font-size: 13px;
    margin-bottom: 10px;
}

.info-label {
    color: #C29BA4;
    min-width: 110px;
    flex-shrink: 0;
}

.info-value {
    color: #4A2E35;
    font-weight: 500;
}

/* Divider */
.section-divider {
    border: none;
    border-top: 1px solid #F4E0E8;
    margin: 14px 0;
}

/* Section label */
.section-label {
    font-size: 12px;
    color: #C29BA4;
    margin-bottom: 10px;
}

/* Items table */
.items-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    margin-bottom: 4px;
}

.items-table th {
    color: #C29BA4;
    font-weight: 400;
    padding: 5px 6px 10px;
    border-bottom: 1px solid #F4E0E8;
    text-align: center;
}

.items-table th:nth-child(2) {
    text-align: left;
}

.items-table td {
    padding: 9px 6px;
    color: #4A2E35;
    text-align: center;
    vertical-align: middle;
}

.items-table td:nth-child(2) {
    text-align: left;
}

.items-table .num-col {
    color: #C29BA4;
    font-size: 12px;
}

/* Totals */
.totals-section {
    padding-top: 4px;
}

.total-row {
    display: flex;
    justify-content: space-between;
    font-size: 13px;
    color: #A07A85;
    margin-bottom: 8px;
}

.total-row.grand-total {
    color: #4A2E35;
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 0;
}

/* Detail card footer */
.detail-card-footer {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 8px;
    padding: 12px 20px 16px;
    border-top: 1px solid #F4E0E8;
}

.footer-icon-btn {
    background: white;
    border: 1px solid #F4C6D5;
    color: #A35271;
    border-radius: 10px;
    width: 38px;
    height: 38px;
    font-size: 16px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

.footer-icon-btn:hover {
    background: #FFF0F5;
}

.export-btn {
    background: #F8D7E3;
    color: #A35271;
    border: none;
    border-radius: 10px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 38px;
}

.export-btn:hover {
    background: #F0C0D5;
}

/* =========================================================
   BACK BUTTON (ใต้รูปฝั่งซ้าย)
========================================================= */
div.stButton > button {
    background-color: #F8D7E3 !important;
    color: #A35271 !important;
    border-radius: 12px !important;
    border: none !important;
    font-weight: bold !important;
}

.back-btn-wrap div.stButton > button {
    width: 42px !important;
    height: 42px !important;
    padding: 0 !important;
    font-size: 18px !important;
}

.export-submit-btn div.stButton > button {
    width: 100% !important;
    height: 42px !important;
    font-size: 14px !important;
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

    uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png", "pdf"], key="uploader_widget")

    st.markdown("""
    <div class="upload-overlay">
        <div class="custom-upload-box">
            <div class="upload-icon">📄</div>
            <div class="upload-text">Choose or paste a file here (image or PDF)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -----------------------------------------------------
    # PIPELINE EXECUTION
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
    processed_img  = st.session_state["processed_img"]
    raw_text       = st.session_state["raw_text"]
    extracted_json = st.session_state["extracted_json"]

    st.markdown('<div class="result-wrapper">', unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 1])

    # ----------------------------------------------------------
    # LEFT COLUMN: Receipt Image
    # ----------------------------------------------------------
    with col_left:
        st.markdown('<div class="img-card-wrap">', unsafe_allow_html=True)

        # แสดงรูปใบเสร็จ
        if len(processed_img.shape) == 2:
            display_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2RGB)
        else:
            display_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)

        st.image(display_img, use_container_width=True)

        # Raw OCR expander
        with st.expander("📄 Raw OCR Text"):
            st.code(raw_text, language="text")

        # Back button
        st.markdown('<div class="back-btn-wrap">', unsafe_allow_html=True)
        st.button("←", key="back_to_upload", on_click=reset_app)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)  # img-card-wrap

    # ----------------------------------------------------------
    # RIGHT COLUMN: Receipt Details
    # ----------------------------------------------------------
    with col_right:
        if "error" in extracted_json:
            st.error(extracted_json["error"])
        else:
            # ── ดึงข้อมูลจาก JSON ──
            merchant      = extracted_json.get("store_name", "—") or "—"
            receipt_no    = extracted_json.get("receipt_no", "—") or "—"
            date_val      = extracted_json.get("date", "—") or "—"
            receipt_type  = extracted_json.get("receipt_type", "ใบกำกับภาษีอย่างย่อ") or "ใบกำกับภาษีอย่างย่อ"
            items_list    = extracted_json.get("items", []) or []
            subtotal_val  = safe_float(extracted_json.get("subtotal", 0))
            vat_val       = safe_float(extracted_json.get("vat", 0))
            total_val     = safe_float(extracted_json.get("total", 0))

            # ── สร้าง HTML ของตารางสินค้า ──
            rows_html = ""
            for idx, item in enumerate(items_list):
                name  = item.get("name", "")
                qty   = safe_int(item.get("qty", 1))
                price = safe_float(item.get("unit_price", 0))
                amt   = qty * price
                rows_html += f"""
                <tr>
                    <td class="num-col">{idx + 1}</td>
                    <td>{name}</td>
                    <td>{qty}</td>
                    <td>{price:,.2f}</td>
                    <td style="text-align:right">{amt:,.2f}</td>
                </tr>"""

            # ── แสดง Detail Card (HTML ทั้งก้อน) ──
            st.markdown(f"""
            <div class="detail-card">

                <div class="detail-card-header">
                    <span class="detail-card-title">รายละเอียดใบเสร็จ</span>
                    <div class="header-icon-btns">
                        <button class="header-icon-btn" title="แก้ไข">✏️</button>
                        <button class="header-icon-btn" title="ลบ">🗑️</button>
                    </div>
                </div>

                <div class="detail-card-body">
                    <span class="receipt-type-badge">{receipt_type}</span>

                    <div class="info-rows">
                        <div class="info-row">
                            <span class="info-label">ร้านค้า / ผู้ขาย :</span>
                            <span class="info-value">{merchant}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">เลขที่ใบเสร็จ :</span>
                            <span class="info-value">{receipt_no}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">วันที่ :</span>
                            <span class="info-value">{date_val}</span>
                        </div>
                    </div>

                    <hr class="section-divider">
                    <div class="section-label">รายการสินค้า</div>

                    <table class="items-table">
                        <thead>
                            <tr>
                                <th style="width:36px">ลำดับ</th>
                                <th>รายการ</th>
                                <th style="width:52px">จำนวน</th>
                                <th style="width:64px">ราคา</th>
                                <th style="width:64px;text-align:right">รวม</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows_html if rows_html else '<tr><td colspan="5" style="text-align:center;color:#C29BA4;padding:16px">ไม่พบรายการสินค้า</td></tr>'}
                        </tbody>
                    </table>

                    <hr class="section-divider">

                    <div class="totals-section">
                        {f'<div class="total-row"><span>ยอดก่อน VAT :</span><span>{subtotal_val:,.2f} บาท</span></div>' if subtotal_val else ''}
                        {f'<div class="total-row"><span>VAT 7% :</span><span>{vat_val:,.2f} บาท</span></div>' if vat_val else ''}
                        <div class="total-row grand-total">
                            <span>ยอดรวม :</span>
                            <span>{total_val:,.2f} บาท</span>
                        </div>
                    </div>
                </div>

                <div class="detail-card-footer">
                    <button class="footer-icon-btn" title="คัดลอก">📋</button>
                    <button class="footer-icon-btn" title="แชร์">↑</button>
                </div>

            </div>
            """, unsafe_allow_html=True)

            # ── ปุ่ม ส่งออก (ต้องใช้ Streamlit เพื่อ trigger Python) ──
            st.markdown('<div class="export-submit-btn">', unsafe_allow_html=True)
            if st.button("📤 ส่งออก", key="export_btn", use_container_width=True):
                st.success("🎉 บันทึกข้อมูลเรียบร้อยแล้ว")
                export_items = []
                for item in items_list:
                    qty   = safe_int(item.get("qty", 1))
                    price = safe_float(item.get("unit_price", 0))
                    export_items.append({
                        "name":       item.get("name", ""),
                        "qty":        qty,
                        "unit_price": price,
                        "amount":     qty * price,
                    })
                st.json({
                    "store_name": merchant,
                    "receipt_no": receipt_no,
                    "date":       date_val,
                    "items":      export_items,
                    "subtotal":   subtotal_val,
                    "vat":        vat_val,
                    "total":      total_val,
                })
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # result-wrapper