import re

import cv2
import fitz
import numpy as np
import requests
import streamlit as st

OCR_URL = "https://api.opentyphoon.ai/v1/ocr"
OCR_MODEL = "typhoon-ocr"
OCR_MAX_TOKENS = 8192
OCR_JPEG_QUALITY = 75
OCR_MAX_RETRIES = 5

# prompt เดิมที่ใช้ตอนสร้างชุดข้อมูล (Preprocess_clahe.py) — ยังไม่มีข้อมูลว่า prompt ยาว 16 ข้อ
# ที่เคยส่งมาให้ดูจะแม่นกว่าหรือแย่กว่านี้ จึงยึดตัวที่วัดผลแล้วไว้ก่อน
OCR_PROMPT = (
    "กรุณาดึงข้อความทั้งหมดที่ปรากฏในภาพออกมาให้ครบถ้วนและแม่นยำที่สุด "
    "ห้ามข้ามหรือตัดข้อความใดๆ ทิ้งเด็ดขาด พิมพ์ออกมาตามที่เห็นในภาพ"
)


# =========================================================
# 1) โหลดไฟล์ (รูปภาพ/PDF) จาก bytes ที่ Streamlit ส่งมา
# =========================================================
def load_image_or_pdf(file_bytes: bytes, file_name: str):
    """
    รองรับ jpg / jpeg / png / pdf
    PDF จะ render หน้าแรกที่ความละเอียดสูง (matrix 3x เทียบเท่าประมาณ 216 DPI)
    """
    if file_name.lower().endswith(".pdf"):
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page = doc.load_page(0)
        mat = fitz.Matrix(3, 3)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        return img

    nparr = np.frombuffer(file_bytes, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)


# =========================================================
# 2) แก้ภาพเอียง (deskew)
# =========================================================
def deskew_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) == 0:
        return image

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    if abs(angle) > 10 or abs(angle) < 0.5:
        return image

    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)

    cos = abs(M[0, 0])
    sin = abs(M[0, 1])
    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))

    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]

    return cv2.warpAffine(
        image, M, (new_w, new_h),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
    )


# =========================================================
# 3) เพิ่ม contrast แบบ CLAHE (ตรงกับตัวที่ใช้สร้างชุดข้อมูลจริง)
# =========================================================
def process_clahe(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


# =========================================================
# 4) เรียก Typhoon OCR (มี retry กัน 500 / network error)
# =========================================================
def run_typhoon_ocr(image_np, max_retries: int = OCR_MAX_RETRIES) -> str:
    api_key = st.secrets["OPENTYPHOON_API_KEY"]

    _, encoded_img = cv2.imencode(".jpg", image_np, [cv2.IMWRITE_JPEG_QUALITY, OCR_JPEG_QUALITY])
    image_bytes = encoded_img.tobytes()

    headers = {"Authorization": f"Bearer {api_key}"}
    data = {
        "model": OCR_MODEL,
        "task_type": "default",
        "temperature": 0,
        "max_tokens": OCR_MAX_TOKENS,
        "prompt": OCR_PROMPT,
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(
                OCR_URL,
                headers=headers,
                data=data,
                files={"file": ("receipt.jpg", image_bytes, "image/jpeg")},
                timeout=90,
            )

            if response.status_code == 500 and attempt < max_retries - 1:
                import time
                time.sleep(30)
                continue

            response.raise_for_status()
            result = response.json()

            texts = []
            for page in result.get("results", []):
                if page.get("success"):
                    texts.append(page["message"]["choices"][0]["message"]["content"])
            return "\n".join(texts)

        except requests.exceptions.RequestException as exc:
            if attempt < max_retries - 1:
                import time
                time.sleep((attempt + 1) * 3)
                continue
            return f"[ERROR] OCR Engine Failed: {exc}"

    return "[ERROR] OCR Engine Failed: max retries exceeded"


# =========================================================
# 5) ล้างข้อความ OCR (ลบ markdown / tag / ตัวหนา)
# =========================================================
def clean_ocr_text(text: str) -> str:
    text = re.sub(r"```[a-zA-Z]*\n", "", text)
    text = text.replace("```", "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("**", "")
    return text.strip()


# =========================================================
# 6) จัดบรรทัดตาม keyword ของโครงสร้างใบเสร็จ
#    (ขั้นตอนนี้ต้องทำ "ก่อน" ส่งต่อให้ receipt_extractor.rule_based_correct เสมอ
#    เพื่อให้ตรงกับลำดับที่ใช้วัดผลจริง)
# =========================================================
def format_ocr_text(text: str) -> str:
    keywords = [
        r"(POS No\.?)", r"(Term\.?\s*No\.?)", r"(Staff\s*:?)", r"(Cashier\s*:?)",
        r"(Date\s*:?)", r"(Time\s*:?)", r"(TAX ID\s*:?)", r"(Rec No\.?)", r"(No\.CAS)",
        r"(Description Amount)", r"(รายการ)", r"(ราคาต่อหน่วย)",
        r"(?<!\n)(\b\d+\s*\))", r"(?<!\n)(\b\d+\.\s+[A-Za-zก-๙])",
        r"(1 EA @)", r"(Sub Total)", r"(Subtotal)", r"(Total\(VAT)", r"(Total Amount)",
        r"(ค่าพื้นที่ห่างไกล:?)", r"(ค่าส่ง:?)", r"(ส่วนลดรวม:?)", r"(ยอดรวม:?)", r"(ยอดสุทธิ:?)",
        r"(QR Promptpay)", r"(รับเงิน:?)", r"(เงินทอน:?)",
        r"(ขอบคุณ)", r"(สแกน QR)", r"(งดรับคืน)", r"(เปลี่ยน/คืน)", r"(ผู้ส่ง)",
    ]
    for kw in keywords:
        text = re.sub(kw, r"\n\1", text, flags=re.IGNORECASE)

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


# =========================================================
# 🚀 ฟังก์ชันหลักที่หน้าเว็บเรียกใช้: รูป/PDF ที่อัปโหลด -> ข้อความพร้อมส่งเข้า extractor
# =========================================================
def run_ocr_pipeline(file_bytes: bytes, file_name: str) -> str:
    """
    รับไฟล์ที่อัปโหลด (bytes + ชื่อไฟล์) -> คืนข้อความ OCR ที่ผ่าน deskew + CLAHE + OCR +
    clean_ocr_text + format_ocr_text เรียบร้อยแล้ว พร้อมส่งต่อให้
    receipt_extractor.call_typhoon_llm() ทันที (ห้ามข้ามหรือสลับลำดับขั้นตอนใดๆ)
    """
    img = load_image_or_pdf(file_bytes, file_name)
    if img is None:
        return "[ERROR] โหลดไฟล์ไม่สำเร็จ หรือไฟล์เสียหาย"

    img = deskew_image(img)
    processed = process_clahe(img)

    raw_text = run_typhoon_ocr(processed)
    if raw_text.startswith("[ERROR]"):
        return raw_text

    text = clean_ocr_text(raw_text)
    text = format_ocr_text(text)
    return text