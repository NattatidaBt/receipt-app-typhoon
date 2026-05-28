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
                        with c2:
                            i_qty = st.number_input(
                                "จำนวนชิ้น",
                                value=int(item.get("qty", 1)) if item.get("qty") else 1,
                                step=1,
                                key=f"q_{idx}",
                            )
                        with c3:
                            i_price = st.number_input(
                                "ราคา/ชิ้น",
                                value=float(item.get("unit_price", 0.0))
                                if item.get("unit_price")
                                else 0.0,
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
                    subtotal = st.number_input(
                        "มูลค่ายอดเงินรวมก่อนคิดภาษี (Subtotal)",
                        value=float(extracted_json.get("subtotal", 0.0))
                        if extracted_json.get("subtotal")
                        else 0.0,
                        step=0.5,
                    )
                    vat = st.number_input(
                        "จำนวนยอดมูลค่าภาษีสะสม (VAT)",
                        value=float(extracted_json.get("vat", 0.0))
                        if extracted_json.get("vat")
                        else 0.0,
                        step=0.1,
                    )
                    total = st.number_input(
                        "ยอดสุทธิชำระเงินจริงทั้งสิ้น (Grand Total)",
                        value=float(extracted_json.get("total", 0.0))
                        if extracted_json.get("total")
                        else 0.0,
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
