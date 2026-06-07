import json
import re

import requests
import streamlit as st


_THAI_CORRECTIONS = {
    "ภาษีมูลค่าเพิน": "ภาษีมูลค่าเพิ่ม",
    "ภาษีมูลคาเพิม": "ภาษีมูลค่าเพิ่ม",
    "ยอดรวมทงหมด": "ยอดรวมทั้งหมด",
    "ยอดรวมทงัหมด": "ยอดรวมทั้งหมด",
    "ใบเสรจ": "ใบเสร็จ",
    "ใบเสรจรบเงน": "ใบเสร็จรับเงิน",
    "เลขทใบ": "เลขที่ใบ",
    "เลขท ": "เลขที่ ",
    "วนท": "วันที่",
    "วนที": "วันที่",
    "เลขผเู้สย": "เลขผู้เสียภาษี",
    "เลขผู้เสยี": "เลขผู้เสียภาษี",
    "จำนวนเงน": "จำนวนเงิน",
    "รวมเปน": "รวมเป็น",
    "มูลคา": "มูลค่า",
    "ราคา/หนวย": "ราคา/หน่วย",
    "จำนวน/หนวย": "จำนวน/หน่วย",
}


def rule_based_correct(text):
    for wrong, correct in _THAI_CORRECTIONS.items():
        text = text.replace(wrong, correct)

    lines = text.split("\n")
    corrected_lines = []
    for line in lines:
        digit_count = sum(1 for char in line if char.isdigit())
        if len(line) > 0 and (digit_count / max(len(line), 1)) > 0.3:
            line = re.sub(r"\bO\b", "0", line)
            line = re.sub(r"\bl\b", "1", line)
        corrected_lines.append(line)
    return "\n".join(corrected_lines)


