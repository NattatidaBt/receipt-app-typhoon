import json
import re
from datetime import datetime

import requests
import streamlit as st

# ==================================================
# ⚙️ CONFIG (ค่าที่ดีที่สุดจากผลทดลอง)
# ==================================================
MODEL_NAME = "typhoon-v2.5-30b-a3b-instruct"
EXTRACT_TEMPERATURE = 0.0     # Mode1_Standard_SFT @ Temp 0.0 = ผลดีที่สุด
VERIFY_TEMPERATURE = 0.0
LLM_MAX_TOKENS = 2048
MAX_EXTRACTION_ATTEMPTS = 3

USE_SELF_VERIFICATION = True   # เปิดรอบตรวจสอบซ้ำ (สำคัญมากสำหรับฟิลด์ตัวเลข)

# ==================================================
# 📋 GOLDEN SCHEMA — ต้องตรงกับ schema ที่ใช้วัดผล (มี vat_amount ไม่ใช่ total_before_discount)
# ==================================================
GOLDEN_SCHEMA = {
    "document_header": {
        "document_type": None,
        "document_date": None,
        "document_number": None
    },
    "merchant_and_buyer": {
        "merchant_name": None,
        "buyer_name": None,
        "merchant_tax_id": None,
        "buyer_tax_id": None
    },
    "line_items": [
        {
            "item_name": None,
            "quantity": None,
            "unit_price": None,
            "total_price": None
        }
    ],
    "summary": {
        "subtotal": None,
        "total_discount": None,
        "vat_amount": None,
        "net_amount": None
    }
}

schema_str = json.dumps(GOLDEN_SCHEMA, indent=2, ensure_ascii=False)

_CURRENT_BE_YY = (datetime.now().year + 543) % 100

# ==================================================
# 📅 กฎวันที่
# ==================================================
DATE_RULE_NOTE = (
    "\n\nกฎเรื่องวันที่ (สำคัญมาก): document_date ต้องอยู่ในรูปแบบ \"วว/ดด/ปป\" แบบไทยเท่านั้น "
    "(วันสองหลัก/เดือนสองหลัก/ปี พ.ศ. สองหลักท้าย) ห้ามแปลงเป็น ค.ศ. และห้ามใช้รูปแบบอื่น เช่น YYYY-MM-DD เด็ดขาด\n"
    "ตัวอย่าง: ถ้าเอกสารเขียนว่า \"29 พ.ย. 2568\" หรือ \"29/11/2568\" ให้ตอบเป็น \"29/11/68\" เท่านั้น\n"
    "ถ้าปีในเอกสารเป็น ค.ศ. อยู่แล้ว ให้แปลงกลับเป็น พ.ศ. 2 หลักก่อน (เช่น ค.ศ. 2025 -> พ.ศ. 68) แล้วค่อยจัดรูปแบบ วว/ดด/ปป\n"
    f"ปี พ.ศ. ต้องใกล้เคียงปัจจุบัน (ปัจจุบันคือ พ.ศ. {_CURRENT_BE_YY:02d}) ห้ามใส่ปีที่มากกว่านี้เกิน 1 ปี"
)

# ==================================================
# 💰 กฎยอดเงิน summary
# ==================================================
SUMMARY_RULE_NOTE = (
    "\n\nกฎเรื่องยอดเงินใน summary (สำคัญมาก):\n"
    "- ⚠️ summary ต้องมีครบ 4 key เท่านี้เสมอ: subtotal, total_discount, vat_amount, net_amount "
    "ห้ามขาด key ใดไปแม้จะหาไม่เจอ (ให้ใส่ 0 หรือ null ตามกฎแต่ละ key แทน) และ ⚠️ ห้ามสร้าง key อื่นที่ไม่มีในโครงสร้างเด็ดขาด "
    "เช่น ห้ามใช้ \"total_before_discount\" หรือชื่ออื่นที่คล้ายกัน ถ้าจะสื่อความหมายนั้นให้ใช้ subtotal แทน\n"
    "- subtotal = ยอดรวมราคาสินค้าทุกชิ้นก่อนหักส่วนลด และก่อนรวม VAT\n"
    "- total_discount = ส่วนลดที่หักออกจากยอดรวม ถ้าไม่มีส่วนลดในเอกสารให้ใส่ 0 (ห้ามใส่ null)\n"
    "- vat_amount = ภาษีมูลค่าเพิ่ม (VAT) ที่แสดงแยกในเอกสาร ถ้าเอกสารไม่มี VAT แยกแสดงให้ใส่ 0 (ห้ามใส่ null)\n"
    "- net_amount = ยอดสุทธิที่ต้องชำระจริง = subtotal - total_discount + vat_amount\n"
    "- ส่วนลดในใบเสร็จอาจไม่ได้เขียนคำว่า \"ส่วนลด\" ตรงๆ ให้จับคำเหล่านี้ว่าเป็นส่วนลดเสมอ: "
    "คูปอง, Coupon, Voucher, โปรโมชั่น, Promotion, Shopee Coins, Coins, Cashback, ส่วนลดพิเศษ, Discount "
    "หากพบตัวเลขติดคำเหล่านี้ ให้ใส่ค่านั้นลงใน total_discount เสมอ อย่าละเลยหรือใส่ 0 ถ้ามีตัวเลขปรากฏจริง"
)

