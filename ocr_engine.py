import cv2
import fitz
import numpy as np
import requests
import streamlit as st


# =========================================================
# LOAD IMAGE OR PDF
# =========================================================
def load_image_or_pdf(file_bytes, file_name):
    """
    รองรับ:
    - jpg
    - jpeg
    - png
    - pdf

    PDF จะ render หน้าแรกที่ความละเอียดสูง
    """

    if file_name.lower().endswith(".pdf"):

        doc = fitz.open(
            stream=file_bytes,
            filetype="pdf"
        )

        page = doc.load_page(0)

        mat = fitz.Matrix(3, 3)

        pix = page.get_pixmap(
            matrix=mat,
            alpha=False
        )

        img = np.frombuffer(
            pix.samples,
            dtype=np.uint8
        ).reshape(
            pix.height,
            pix.width,
            pix.n
        )

        if pix.n == 4:
            img = cv2.cvtColor(
                img,
                cv2.COLOR_RGBA2BGR
            )

        elif pix.n == 3:
            img = cv2.cvtColor(
                img,
                cv2.COLOR_RGB2BGR
            )

        return img

    nparr = np.frombuffer(
        file_bytes,
        np.uint8
    )

    return cv2.imdecode(
        nparr,
        cv2.IMREAD_COLOR
    )


# =========================================================
# DESKEW
# =========================================================
def deskew_image(image):

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    blur = cv2.GaussianBlur(
        gray,
        (9, 9),
        0
    )

    thresh = cv2.threshold(
        blur,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )[1]

    coords = np.column_stack(
        np.where(thresh > 0)
    )

    if len(coords) == 0:
        return image

    angle = cv2.minAreaRect(coords)[-1]

    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    if abs(angle) < 0.5:
        return image

    if abs(angle) > 10:
        return image

    h, w = image.shape[:2]

    center = (w // 2, h // 2)

    M = cv2.getRotationMatrix2D(
        center,
        angle,
        1.0
    )

    cos = abs(M[0, 0])
    sin = abs(M[0, 1])

    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))

    M[0, 2] += (new_w / 2) - center[0]
    M[1, 2] += (new_h / 2) - center[1]

    return cv2.warpAffine(
        image,
        M,
        (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )


# =========================================================
# IMAGE ENHANCEMENT
# =========================================================
def process_method_4_sharpening(img):

    gray = cv2.cvtColor(
        img,
        cv2.COLOR_BGR2GRAY
    )

    denoised = cv2.fastNlMeansDenoising(
        gray,
        None,
        10,
        7,
        21
    )

    clahe = cv2.createCLAHE(
        clipLimit=3.0,
        tileGridSize=(8, 8)
    )

    enhanced = clahe.apply(
        denoised
    )

    kernel = np.array(
        [
            [0, -1, 0],
            [-1, 5, -1],
            [0, -1, 0]
        ]
    )

    sharpened = cv2.filter2D(
        enhanced,
        -1,
        kernel
    )

    return sharpened


# =========================================================
# OCR
# =========================================================
def run_typhoon_ocr(image_np):

    url = "https://api.opentyphoon.ai/v1/ocr"

    api_key = st.secrets["OPENTYPHOON_API_KEY"]

    _, encoded_img = cv2.imencode(
        ".jpg",
        image_np,
        [
            cv2.IMWRITE_JPEG_QUALITY,
            95
        ]
    )

    image_bytes = encoded_img.tobytes()

    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": "typhoon-ocr",
        "task_type": "default",
        "temperature": 0,
        "max_tokens": 8192,
        "prompt": """
อ่านข้อความทั้งหมดจากภาพใบเสร็จให้ครบถ้วนที่สุด

กฎการดึงข้อมูล:

1. ดึงทุกบรรทัด
2. ห้ามสรุป
3. ห้ามแปลภาษา
4. ห้ามแก้คำ
5. ห้ามตัดข้อความ
6. เก็บรูปแบบตัวเลขเดิม
7. เก็บเลขผู้เสียภาษี
8. เก็บชื่อร้าน
9. เก็บที่อยู่
10. เก็บรายการสินค้า
11. เก็บ VAT
12. เก็บยอดรวม
13. เก็บ QR PromptPay ถ้ามี
14. เก็บ Receipt No
15. เก็บ ABB No
16. เก็บวันที่และเวลา

พิมพ์ออกมาตามที่เห็นในภาพทั้งหมด
"""
    }

    try:

        response = requests.post(
            url,
            headers=headers,
            data=data,
            files={
                "file": (
                    "receipt.jpg",
                    image_bytes,
                    "image/jpeg"
                )
            },
            timeout=90
        )

        response.raise_for_status()

        result = response.json()

        texts = []

        for page in result.get(
            "results",
            []
        ):

            if page.get("success"):

                content = page["message"]["choices"][0]["message"]["content"]

                texts.append(content)

        return "\n".join(texts)

    except Exception as exc:

        return (
            "[ERROR] OCR Engine Failed: "
            f"{str(exc)}"
        )