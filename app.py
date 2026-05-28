import cv2
import numpy as np
import streamlit as st
from PIL import Image

# =========================================================
# PAGE CONFIG (ซ่อนแถบเมนูและ Sidebar ทั้งหมด)
# =========================================================
st.set_page_config(
    page_title="RecAipt - Receipt scanning tools",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# =========================================================
# LOAD CSS & INJECT NATIVE CORE INTERFACE OVERRIDE
# =========================================================
def load_css():
    # รองรับการดึงไฟล์ assets/style.css ของกลุ่มคุณตามปกติ
    try:
        with open("assets/style.css", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except:
        pass


load_css()

# 🎨 แทรก CSS หลักเพื่อควบคุมกรอบประสีชมพูและซ่อนปุ่มดั้งเดิมอย่างถาวร 100% ทุกสเตตัส
st.markdown("""
<style>
/* ── 1. ลบเมนูและฟุตเตอร์ส่วนเกินของ Streamlit ออกเกลี้ยง ── */
header, footer, [data-testid="stToolbar"], [data-testid="stSidebar"], #MainMenu {
    visibility: hidden !important;
    display: none !important;
    height: 0 !important;
}

/* ── 2. คุมโทนสีพื้นหลังขาวอมชมพูพาสเทลตามรายงานโครงงาน ── */
.stApp {
    background-color: #FFF2F6 !important;
}

.block-container {
    max-width: 100% !important;
    padding: 1.5rem 3rem !important;
}

/* ── 3. ล็อกมิติกราฟความสูงกล่องสแกนใบเสร็จ (Dropzone Container) ── */
section[data-testid="stFileUploader"] {
    max-width: 820px;
    margin: 0 auto !important;
    position: relative !important;
    height: 250px !important;
}

/* บังคับวาดเฟรมสี่เหลี่ยมผืนผ้าสีขาว มีเส้นประประจุสีชมพูล้อมรอบ */
section[data-testid="stFileUploader"] > div {
    background-color: #FFFFFF !important;
    border: 2px dashed #F4C6D5 !important;
    border-radius: 28px !important;
    height: 250px !important;
    min-height: 250px !important;
    position: relative !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 12px 35px rgba(74, 46, 53, 0.03) !important;
    padding: 0 !important;
}

/* สั่งทำลายและซ่อนปุ่ม Browse, ข้อความระบุขนาด และคำเตือนระบบดั้งเดิมออกทั้งหมด 100% */
div[data-testid="stFileUploaderDropzone"] svg,
div[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploaderFileHeader"],
[data-testid="stFileUploaderDeleteBtn"],
[data-testid="stFileUploaderFileName"],
[data-testid="stFileUploaderFile"],
[data-testid="stFileUploaderDropzoneInputButton"],
[data-testid="stFileUploaderFileSize"],
small[data-testid="stWidgetLabel-help"],
.stFileUploaderSection {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
}

/* ยืดแผ่นกระดาน Dropzone ให้ใหญ่กางเต็มกรอบขาว */
div[data-testid="stFileUploaderDropzone"] {
    background: transparent !important;
    border: none !important;
    width: 100% !important;
    height: 250px !important;
    position: absolute !important;
    top: 0 !important;
    left: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    z-index: 20 !important;
    cursor: pointer !important;
}
div[data-testid="stFileUploaderDropzone"] button {
    width: 100% !important;
    height: 100% !important;
    opacity: 0 !important;
    cursor: pointer !important;
}

/* 📌 หน้ากากจำลองจัดวางไอคอนเอกสารเดี่ยวและคำแนะนำมินิมอลกึ่งกลางเฟรมพอดีเป๊ะ */
section[data-testid="stFileUploader"]::after {
    content: "📄\\A\\A Choose or paste a file here (image or PDF)";
    white-space: pre-wrap;
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: #A3858C;
    font-size: 15px;
    text-align: center;
    font-weight: 400;
    z-index: 10;
    pointer-events: none;
    line-height: 1.3;
}
/* เจาะจงขยายฟอนต์ไอคอนใบเสร็จแถวแรกให้เด่นชัดน่าใช้งาน */
section[data-testid="stFileUploader"]::first-line {
    font-size: 52px;
    color: #4A2E35;
}

/* ── 4. สยบส่วนเกินและ Iframe Margins ในหน้าแสดงผลลัพธ์ ── */
div[data-testid="stHtml"] {
    padding: 0 !important;
    margin: 0 !important;
}
.result-wrapper {
    background: #FFFFFF;
    border-radius: 32px;
    padding: 35px;
    max-width: 1450px;
    margin: 0 auto !important;
    box-shadow: 0 12px 40px rgba(74, 46, 53, 0.04);
}

/* ตกแต่งฟอร์มดีไซน์ปุ่มจัดเก็บให้สวยงามขึ้น */
div[data-testid="stButton"] > button {
    background: #F8D7E3 !important;
    color: #A35271 !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    height: 46px !important;
}
div[data-testid="stButton"] > button:hover {
    background-color: #D47A9A !important;
    color: white !important;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# HELPERS
# =========================================================
def reset_app():
    st.session_state.clear()


def fake_ocr_result():
    return {
        "store_name": "7-Eleven ม.วลัยลักษณ์",
        "receipt_no": "A102938",
        "date": "2026-05-29",
        "items": [
            {"name": "Milk", "qty": 2, "unit_price": 25.0},
            {"name": "Bread", "qty": 1, "unit_price": 35.0},
            {"name": "Coffee", "qty": 1, "unit_price": 45.0}
        ],
        "subtotal": 130.0,
        "vat": 9.1,
        "total": 139.1
    }


# =========================================================
# HEADER COMPONENT (กล่องสีขาวด้านบนเรียบหรู)
# =========================================================
st.markdown("""
<div class="header-bar">
    <div class="logo-text">📄 RecAipt</div>
    <div class="lang-pill">English ▾</div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# PAGE 1 : UPLOAD INTERFACE (ถอดแบบตามรายงานรูปเล่มหน้า 41)
# =========================================================
if "processed_img" not in st.session_state:

    st.markdown("<div class='hero-title'>Receipt scanning and data collection tools</div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>Upload receipt image or PDF document</div>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload Receipt", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

    # =====================================================
    # PREVIEW & PIPELINE TRIGGER
    # =====================================================
    if uploaded_file is not None:
        st.markdown(
            "<div class='preview-title' style='text-align:center; color:#4A2E35; font-weight:bold; margin-top:30px; margin-bottom:15px;'>Uploaded Preview</div>",
            unsafe_allow_html=True)

        image = Image.open(uploaded_file)

        # จัดพิกัดให้อยู่ตรงกลางสวยงามก่อนกดประมวลผล
        col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
        with col_p2:
            st.image(image, use_container_width=True)

            if st.button("🚀 Process Receipt", use_container_width=True):
                with st.spinner("Processing receipt..."):
                    img_array = np.array(image)
                    if len(img_array.shape) == 3:
                        img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

                    st.session_state["processed_img"] = img_array
                    st.session_state["raw_text"] = "7-Eleven\nMilk 25\nBread 35\nCoffee 45"
                    st.session_state["extracted_json"] = fake_ocr_result()
                st.rerun()

# =========================================================
# PAGE 2 : RESULT INTERFACE (ถอดแบบตามรายงานรูปเล่มหน้า 42)
# =========================================================
else:
    processed_img = st.session_state["processed_img"]
    raw_text = st.session_state["raw_text"]
    extracted_json = st.session_state["extracted_json"]

    # ปุ่มกดย้อนกลับทรงเหลี่ยมมนพาสเทล
    st.button("← Back", key="back_btn", on_click=reset_app)

    st.markdown('<div class="result-wrapper">', unsafe_allow_html=True)
    left_col, right_col = st.columns([1, 1])

    # ── ฝั่งซ้าย: พรีวิวรูปใบเสร็จต้นฉบับอ้างอิง ──
    with left_col:
        st.markdown(
            "<div class='section-title' style='color:#4A2E35; font-weight:bold; margin-bottom:15px;'>🖼️ Receipt Preview</div>",
            unsafe_allow_html=True)
        st.markdown('<div class="image-card">', unsafe_allow_html=True)

        display_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)
        st.image(display_img, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        with st.expander("📄 Raw OCR Text"):
            st.code(raw_text)

    # ── ฝั่งขวา: การ์ดฟอร์มรายละเอียดใบเสร็จสีชมพูพาสเทล (RecAipt Card) ──
    with right_col:
        st.markdown('<div class="receipt-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="receipt-title" style="text-align:center; color:#4A2E35; font-size:20px; font-weight:bold; margin-bottom:25px;">รายละเอียดใบเสร็จ</div>',
            unsafe_allow_html=True)

        with st.form("verified_receipt_form"):
            merchant = st.text_input("🏪 ร้านค้า / ผู้ขาย", value=extracted_json.get("store_name", ""))
            receipt_no = st.text_input("🧾 เลขที่ใบเสร็จ", value=extracted_json.get("receipt_no", ""))
            date_val = st.text_input("📅 วันที่", value=extracted_json.get("date", ""))

            st.markdown("<p style='font-weight:bold; margin-top:20px; color:#4A2E35;'>📦 รายการสินค้า</p>",
                        unsafe_allow_html=True)
            items = extracted_json.get("items", [])
            edited_items = []

            for idx, item in enumerate(items):
                c1, c2, c3 = st.columns([5, 2, 3])
                with c1:
                    i_name = st.text_input(f"รายการ #{idx + 1}", value=item.get("name", ""), key=f"n_{idx}")
                with c2:
                    i_qty = st.number_input("จำนวน", value=int(item.get("qty", 1)), step=1, key=f"q_{idx}")
                with c3:
                    i_price = st.number_input("ราคา", value=float(item.get("unit_price", 0.0)), step=0.5,
                                              key=f"p_{idx}")

                edited_items.append({
                    "name": i_name,
                    "qty": i_qty,
                    "unit_price": i_price,
                    "amount": i_qty * i_price
                })

            st.markdown("---")
            subtotal = st.number_input("ยอดรวมก่อนภาษี (Subtotal)", value=float(extracted_json.get("subtotal", 0.0)),
                                       step=0.5)
            vat = st.number_input("VAT 7% :", value=float(extracted_json.get("vat", 0.0)), step=0.1)
            total = st.number_input("ยอดรวม :", value=float(extracted_json.get("total", 0.0)), step=0.5)

            export_btn = st.form_submit_button("📤  ส่งออก")

        if export_btn:
            st.success("🎉 บันทึกและดึงข้อมูลเข้าสู่ฐานข้อมูลเสร็จสิ้นเรียบร้อยแล้ว!")
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