# ==================================================
# 🧑‍💼 กฎ merchant / buyer
# ==================================================
MERCHANT_BUYER_RULE_NOTE = (
    "\n\nกฎเรื่อง merchant_name กับ buyer_name (สำคัญมาก ห้ามสลับกันเด็ดขาด):\n"
    "- merchant_name คือ \"ผู้ขาย/ผู้ออกใบเสร็จ\" เสมอ ไม่ใช่ชื่อที่ตัวใหญ่สุดหรืออยู่บนสุดของเอกสาร "
    "ให้สังเกตจากตำแหน่งของโลโก้/หัวกระดาษ หรือคำกำกับ เช่น \"ผู้ขาย\", \"ร้าน\", \"ออกโดย\", \"Sold by\", \"Seller\", "
    "หรือ merchant_tax_id ที่พิมพ์กำกับไว้ใต้ชื่อนั้นในหัวเอกสาร\n"
    "- ถ้าเอกสารมีทั้ง \"ชื่อแบรนด์/สาขาหน้าร้าน\" (เช่น ชื่อร้านสะดวกซื้อ ชื่อสาขา) และ \"ชื่อนิติบุคคลเต็ม\" (ขึ้นต้นด้วย "
    "\"บริษัท\"/\"ห้างหุ้นส่วนจำกัด\"/\"หจก.\" อยู่ใกล้เลขผู้เสียภาษี) ให้เลือก \"ชื่อนิติบุคคลเต็ม\" เสมอ เพราะเป็นชื่อที่ใช้ในการออกใบกำกับภาษีจริง "
    "ห้ามใช้ชื่อแบรนด์/สาขาแทนแม้จะเห็นเด่นกว่า\n"
    "- ห้ามนำคำโปรย/สโลแกน/คำแปลภาษาอังกฤษ/ที่อยู่ ที่ต่อท้ายชื่อร้านมารวมไว้ใน merchant_name เด็ดขาด ให้ตัดออกให้เหลือแค่ชื่อร้าน/นิติบุคคลล้วนๆ\n"
    "- buyer_name คือ \"ผู้ซื้อ/ลูกค้า\" เสมอ ให้สังเกตจากคำกำกับ เช่น \"ลูกค้า\", \"ผู้ซื้อ\", \"นามผู้ซื้อ\", "
    "\"ในนาม\", \"Bill to\", \"Customer\", \"Ship to\" ซึ่งมักอยู่ใต้ส่วนหัวของ merchant หรือในกล่องแยกต่างหาก\n"
    "- ถ้าไม่มีคำกำกับชัดเจน ให้ถือว่าชื่อที่อยู่ในตำแหน่งหัวกระดาษ/โลโก้บนสุดคือ merchant "
    "และชื่อที่อยู่ในบรรทัดถัดมา (มักขึ้นต้นด้วย \"ในนาม\"/\"ลูกค้า\") คือ buyer\n"
    "- ห้ามเดาว่าชื่อที่ตัวหนา/ตัวใหญ่/เห็นชัดที่สุดคือ merchant เสมอไป บางใบชื่อร้านตัวจริงพิมพ์ตัวเล็กหรืออยู่มุมล่าง "
    "ให้ยึดคำกำกับ (ผู้ขาย/ลูกค้า) เป็นหลัก ไม่ใช่ขนาดตัวอักษร\n"
    "- ⚠️ ห้ามตัดสิน merchant/buyer จาก \"ความน่าเชื่อถือ\" หรือ \"ขนาดองค์กร\" ของชื่อเด็ดขาด บางใบร้านเล็กขายของให้ "
    "หน่วยงาน/บริษัท/มหาวิทยาลัยขนาดใหญ่ ชื่อที่ฟังดูเป็นองค์กรใหญ่ (เช่น \"มหาวิทยาลัย...\", \"บริษัท...จำกัด (มหาชน)\") "
    "ก็เป็น buyer (ผู้ซื้อ) ได้ปกติ ถ้ามีคำกำกับ \"ผู้ซื้อ\"/\"ชื่อผู้ซื้อ\"/\"ข้อมูลผู้ซื้อ\" อยู่ติดกัน ให้เชื่อคำกำกับเสมอ "
    "ห้ามเปลี่ยนไปเป็น merchant เองเพียงเพราะชื่อฟังดูใหญ่กว่าร้าน\n"
    "- คำว่า \"ข้อมูลสมาชิก\" ตามด้วยชื่อคน (มักเจอในใบเสร็จร้านสะดวกซื้อ/ร้านค้าปลีกที่มีระบบสมาชิก) ก็นับเป็นสัญญาณของ "
    "buyer_name เช่นกัน แม้จะไม่มีคำว่า \"ผู้ซื้อ\"/\"ลูกค้า\" ตรงๆ ก็ตาม เพราะคือชื่อคนที่ซื้อสินค้าในใบเสร็จนั้น\n"
    "- ⚠️ ห้ามนำคำที่บ่งบอก \"ประเภทการสั่งซื้อ\" มาใส่เป็น buyer_name เด็ดขาด เช่น \"TAKE AWAY\", \"DINE IN\", \"DELIVERY\", "
    "\"ทานที่ร้าน\", \"กลับบ้าน\", \"นั่งทาน\", \"ซื้อกลับ\" คำเหล่านี้ไม่ใช่ชื่อคน แม้จะอยู่ในตำแหน่งใกล้ข้อมูลลูกค้าก็ตาม "
    "หากหาชื่อผู้ซื้อจริงไม่เจอในเอกสาร ให้ตอบ null ห้ามเดาเอาคำประเภทนี้มาใส่แทนเด็ดขาด\n"
    "- 🎯 รูปแบบสำคัญที่มักถูกมองข้าม: ถ้าเจอบรรทัดที่มีชื่อคน ตามด้วยคำว่า \"Card No.\" หรือ \"เลขบัตร\" "
    "แล้วตามด้วยเลขบัตรสมาชิก (เช่น \"กรกมล Card No. XXXX XXXX 6141 7422\") ให้ถือว่าชื่อที่อยู่ก่อนหน้า \"Card No.\" "
    "นั้นคือ buyer_name เสมอ (คือชื่อเจ้าของบัตรสมาชิก/บัตรสะสมแต้มที่ใช้จ่ายในธุรกรรมนี้) แม้จะไม่มีคำกำกับ \"ผู้ซื้อ\"/\"ลูกค้า\" ก็ตาม "
    "รูปแบบนี้พบบ่อยมากในใบเสร็จร้านกาแฟ/ปั๊มน้ำมัน (เช่น Cafe Amazon, PTT Station) ห้ามมองข้ามหรือทิ้งเป็น null ถ้าเจอรูปแบบนี้\n"
    "- 🎯 กรณีใบเสร็จจาก LINE MAN Delivery: โครงสร้างมักเป็น [LINE MAN Delivery] -> [เลขออเดอร์] -> [ชื่อ/ชื่อเล่นลูกค้า] -> [ชื่อร้านค้า] "
    "ให้สังเกตว่าบรรทัดที่อยู่ \"ระหว่าง\" เลขออเดอร์กับชื่อร้านค้า (ซึ่งมักมีสัญลักษณ์อีโมจิ/หัวใจ/ดอกไม้ประกอบ เช่น \"❤️ANG❤️\") "
    "คือ buyer_name (ชื่อ/ชื่อเล่นผู้สั่งซื้อ) ไม่ใช่ส่วนหนึ่งของชื่อร้าน"
)

