import cv2
import streamlit as st

from llm_engine import call_typhoon_llm
from ocr_engine import (
    deskew_image,
    load_image_or_pdf,
    process_method_4_sharpening,
    run_typhoon_ocr,
)

st.set_page_config(page_title="RecAipt - Typhoon End-to-End", layout="wide")

st.title("📄 ระบบอ่านและสกัดข้อมูลจากใบเสร็จรับเงินอัตโนมัติ")
st.caption(
    "Automated Receipt Information Extraction System - "
    "ขอบเขตสถาปัตยกรรมโมเดลร่วมค่าย Typhoon End-to-End"
)

# 🎨 แทรกสไตล์ CSS ปรับแต่งโครงสร้างหน้าจอและกล่องข้อมูลให้โค้งมนสไตล์สีชมพูพาสเทล
st.markdown("""
    <style>
    /* 1. ปรับแต่งกล่องพื้นที่สำหรับลากและวางไฟล์อัปโหลดใบเสร็จ */
    .stFileUploader {
        border: 2px dashed #D47A9A !important;
        border-radius: 15px !important;
        background-color: #FCE4EC !important;
    }
    /* 2. ปรับแต่งฟอร์มกล่องข้อมูลฝั่งขวาให้ออกโทนขาวคลีน โค้งมน และมีเงามิติบางๆ */
    div[data-testid="stForm"] {
        border: 1px solid #F8BBD0 !important;
        border-radius: 20px !important;
        background-color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(212, 122, 154, 0.12);
        padding: 2.5rem !important;
    }
    /* 3. ปรับแต่งปุ่มกดบันทึก (Form Submit Button) ให้เป็นบล็อกสีชมพูเด่นชัดน่าใช้งาน */
    button[kind="formSubmit"] {
        background-color: #D47A9A !important;
        color: white !important;
        border-radius: 10px !important;
        border: none !important;
        width: 100% !important;
        font-weight: bold !important;
        font-size: 16px !important;
        padding: 0.6rem 0 !important;
        transition: background-color 0.3s ease, transform 0.1s ease;
    }
    button[kind="formSubmit"]:hover {
        background-color: #C26383 !important;
        color: white !important;
    }
    button[kind="formSubmit"]:active {
        transform: scale(0.98);
    }
    </style>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "เลือกไฟล์รูปภาพหรือไฟล์ PDF ใบเสร็จของคุณนำเข้า",
    type=["jpg", "jpeg", "png", "pdf"],
)

if uploaded_file is not None:
    file_bytes = uploaded_file.read()
    file_name = uploaded_file.name

    with st.spinner(
            "⏳ ขั้นตอนที่ 1: กำลังรันกระบวนการหมุนแก้องศาเอียงและใช้ฟิลเตอร์เพิ่มความคมชัด (Sharpen)..."
    ):
        img = load_image_or_pdf(file_bytes, file_name)
        if img is None:
            st.error("❌ ไฟล์เอกสารชำรุดหรือไม่รองรับพิกเซลรูปภาพนี้")
            st.stop()

        deskewed_img = deskew_image(img)
        processed_img = process_method_4_sharpening(deskewed_img)

    with st.spinner("⚡ ขั้นตอนที่ 2: ระบบกำลังนำภาพส่งวิเคราะห์ข้อความอักขระดิบผ่านทาง Typhoon OCR API..."):
        raw_text = run_typhoon_ocr(processed_img)

    if "[ERROR]" in raw_text or not raw_text.strip():
        st.error(raw_text if raw_text.strip() else "❌ ระบบตัวแปลงภาพไม่สามารถถอดคำออกจากหน้าใบเสร็จนี้ได้")
    else:
        with st.spinner("🤖 ขั้นตอนที่ 3: กำลังเรียบเรียงไวยากรณ์คำผิดและสกัดเป็นออบเจกต์ JSON ด้วย Typhoon LLM..."):
            extracted_json = call_typhoon_llm(raw_text)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("🖼️ ไฟล์เอกสารอ้างอิงหลังทำ Preprocessing")
            if len(processed_img.shape) == 2:
                display_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2RGB)
            else:
                display_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)
            st.image(display_img, use_container_width=True)

            with st.expander("📄 เปิดรีวิวสายข้อความดิบที่ดึงขึ้นคลาวด์ (Raw OCR Text)"):
                st.code(raw_text, language="text")

        with col2:
            st.subheader("📊 หน้าต่างยืนยันคุณลักษณะและข้อมูลดิจิทัล")

            if "error" in extracted_json:
                st.error(extracted_json["error"])
            else:
                with st.form("verified_receipt_form"):
                    merchant = st.text_input(
                        "ชื่อร้านค้า / นิติบุคคลผู้ขาย",
                        value=extracted_json.get("store_name", ""),
                    )
                    tax_id = st.text_input(
                        "เลขประจำตัวผู้เสียภาษี (Tax ID)",
                        value=extracted_json.get("tax_id", ""),
                    )
                    receipt_no = st.text_input(
                        "หมายเลขเลขที่เอกสารใบเสร็จ (Receipt No.)",
                        value=extracted_json.get("receipt_no", ""),
                    )
                    date_val = st.text_input(
                        "วันที่บันทึกธุรกรรมการค้า (YYYY-MM-DD)",
                        value=extracted_json.get("date", ""),
                    )

                    st.write("**📦 รายการตารางสินค้าและบริการ**")
                    items_list = extracted_json.get("items", []) or []
                    edited_items = []

                    for idx, item in enumerate(items_list):
                        c1, c2, c3 = st.columns([5, 2, 3])
                        with c1:
                            i_name = st.text_input(
                                f"ชื่อสินค้า #{idx + 1}",
                                value=item.get("name", ""),
                                key=f"n_{idx}",
                            )

                        # 🛡️ ป้องกันบั๊ก: จัดการการแปลงข้อมูลจำนวนชิ้น (qty) ให้ปลอดภัย
                        raw_qty = item.get("qty", 1)
                        if isinstance(raw_qty, str):
                            raw_qty = re.sub(r"[^\d.]", "", raw_qty)  # ตัดตัวอักษรแปลกปลอมออก
                        try:
                            default_qty = int(float(raw_qty)) if raw_qty else 1
                        except:
                            default_qty = 1

                        with c2:
                            i_qty = st.number_input(
                                "จำนวนชิ้น",
                                value=default_qty,
                                step=1,
                                key=f"q_{idx}",
                            )

                        # 🛡️ ป้องกันบั๊ก: จัดการล้างเครื่องหมายจุลภาค คอมมา ออกจากราคาสินค้าก่อนแปลงเป็น float
                        raw_price = item.get("unit_price", 0.0)
                        if isinstance(raw_price, str):
                            raw_price = raw_price.replace(",", "")
                        try:
                            default_price = float(raw_price) if raw_price else 0.0
                        except:
                            default_price = 0.0

                        with c3:
                            i_price = st.number_input(
                                "ราคา/ชิ้น",
                                value=default_price,
                                step=0.5,
                                key=f"p_{idx}",
                            )
                        edited_items.append(
                            {
                                "name": i_name,
                                "qty": i_qty,
                                "unit_price": i_price,
                                "amount": i_qty * i_price,
                            }
                        )

                    st.write("---")

                    # 🛡️ ล้างเครื่องหมายคอมมาออกจากข้อมูลสรุปยอดเงินรวมก่อนดึงมาแสดงผล
                    raw_subtotal = extracted_json.get("subtotal", 0.0)
                    if isinstance(raw_subtotal, str): raw_subtotal = raw_subtotal.replace(",", "")
                    try:
                        default_subtotal = float(raw_subtotal) if raw_subtotal else 0.0
                    except:
                        default_subtotal = 0.0

                    subtotal = st.number_input(
                        "มูลค่ายอดเงินรวมก่อนคิดภาษี (Subtotal)",
                        value=default_subtotal,
                        step=0.5,
                    )

                    raw_vat = extracted_json.get("vat", 0.0)
                    if isinstance(raw_vat, str): raw_vat = raw_vat.replace(",", "")
                    try:
                        default_vat = float(raw_vat) if raw_vat else 0.0
                    except:
                        default_vat = 0.0

                    vat = st.number_input(
                        "จำนวนยอดมูลค่าภาษีสะสม (VAT)",
                        value=default_vat,
                        step=0.1,
                    )

                    raw_total = extracted_json.get("total", 0.0)
                    if isinstance(raw_total, str): raw_total = raw_total.replace(",", "")
                    try:
                        default_total = float(raw_total) if raw_total else 0.0
                    except:
                        default_total = 0.0

                    total = st.number_input(
                        "ยอดสุทธิชำระเงินจริงทั้งสิ้น (Grand Total)",
                        value=default_total,
                        step=0.5,
                    )

                    pay_method = st.text_input(
                        "ช่องทางการจ่ายชำระเงิน (Payment Method)",
                        value=extracted_json.get("payment_method", ""),
                    )

                    save_btn = st.form_submit_button("💾 ยืนยันข้อมูลถูกต้องและกดจัดเก็บบันทึกข้อมูล")

                if save_btn:
                    st.success("🎉 ระบบลงตารางจัดโครงสร้างและบันทึกข้อมูลเข้าฐานข้อมูลเสร็จสิ้นแล้ว!")
                    st.json(
                        {
                            "store_name": merchant,
                            "tax_id": tax_id,
                            "receipt_no": receipt_no,
                            "date": date_val,
                            "items": edited_items,
                            "subtotal": subtotal,
                            "vat": vat,
                            "total": total,
                            "payment_method": pay_method,
                        }
                    )