def clean_and_format_ocr(text):
    text = re.sub(r"```[a-zA-Z]*\n", "", text)
    text = text.replace("\n```", "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("**", "")

    keywords = [
        r"(POS No\.?)",
        r"(Term\.?\s*No\.?)",
        r"(Staff\s*:?)",
        r"(Cashier\s*:?)",
        r"(Date\s*:?)",
        r"(Time\s*:?)",
        r"(TAX ID\s*:?)",
        r"(Rec No\.?)",
        r"(No\.CAS)",
        r"(Description Amount)",
        r"(รายการ)",
        r"(ราคาต่อหน่วย)",
        r"(?<!\n)(\b\d+\s*\))",
        r"(?<!\n)(\b\d+\.\s+[A-Za-zก-๙])",
        r"(1 EA @)",
        r"(Sub Total)",
        r"(Subtotal)",
        r"(Total\(VAT)",
        r"(Total Amount)",
        r"(ค่าพื้นที่ห่างไกล:?)",
        r"(ค่าส่ง:?)",
        r"(ส่วนลดรวม:?)",
        r"(ยอดรวม:?)",
        r"(ยอดสุทธิ:?)",
        r"(QR Promptpay)",
        r"(รับเงิน:?)",
        r"(เงินทอน:?)",
        r"(ขอบคุณ)",
        r"(สแกน QR)",
        r"(ผู้ส่ง)",
    ]
    for keyword in keywords:
        text = re.sub(keyword, r"\n\1", text, flags=re.IGNORECASE)

    # Retail receipts often print several items in one OCR line. Split after money-like
    # amounts when the next token looks like a new Thai/English item name.
    text = re.sub(r"(?<=\d[.,]\d{2})\s+(?=[A-Za-zก-๙])", "\n", text)

    lines = text.split("\n")
    formatted = []
    for line in lines:
        line = line.strip()
        line = re.sub(r"^[-#*]+\s*", "", line)
        if not line:
            continue
        line = re.sub(r"\s+", " ", line)
        formatted.append(line)
    return "\n".join(formatted)


def call_typhoon_llm(ocr_text):
    url = "https://api.opentyphoon.ai/v1/chat/completions"
    api_key = st.secrets["OPENTYPHOON_API_KEY"]

    corrected_ocr = rule_based_correct(ocr_text)
    final_ocr_input = clean_and_format_ocr(corrected_ocr)

    system_prompt = """
คุณคือผู้เชี่ยวชาญด้านการอ่านใบเสร็จ ใบกำกับภาษี และเอกสารทางการเงินภาษาไทย

หน้าที่ของคุณคือ

1. วิเคราะห์ข้อความ OCR
2. แก้ข้อความ OCR ที่ผิดตามบริบท
3. แยกข้อมูลลง JSON ให้ตรงโครงสร้าง
4. ห้ามเดาข้อมูล
5. ถ้าไม่มีข้อมูลให้ใช้ null
6. ตอบกลับเฉพาะ JSON เท่านั้น
7. ห้ามมีคำอธิบาย
8. ห้ามใส่ markdown
9. ห้ามใส่ ```json
"""

    user_prompt = f"""
ข้อความ OCR:

----------------
{final_ocr_input}
----------------

ให้สกัดข้อมูลออกมาเป็น JSON ตาม Schema นี้

{{
  "document_type": "ใบกำกับภาษีเต็มรูป|ใบกำกับภาษีอย่างย่อ|ใบเสร็จรับเงิน|อื่นๆ",

  "seller": {{
    "name": null,
    "tax_id": null,
    "address": null,
    "telephone": null
  }},

  "buyer": {{
    "name": null,
    "tax_id": null,
    "address": null
  }},

  "document_number": null,

  "document_date": null,

  "tax_included": true,

  "amount_before_tax": null,

  "vat_rate": null,

  "vat_amount": null,

  "grand_total": null,

  "payment_method": null,

  "items": [
    {{
      "item_description": null,
      "quantity": null,
      "unit_price": null,
      "subtotal": null
    }}
  ]
}}

กฎเพิ่มเติม

- ถ้ามีข้อมูลผู้ซื้อให้ใส่ใน buyer
- ถ้าไม่มีผู้ซื้อให้ buyer เป็น null
- ถ้าพบคำว่า ABB ให้ document_type = ใบกำกับภาษีอย่างย่อ
- ถ้ามีชื่อผู้ซื้อและเลขผู้เสียภาษีผู้ซื้อ ให้ document_type = ใบกำกับภาษีเต็มรูป
- document_date ใช้รูปแบบ YYYY-MM-DD
- amount_before_tax คือยอดก่อน VAT
- vat_amount คือจำนวน VAT
- grand_total คือยอดสุทธิ
- quantity ต้องเป็นตัวเลข
- unit_price ต้องเป็นตัวเลข
- subtotal ต้องเป็นตัวเลข
- items ต้องแยกเป็นรายแถวสินค้า/บริการเท่านั้น: 1 object ต่อ 1 รายการ ห้ามรวมสินค้าหลายรายการไว้ใน item_description เดียว
- ถ้าใบเสร็จเป็นร้านค้าปลีก เช่น 7-Eleven หรือแสดง VAT รวมในราคา ให้ tax_included = true และห้ามบวก VAT เพิ่มซ้ำจากยอดสินค้า
- ถ้าไม่เห็น VAT แยกชัดเจน แต่เห็นยอดสุทธิรวม ให้ประมาณ amount_before_tax = grand_total / 1.07 และ vat_amount = grand_total - amount_before_tax เฉพาะกรณีมีข้อความบ่งชี้ว่าเป็น VAT 7%

ตอบกลับเฉพาะ JSON เท่านั้น
"""

    payload = {
        "model": "typhoon-v2.5-30b-a3b-instruct",
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        "temperature": 0,
        "max_tokens": 3000,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60,
        )

        response.raise_for_status()

        data = response.json()

        content = data["choices"][0]["message"]["content"].strip()

        content = re.sub(
            r"```json",
            "",
            content,
            flags=re.IGNORECASE
        )

        content = re.sub(
            r"```",
            "",
            content
        )

        json_match = re.search(
            r"\{.*\}",
            content,
            re.DOTALL
        )

        if json_match:
            return json.loads(
                json_match.group(0)
            )

        return json.loads(content)

    except Exception as exc:
        return {
            "error": f"LLM Parse Error: {str(exc)}"
        }