# ==================================================
# 🧾 กฎ document_type
# ==================================================
DOC_TYPE_RULE_NOTE = (
    "\n\nกฎเรื่อง document_type (สำคัญมาก): ต้องเลือกตอบเพียง 1 ค่า จาก 3 ค่านี้เท่านั้น (ห้ามตอบค่าอื่น ห้ามรวมด้วย \"/\"):\n"
    "ให้ตรวจสอบตามลำดับความสำคัญนี้เท่านั้น (เจอข้อไหนก่อน ให้ตอบข้อนั้นทันที ห้ามข้ามไปดูข้ออื่น):\n"
    "ลำดับที่ 1 — ค้นหาคำที่พิมพ์ตรงตัวในเอกสารก่อนเสมอ (ให้ความสำคัญกับคำที่พิมพ์จริงมากกว่าการอนุมาน):\n"
    "   - ถ้าพบคำว่า \"เต็มรูป\" ปรากฏจริงในเอกสาร -> ตอบ \"ใบกำกับภาษีเต็มรูป\" ทันที (ไม่ต้องดูเงื่อนไขอื่น)\n"
    "   - ถ้าพบคำว่า \"อย่างย่อ\" ปรากฏจริงในเอกสาร (และไม่เจอคำว่า \"เต็มรูป\") -> ตอบ \"ใบกำกับภาษีอย่างย่อ\" ทันที\n"
    "ลำดับที่ 2 — ถ้าไม่พบทั้ง \"เต็มรูป\" และ \"อย่างย่อ\" เป็นคำพิมพ์ตรงตัวเลย ให้ดูสัญญาณอนุมาน:\n"
    "   - ถ้ามี buyer_tax_id (เลขผู้เสียภาษีของผู้ซื้อ 13 หลัก) ปรากฏชัดเจนในเอกสาร -> ตอบ \"ใบกำกับภาษีเต็มรูป\" "
    "(เพราะการมีเลขผู้เสียภาษีผู้ซื้อคือสัญญาณที่แน่นอนที่สุดของใบกำกับภาษีเต็มรูป มากกว่าแค่มีชื่อ-ที่อยู่ผู้ซื้อ)\n"
    "   - ถ้าไม่มี buyer_tax_id แต่มีคำกำกับอย่าง \"ใบกำกับภาษี\" ปรากฏ (โดยไม่มี \"อย่างย่อ\"/\"เต็มรูป\" ต่อท้าย) "
    "และมีแค่ชื่อผู้ซื้อ (ไม่มีเลขผู้เสียภาษี) -> ให้ตอบ \"ใบกำกับภาษีอย่างย่อ\" (ใบกำกับภาษีเต็มรูปตัวจริงเกือบทุกใบจะมีเลขผู้เสียภาษีผู้ซื้อกำกับเสมอ)\n"
    "ลำดับที่ 3 — ถ้าไม่เข้าเงื่อนไขข้างต้นเลย (ไม่มีคำว่าใบกำกับภาษี ไม่มี \"อย่างย่อ\"/\"เต็มรูป\") -> ตอบ \"ใบเสร็จรับเงินทั่วไป\"\n"
    "⚠️ ห้ามเดาจากความยาว/ความซับซ้อนของเอกสารเด็ดขาด ต้องอิงจากคำที่พิมพ์จริงหรือ buyer_tax_id เท่านั้น"
)

# ==================================================
# 🪪 กฎ tax_id
# ==================================================
TAX_ID_RULE_NOTE = (
    "\n\nกฎเรื่อง merchant_tax_id และ buyer_tax_id (สำคัญมาก):\n"
    "- เลขผู้เสียภาษีไทยที่ถูกต้องต้องมี 13 หลักเท่านั้น และต้องมีคำกำกับชัดเจนในเอกสาร เช่น \"เลขประจำตัวผู้เสียภาษี\", "
    "\"เลขผู้เสียภาษี\", \"Tax ID\" อยู่ติดกับตัวเลขนั้น\n"
    "- ถ้าตัวเลขที่เจอไม่ครบ 13 หลัก หรือไม่มีคำกำกับชัดเจน (เช่น เป็นเลขคำสั่งซื้อ/เบอร์โทร/รหัสอ้างอิง/เลขที่ใบเสร็จ) "
    "ห้ามนำมาใส่ในช่อง tax_id เด็ดขาด ให้ใส่ null แทน\n"
    "- ห้ามใส่เลขเดียวกันซ้ำทั้ง merchant_tax_id และ buyer_tax_id เว้นแต่เอกสารจะระบุชัดเจนจริงๆ ว่าเป็นเลขเดียวกันทั้งสองฝ่าย "
    "หากไม่มั่นใจว่าเลขใดเป็นของฝ่ายไหน ให้ใส่เฉพาะฝ่ายที่มีคำกำกับชัดเจนเท่านั้น อีกฝ่ายให้เป็น null"
)

# ==================================================
# 📖 ตัวอย่างสอน pattern (few-shot)
# ==================================================
FEWSHOT_EXAMPLE_NOTE = (
    "\n\nตัวอย่างการอ่านให้ถูกต้อง (เรียนรู้ pattern นี้แล้วนำไปใช้กับเอกสารจริง):\n"
    "ตัวอย่างข้อความ OCR ที่พบบ่อย:\n"
    "```\n"
    "หจก. ตัวอย่างอลูมิเนียม (สาขา00001)\n"
    "เลขประจำตัวผู้เสียภาษี 0903547002224\n"
    "ใบเสร็จรับเงิน/ใบกำกับภาษีอย่างย่อ\n"
    "เลขที่ 00123  วันที่ 15 มิ.ย. 2568\n"
    "ในนาม: สมชาย ใจดี\n"
    "รายการ...\n"
    "```\n"
    "การอ่านที่ถูกต้อง:\n"
    "- merchant_name = \"หจก. ตัวอย่างอลูมิเนียม (สาขา00001)\" เพราะอยู่หัวกระดาษบนสุด และมีเลขผู้เสียภาษี "
    "13 หลักกำกับอยู่ติดกัน (สัญญาณของผู้ขาย/ผู้ออกเอกสาร)\n"
    "- buyer_name = \"สมชาย ใจดี\" เพราะมีคำกำกับ \"ในนาม:\" นำหน้าอย่างชัดเจน (สัญญาณของผู้ซื้อ) "
    "แม้ว่าชื่อนี้จะอยู่บรรทัดถัดจากหัวกระดาษก็ตาม ห้ามเอาไปใส่ merchant_name เด็ดขาด\n"
    "- document_type = \"ใบกำกับภาษีอย่างย่อ\" เพราะเอกสารมีคำว่า \"อย่างย่อ\" กำกับชัดเจน (ให้เลือกคำเฉพาะเจาะจงกว่าเสมอ)\n"
    "- document_date = \"15/06/68\" (แปลง 15 มิ.ย. 2568 -> พ.ศ. 68 -> จัดรูปแบบ วว/ดด/ปป ห้ามแปลงเป็น ค.ศ.)\n"
    "- merchant_tax_id = \"0903547002224\" (13 หลัก มีคำกำกับชัดเจน) ส่วน buyer_tax_id = null "
    "เพราะไม่มีเลขผู้เสียภาษีกำกับคู่กับชื่อผู้ซื้อในตัวอย่างนี้ ห้ามเดาใส่เลขซ้ำจาก merchant_tax_id\n\n"
    "ตัวอย่างที่ 2 (กรณีร้านเล็กขายให้หน่วยงานใหญ่ + ข้อมูลสมาชิก):\n"
    "```\n"
    "ร้านออลล์นิวส์เต็ป : www.Allnewstep.com :: ไกรสร สืบบุญ\n"
    "เลขประจำตัวผู้เสียภาษี 1349700003006\n"
    "ข้อมูลผู้ซื้อ\n"
    "ชื่อผู้ซื้อ มหาวิทยาลัยวลัยลักษณ์\n"
    "```\n"
    "การอ่านที่ถูกต้อง: merchant_name = \"ร้านออลล์นิวส์เต็ป\" (ร้านเล็ก มีเลขผู้เสียภาษีกำกับ) และ "
    "buyer_name = \"มหาวิทยาลัยวลัยลักษณ์\" (แม้ชื่อจะฟังดูเป็นองค์กรใหญ่กว่าร้านมาก แต่มีคำกำกับ \"ผู้ซื้อ\"/\"ชื่อผู้ซื้อ\" "
    "อยู่ติดกันชัดเจน ห้ามสลับไปเป็น merchant เองเด็ดขาด)\n\n"
    "อีกตัวอย่าง: ถ้า OCR มีข้อความ \"ข้อมูลสมาชิก คุณอริษา\" (ไม่มีคำว่า \"ผู้ซื้อ\"/\"ลูกค้า\" ตรงๆ) "
    "ให้ตีความว่า buyer_name = \"คุณอริษา\" เพราะ \"ข้อมูลสมาชิก\" ตามด้วยชื่อคน หมายถึงชื่อผู้ซื้อที่เป็นสมาชิกร้านนั้น"
)

# ==================================================
# 🏷️ กฎชื่อสินค้า
# ==================================================
ITEM_NAME_RULE_NOTE = (
    "\n\nกฎเรื่องชื่อสินค้า (item_name) (สำคัญมาก):\n"
    "- ห้ามนำตัวเลขจำนวนสินค้า (เช่น 1, 10) หรือลำดับที่ ซึ่งมักพิมพ์อยู่ข้างหน้า มารวมไว้ในช่อง \"item_name\" เด็ดขาด\n"
    "- ตัวอย่าง: หาก OCR แสดง \"1 Hไข่ไก่ต้มสุก\" หรือ \"1.กล้วยหอมทอง\" ให้สกัดเฉพาะตัวหนังสือเท่านั้น อย่าดึงเลขและเครื่องหมายต่างๆ มาด้วยเด็ดขาด\n"
    "- ⚠️ สำคัญมาก: ถ้าชื่อสินค้ามีตัวเลขต่อท้าย/แทรกอยู่ (เช่น รุ่น, ไซส์, ขนาด, รหัสสี เช่น \"เอลิสแฟรี่วิงส์ไนท์ 3\" "
    "หรือ \"...ยาว 30cm จำนวน 40 เส้น\") ตัวเลขเหล่านั้นเป็น \"ส่วนหนึ่งของชื่อสินค้า\" ไม่ใช่ \"quantity\" ของรายการ "
    "ห้ามดึงตัวเลขจากในชื่อสินค้าไปใส่ quantity เด็ดขาด — quantity ต้องมาจากคอลัมน์จำนวนที่แยกต่างหากในตารางรายการสินค้าเท่านั้น "
    "ถ้าไม่มีคอลัมน์จำนวนแยกต่างหาก ให้ถือว่า quantity = 1 เสมอ"
)

EXTRA_RULES = (
    MERCHANT_BUYER_RULE_NOTE + DOC_TYPE_RULE_NOTE + TAX_ID_RULE_NOTE
    + FEWSHOT_EXAMPLE_NOTE + ITEM_NAME_RULE_NOTE
)

# ==================================================
# 🥇 SYSTEM PROMPT — Mode1_Standard_SFT (config ที่ให้ผลดีที่สุด, F1 = 0.9358)
# ==================================================
EXTRACT_SYS_PROMPT = (
    f"คุณคือ AI Expert ด้านการดึงข้อมูลใบเสร็จรับเงิน (Invoice/Receipt)\n"
    f"คำสั่ง: จงอ่านข้อความ OCR ที่ผ่านการคลีนแล้ว จากนั้นสกัดข้อมูลและจัดกลุ่มให้ตรงตามโครงสร้าง JSON นี้อย่างเคร่งครัด:\n{schema_str}"
    f"{DATE_RULE_NOTE}{SUMMARY_RULE_NOTE}{EXTRA_RULES}\n"
    "กฎเหล็ก: ตอบเฉพาะผลลัพธ์ JSON ครอบด้วยแท็ก <output>...</output> เท่านั้น ห้ามอธิบาย ห้ามทักทาย ห้ามมีข้อความอื่นนอกแท็กเด็ดขาด"
)

# ==================================================
# 🩺 SELF-VERIFICATION PROMPT (LLM รอบที่สอง)
# ==================================================
VERIFY_SYS_PROMPT = f"""คุณคือ AI Expert ด้านการตรวจสอบความถูกต้องของ JSON ที่สกัดมาจากใบเสร็จ/ใบกำกับภาษี
คุณจะได้รับ JSON ที่สกัดไว้แล้วตามโครงสร้างนี้:
{schema_str}
{DATE_RULE_NOTE}{SUMMARY_RULE_NOTE}{EXTRA_RULES}

จงตรวจสอบและแก้ไขให้ถูกต้องตามกฎต่อไปนี้:
1. สำหรับแต่ละรายการใน line_items ตรวจสอบว่า quantity x unit_price ใกล้เคียงกับ total_price หรือไม่ ถ้าไม่ตรงกันและสามารถอนุมานค่าที่ถูกต้องได้จากตัวเลขอื่นในรายการ ให้แก้ไขให้สอดคล้องกัน (จำไว้ว่าตัวเลขที่ฝังอยู่ในชื่อสินค้า เช่น รุ่น/ไซส์/จำนวนบรรจุภัณฑ์ ไม่ใช่ quantity จริง)
2. ตรวจสอบว่า summary.subtotal ใกล้เคียงกับผลรวมของ total_price ทุกรายการหรือไม่
3. ตรวจสอบว่า summary.net_amount = subtotal - total_discount + vat_amount ใกล้เคียงกันหรือไม่
4. merchant_tax_id และ buyer_tax_id ควรมีความยาว 13 หลัก (เฉพาะตัวเลข) หากพบว่ามีอักขระอื่นปนอยู่ให้คงตัวเลขไว้เท่านั้น
5. ตรวจสอบว่า document_date อยู่ในรูปแบบ "วว/ดด/ปป" แบบไทย (พ.ศ. 2 หลัก) ตามกฎด้านบน ไม่ใช่ ค.ศ. หรือรูปแบบอื่น
6. หากฟิลด์ใดไม่มีข้อมูลชัดเจนหรือไม่สามารถอนุมานได้อย่างมั่นใจ ให้คงค่าเป็น null ห้ามเดาข้อมูลขึ้นมาเอง
7. ห้ามเปลี่ยนแปลงข้อมูลที่ถูกต้องอยู่แล้ว แก้ไขเฉพาะจุดที่ไม่สอดคล้องกันเชิงตรรกะเท่านั้น

กฎเหล็ก: ตอบเฉพาะ JSON ฉบับแก้ไขแล้ว ครอบด้วยแท็ก <output>...</output> เท่านั้น ห้ามอธิบาย ห้ามมีข้อความอื่นนอกแท็กเด็ดขาด"""


# ==================================================
# 🔧 RULE-BASED OCR CORRECTION (เวอร์ชันเต็มตามที่ใช้ในผลทดลอง)
# ==================================================
_THAI_CORRECTIONS = {
    "ภาษีมูลค่าเพิน": "ภาษีมูลค่าเพิ่ม", "ภาษีมูลคาเพิม": "ภาษีมูลค่าเพิ่ม",
    "ยอดรวมทงหมด": "ยอดรวมทั้งหมด", "ยอดรวมทงัหมด": "ยอดรวมทั้งหมด",
    "ใบเสรจ": "ใบเสร็จ", "ใบเสรจรบเงน": "ใบเสร็จรับเงิน",
    "เลขทใบ": "เลขที่ใบ", "เลขท ": "เลขที่ ", "วนท": "วันที่", "วนที": "วันที่",
    "เลขผเู้สย": "เลขผู้เสียภาษี", "เลขผู้เสยี": "เลขผู้เสียภาษี",
    "จำนวนเงน": "จำนวนเงิน", "รวมเปน": "รวมเป็น", "มูลคา": "มูลค่า",
    "ราคา/หนวย": "ราคา/หน่วย", "จำนวน/หนวย": "จำนวน/หน่วย",
}


def rule_based_correct(text: str) -> str:
    for wrong, correct in _THAI_CORRECTIONS.items():
        text = text.replace(wrong, correct)

    text = text.replace("฿", "บาท")
    text = re.sub(r"VAT\s*7\s*%", "VAT 7%", text, flags=re.IGNORECASE)

    lines = []
    for line in text.split("\n"):
        line_strip = line.strip()
        if not line_strip:
            continue

        digit_count = sum(1 for c in line_strip if c.isdigit())
        digit_ratio = digit_count / max(len(line_strip), 1)

        if digit_ratio > 0.2:
            line_strip = re.sub(r"\bO\b", "0", line_strip)
            line_strip = re.sub(r"\bo\b", "0", line_strip)
            line_strip = re.sub(r"\bI\b", "1", line_strip)
            line_strip = re.sub(r"\bl\b", "1", line_strip)
            line_strip = re.sub(r"\bS\b", "5", line_strip)
            line_strip = re.sub(r"\bB\b", "8", line_strip)

        lines.append(line_strip)

    return "\n".join(lines)


# ==================================================
# 🔢 Normalization helpers (ใช้เช็คความสอดคล้องก่อนตัดสินใจเรียก verification)
# ==================================================
def normalize_numeric(val):
    if val is None:
        return None
    s = str(val).strip()
    if s == "" or s.lower() == "null":
        return None
    s = s.replace(",", "").replace("฿", "").replace("บาท", "").strip()
    s = re.sub(r"[^\d.\-]", "", s)
    if s in ("", "-", ".", "-."):
        return None
    try:
        return float(s)
    except ValueError:
        return None


_TWO_DIGIT_YEAR_DATE_RE = re.compile(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2})$")


def normalize_tax_id(val):
    if val is None:
        return None
    s = re.sub(r"\D", "", str(val))
    return s if s else None


# ==================================================
# 📤 Output parsing (parse จาก <output>...</output> ให้ตรงกับที่ prompt สั่ง)
# ==================================================
def extract_clean_output(raw_text: str) -> str:
    match = re.search(r'<output>(.*?)(</output>|$)', raw_text, flags=re.DOTALL)
    clean_text = match.group(1) if match else re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL)
    clean_text = re.sub(r'```json', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'```', '', clean_text)
    return clean_text.strip()


def _remove_trailing_commas(s: str) -> str:
    return re.sub(r",\s*([}\]])", r"\1", s)


def safe_parse_json(raw_str: str):
    candidate = raw_str.strip()
    try:
        return json.loads(candidate)
    except Exception:
        pass
    repaired = _remove_trailing_commas(candidate)
    json_match = re.search(r"\{.*\}", repaired, re.DOTALL)
    if json_match:
        repaired = json_match.group(0)
    return json.loads(repaired)


def ensure_schema(data):
    if not isinstance(data, dict):
        return json.loads(json.dumps(GOLDEN_SCHEMA))

    def merge(template, target):
        if isinstance(template, dict):
            if not isinstance(target, dict):
                target = {}
            return {k: merge(v, target.get(k)) for k, v in template.items()}
        elif isinstance(template, list):
            if isinstance(target, list):
                if template and isinstance(template[0], dict):
                    return [merge(template[0], item) for item in target if isinstance(item, dict)]
                return target
            return []
        else:
            return target if target is not None else None

    return merge(GOLDEN_SCHEMA, data)


# ==================================================
# ✅ ตัดสินใจว่าต้องเรียก verification รอบสองหรือไม่
#    (เฉพาะฟิลด์ตัวเลข/รูปแบบที่ผลทดสอบชี้ว่าแม่นน้อยที่สุด)
# ==================================================
def needs_verification(extracted_json: dict) -> bool:
    if not isinstance(extracted_json, dict):
        return True

    items = extracted_json.get("line_items", [])
    items = items if isinstance(items, list) else []
    for it in items:
        if not isinstance(it, dict):
            continue
        qty = normalize_numeric(it.get("quantity"))
        unit_price = normalize_numeric(it.get("unit_price"))
        total = normalize_numeric(it.get("total_price"))
        if qty is not None and unit_price is not None and total is not None:
            expected = qty * unit_price
            if abs(expected) > 1e-6 and abs(expected - total) / abs(expected) > 0.03:
                return True

    mb = extracted_json.get("merchant_and_buyer", {})
    mb = mb if isinstance(mb, dict) else {}
    for key in ("merchant_tax_id", "buyer_tax_id"):
        tax_id = normalize_tax_id(mb.get(key))
        if tax_id is not None and len(tax_id) != 13:
            return True

    summary = extracted_json.get("summary", {})
    summary = summary if isinstance(summary, dict) else {}
    subtotal = normalize_numeric(summary.get("subtotal"))
    discount = normalize_numeric(summary.get("total_discount")) or 0.0
    vat = normalize_numeric(summary.get("vat_amount")) or 0.0
    net = normalize_numeric(summary.get("net_amount"))
    if subtotal is not None and net is not None:
        expected_net = subtotal - discount + vat
        if abs(expected_net) > 1e-6 and abs(expected_net - net) / abs(expected_net) > 0.05:
            return True

    doc_header = extracted_json.get("document_header", {})
    doc_date = doc_header.get("document_date") if isinstance(doc_header, dict) else None
    if doc_date:
        s = str(doc_date).strip()
        m = _TWO_DIGIT_YEAR_DATE_RE.match(s)
        if not m:
            return True
        yy = int(m.group(3))
        if abs(yy - _CURRENT_BE_YY) > 1:
            return True

    return False


# ==================================================
# 🌐 API call
# ==================================================
def _call_typhoon_raw(sys_prompt: str, user_prompt: str, temperature: float) -> str:
    url = "https://api.opentyphoon.ai/v1/chat/completions"
    api_key = st.secrets["OPENTYPHOON_API_KEY"]

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": LLM_MAX_TOKENS,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def _extract_with_retry(final_ocr_input: str, attempts: int = MAX_EXTRACTION_ATTEMPTS):
    user_prompt = f"""
ข้อความ OCR:

----------------
{final_ocr_input}
----------------

ให้สกัดข้อมูลออกมาเป็น JSON ตาม Schema ที่กำหนด ตอบเฉพาะ JSON ครอบด้วยแท็ก <output>...</output> เท่านั้น
"""
    last_err = None
    for _ in range(attempts):
        try:
            raw = _call_typhoon_raw(EXTRACT_SYS_PROMPT, user_prompt, EXTRACT_TEMPERATURE)
            cleaned = extract_clean_output(raw)
            parsed = safe_parse_json(cleaned)
            return ensure_schema(parsed)
        except Exception as e:
            last_err = e
    return {"error": f"LLM Parse Error: {last_err}"}


def _verify(extracted_json: dict):
    user_prompt = (
        "นี่คือ JSON ที่สกัดไว้แล้ว กรุณาตรวจสอบตามกฎ แล้วส่งฉบับแก้ไข (หรือฉบับเดิมถ้าไม่มีจุดผิด) "
        f"คืนในแท็ก <output>...</output>:\n{json.dumps(extracted_json, ensure_ascii=False, indent=2)}"
    )
    try:
        raw = _call_typhoon_raw(VERIFY_SYS_PROMPT, user_prompt, VERIFY_TEMPERATURE)
        cleaned = extract_clean_output(raw)
        verified = safe_parse_json(cleaned)
        return ensure_schema(verified)
    except Exception:
        # ถ้าตรวจซ้ำล้มเหลว ให้คืนผลรอบแรกแทน ดีกว่าทิ้งงาน
        return extracted_json


# ==================================================
# 🚀 ฟังก์ชันหลักที่หน้าเว็บเรียกใช้
# ==================================================
def call_typhoon_llm(ocr_text: str) -> dict:
    """
    รับข้อความ OCR ที่ผ่าน clean_ocr_text() + format_ocr_text() มาแล้ว
    (ดู ocr_pipeline.py — สองขั้นตอนนั้นต้องทำ "ก่อน" เรียกฟังก์ชันนี้เสมอ เพื่อให้ตรงกับลำดับ
    ที่ใช้วัดผลจริงใน LLMJasonJune.py: clean_ocr_text -> format_ocr_text -> rule_based_correct)
    -> คืนค่า JSON ตาม GOLDEN_SCHEMA
    ใช้ config ที่ผลทดลองยืนยันว่าดีที่สุด: Mode1_Standard_SFT @ Temp 0.0
    บวก self-verification รอบสองเฉพาะกรณีที่ตรวจพบความไม่สอดคล้องของตัวเลข/รูปแบบ
    """
    final_ocr_input = rule_based_correct(ocr_text)

    extracted = _extract_with_retry(final_ocr_input)

    if "error" in extracted:
        return extracted

    if USE_SELF_VERIFICATION and needs_verification(extracted):
        extracted = _verify(extracted)

    return extracted