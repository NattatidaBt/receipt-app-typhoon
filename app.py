import base64
import csv
import json
import re
from io import StringIO

import cv2
import streamlit as st
import streamlit.components.v1 as components

from llm_engine import call_typhoon_llm, clean_and_format_ocr
from ocr_engine import (
    deskew_image,
    load_image_or_pdf,
    process_method_4_sharpening,
    run_typhoon_ocr,
)

try:
    from supabase import create_client
except ImportError:
    create_client = None


st.set_page_config(
    page_title="RecAipt - Receipt Verification",
    layout="wide",
    initial_sidebar_state="collapsed",
)


CSS = """
<style>
:root {
    --bg: #f3f1ec;
    --panel: #fbfaf7;
    --panel-2: #f7f3ea;
    --ink: #24302f;
    --muted: #64706d;
    --line: #ddd8cc;
    --accent: #2f6f73;
    --accent-2: #285e62;
    --ok-bg: #e8f2e7;
    --ok-line: #9abe98;
    --ok-ink: #2c6330;
    --warn-bg: #fff3d8;
    --warn-line: #dfb65b;
    --warn-ink: #75520f;
    --bad-bg: #fae4e0;
    --bad-line: #d9958d;
    --bad-ink: #91382d;
}

header, footer, #MainMenu,
[data-testid="stToolbar"],
[data-testid="stDecoration"] {
    display: none !important;
}

.stApp {
    background: var(--bg);
    color: var(--ink);
}

.block-container {
    max-width: 100% !important;
    padding: 0 22px 18px !important;
}

h1, h2, h3, h4, p, label, span, div {
    letter-spacing: 0 !important;
}

.app-topbar {
    position: sticky;
    top: 0;
    z-index: 20;
    margin: 0 -22px 16px;
    padding: 16px 28px;
    background: #f9f7f1;
    border-bottom: 1px solid var(--line);
}

.topbar-grid {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 16px;
    align-items: center;
}

.brand {
    color: var(--ink);
    font-size: 1.32rem;
    font-weight: 720;
    line-height: 1.3;
}

.subtitle {
    color: var(--muted);
    font-size: 0.98rem;
    line-height: 1.55;
    margin-top: 3px;
}

.status-row {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: flex-end;
}

.badge {
    display: inline-flex;
    align-items: center;
    min-height: 30px;
    padding: 4px 11px;
    border-radius: 999px;
    font-size: 0.92rem;
    font-weight: 650;
    white-space: nowrap;
}

.badge-ok {
    color: var(--ok-ink);
    background: var(--ok-bg);
    border: 1px solid var(--ok-line);
}

.badge-warn {
    color: var(--warn-ink);
    background: var(--warn-bg);
    border: 1px solid var(--warn-line);
}

.badge-bad {
    color: var(--bad-ink);
    background: var(--bad-bg);
    border: 1px solid var(--bad-line);
}

.upload-wrap {
    max-width: 860px;
    margin: 44px auto 20px;
    padding: 0 10px;
}

.upload-title {
    color: var(--ink);
    font-size: clamp(1.7rem, 2.4vw, 2.45rem);
    font-weight: 760;
    line-height: 1.25;
    text-align: center;
    margin-bottom: 8px;
}

.upload-subtitle {
    color: var(--muted);
    font-size: 1.08rem;
    line-height: 1.65;
    text-align: center;
    margin-bottom: 24px;
}

[data-testid="stFileUploader"] {
    max-width: 820px;
    margin: 0 auto;
}

[data-testid="stFileUploaderDropzone"] {
    background: var(--panel) !important;
    border: 2px dashed #b7aa91 !important;
    border-radius: 8px !important;
    min-height: 190px !important;
    padding: 30px !important;
}

[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--accent) !important;
    background: #fffffb !important;
}

[data-testid="stFileUploaderDropzoneInstructions"] span {
    color: var(--ink) !important;
    font-size: 1.05rem !important;
    line-height: 1.5 !important;
}

[data-testid="stFileUploaderDropzoneInstructions"] small {
    color: var(--muted) !important;
    font-size: 0.96rem !important;
}

.split-shell {
    display: grid;
    grid-template-columns: minmax(360px, 0.95fr) minmax(420px, 1.05fr);
    gap: 16px;
    align-items: start;
}

.pane {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
}

.pane-head {
    padding: 14px 16px;
    border-bottom: 1px solid var(--line);
    background: var(--panel-2);
}

.pane-title {
    color: var(--ink);
    font-size: 1.08rem;
    font-weight: 740;
    line-height: 1.35;
}

.pane-note {
    color: var(--muted);
    font-size: 0.94rem;
    line-height: 1.5;
    margin-top: 3px;
}

.image-scroll {
    height: calc(100vh - 250px);
    min-height: 520px;
    overflow: auto;
    padding: 14px;
    background:
        linear-gradient(45deg, #ece7dc 25%, transparent 25%),
        linear-gradient(-45deg, #ece7dc 25%, transparent 25%),
        linear-gradient(45deg, transparent 75%, #ece7dc 75%),
        linear-gradient(-45deg, transparent 75%, #ece7dc 75%);
    background-size: 18px 18px;
    background-position: 0 0, 0 9px, 9px -9px, -9px 0;
}

.receipt-image {
    display: block;
    height: auto;
    margin: 0 auto;
    border: 1px solid #cfc8b8;
    background: #fff;
    box-shadow: 0 10px 28px rgba(40, 48, 42, 0.12);
}

.soft-callout {
    padding: 12px 14px;
    border-radius: 8px;
    background: #eef4f4;
    border: 1px solid #c8dddf;
    color: #294f52;
    font-size: 0.97rem;
    line-height: 1.55;
    margin: 10px 0 14px;
}

.section-band {
    margin-top: 12px;
    padding: 9px 12px;
    border-left: 4px solid var(--accent);
    background: #eff5f3;
    color: var(--ink);
    font-size: 1.02rem;
    font-weight: 720;
}

.metric-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
    margin: 8px 0 12px;
}

.metric {
    padding: 12px;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: #fffdf8;
}

.metric-label {
    color: var(--muted);
    font-size: 0.9rem;
    line-height: 1.4;
}

.metric-value {
    color: var(--ink);
    font-size: 1.18rem;
    font-weight: 760;
    line-height: 1.3;
    margin-top: 4px;
    overflow-wrap: anywhere;
}

.review-list {
    margin: 8px 0 12px;
    padding: 0;
    list-style: none;
}

.review-list li {
    margin: 6px 0;
    padding: 9px 11px;
    border-radius: 8px;
    font-size: 0.96rem;
    line-height: 1.5;
}

.needs-check {
    background: var(--warn-bg);
    border: 1px solid var(--warn-line);
    color: var(--warn-ink);
}

.looks-ok {
    background: var(--ok-bg);
    border: 1px solid var(--ok-line);
    color: var(--ok-ink);
}

.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"] > div {
    min-height: 44px !important;
    font-size: 1.02rem !important;
    line-height: 1.55 !important;
    color: var(--ink) !important;
    background: #fffefb !important;
    border-color: #cfc8b8 !important;
    border-radius: 8px !important;
}

.stTextArea textarea {
    min-height: 92px !important;
}

.stTextInput label,
.stTextArea label,
.stNumberInput label,
.stSelectbox label,
.stDataFrame label {
    color: var(--ink) !important;
    font-size: 0.98rem !important;
    font-weight: 680 !important;
    line-height: 1.45 !important;
}

.stTextInput input:focus,
.stTextArea textarea:focus,
.stNumberInput input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(47, 111, 115, 0.18) !important;
}

div.stButton > button,
div.stDownloadButton > button,
div.stFormSubmitButton > button {
    min-height: 44px !important;
    border-radius: 8px !important;
    font-size: 1rem !important;
    font-weight: 720 !important;
    border: 1px solid #b9af9c !important;
    background: #fffdf8 !important;
    color: var(--ink) !important;
}

div.stButton > button:hover,
div.stDownloadButton > button:hover,
div.stFormSubmitButton > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent-2) !important;
    background: #eef4f4 !important;
}

div.stButton > button[kind="primary"],
div.stFormSubmitButton > button[kind="primary"] {
    background: var(--accent) !important;
    color: #ffffff !important;
    border-color: var(--accent) !important;
}

div.stButton > button[kind="primary"]:hover,
div.stFormSubmitButton > button[kind="primary"]:hover {
    background: var(--accent-2) !important;
    color: #ffffff !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--line);
    border-radius: 8px;
    overflow: hidden;
}

.action-pad {
    position: sticky;
    bottom: 0;
    z-index: 12;
    padding: 12px;
    margin-top: 12px;
    background: rgba(251, 250, 247, 0.96);
    border: 1px solid var(--line);
    border-radius: 8px;
    box-shadow: 0 -8px 24px rgba(40, 48, 42, 0.08);
}

.kbd {
    display: inline-block;
    padding: 1px 7px;
    border: 1px solid #b9af9c;
    border-radius: 5px;
    background: #fffdf8;
    color: var(--ink);
    font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
    font-size: 0.88rem;
}

.tiny-note {
    color: var(--muted);
    font-size: 0.92rem;
    line-height: 1.55;
}

@media (max-width: 980px) {
    .topbar-grid,
    .split-shell,
    .metric-grid {
        grid-template-columns: 1fr;
    }

    .status-row {
        justify-content: flex-start;
    }

    .image-scroll {
        height: 58vh;
        min-height: 420px;
    }
}
</style>
"""


st.markdown(CSS, unsafe_allow_html=True)


def safe_float(value, default=0.0):
    try:
        if value in (None, ""):
            return default
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def safe_int(value, default=1):
    try:
        if value in (None, ""):
            return default
        return int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return default


def normalize_date(value):
    if not value:
        return ""

    text = str(value).strip()
    numeric = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", text)
    iso = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", text)

    if iso:
        year, month, day = map(int, iso.groups())
        if year > 2500:
            year -= 543
        return f"{year:04d}-{month:02d}-{day:02d}"

    if numeric:
        day, month, year = map(int, numeric.groups())
        if year > 2500:
            year -= 543
        return f"{year:04d}-{month:02d}-{day:02d}"

    return text


def get_nested(data, path, default=""):
    current = data or {}
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current in (None, "") else current


def derive_vat_values(grand_total, vat_rate=7.0, tax_included=True):
    grand_total = safe_float(grand_total)
    vat_rate = safe_float(vat_rate, 7.0)
    if grand_total <= 0 or vat_rate <= 0:
        return 0.0, 0.0

    if tax_included:
        before_tax = grand_total / (1 + (vat_rate / 100))
        vat_amount = grand_total - before_tax
        return round(before_tax, 2), round(vat_amount, 2)

    vat_amount = grand_total * (vat_rate / 100)
    return round(grand_total, 2), round(vat_amount, 2)


def normalize_result(data):
    data = data or {}
    seller = data.get("seller") if isinstance(data.get("seller"), dict) else {}
    buyer = data.get("buyer") if isinstance(data.get("buyer"), dict) else {}

    items = []
    for item in data.get("items", []) or []:
        if not isinstance(item, dict):
            continue
        qty = safe_float(item.get("quantity", item.get("qty", 1)), 1.0)
        unit_price = safe_float(item.get("unit_price", 0.0))
        subtotal = safe_float(item.get("subtotal", item.get("amount", qty * unit_price)))
        items.append(
            {
                "รายการ": item.get("item_description", item.get("name", "")) or "",
                "จำนวน": qty,
                "ราคาต่อหน่วย": unit_price,
                "รวม": subtotal,
                "สถานะ": "ตรวจสอบ",
            }
        )

    if not items:
        items = [{"รายการ": "", "จำนวน": 1.0, "ราคาต่อหน่วย": 0.0, "รวม": 0.0, "สถานะ": "กรอกเอง"}]

    grand_total = safe_float(data.get("grand_total", data.get("total", 0.0)))
    vat_rate = safe_float(data.get("vat_rate", 7.0), 7.0)
    tax_included = data.get("tax_included", True)
    amount_before_tax = safe_float(data.get("amount_before_tax", data.get("subtotal", 0.0)))
    vat_amount = safe_float(data.get("vat_amount", data.get("vat", 0.0)))
    if grand_total > 0 and (amount_before_tax <= 0 or vat_amount <= 0):
        amount_before_tax, vat_amount = derive_vat_values(grand_total, vat_rate, tax_included=True)

    normalized = {
        "document_type": data.get("document_type", "ใบเสร็จรับเงิน") or "ใบเสร็จรับเงิน",
        "seller": {
            "name": seller.get("name", data.get("store_name", "")) or "",
            "tax_id": seller.get("tax_id", data.get("tax_id", "")) or "",
            "address": seller.get("address", "") or "",
            "telephone": seller.get("telephone", "") or "",
        },
        "buyer": {
            "name": buyer.get("name", "") or "",
            "tax_id": buyer.get("tax_id", "") or "",
            "address": buyer.get("address", "") or "",
        },
        "document_number": data.get("document_number", data.get("receipt_no", "")) or "",
        "document_date": normalize_date(data.get("document_date", data.get("date", ""))),
        "tax_included": bool(tax_included),
        "amount_before_tax": amount_before_tax,
        "vat_rate": vat_rate,
        "vat_amount": vat_amount,
        "grand_total": grand_total,
        "payment_method": data.get("payment_method", "") or "",
        "items": items,
    }
    return normalized


def build_export_payload(values, edited_items):
    if hasattr(edited_items, "to_dict"):
        edited_items = edited_items.to_dict("records")

    items = []
    for item in edited_items:
        name = str(item.get("รายการ", "")).strip()
        qty = safe_float(item.get("จำนวน", 1.0), 1.0)
        unit_price = safe_float(item.get("ราคาต่อหน่วย", 0.0))
        subtotal = safe_float(item.get("รวม", qty * unit_price))
        if not name and subtotal == 0:
            continue
        items.append(
            {
                "item_description": name,
                "quantity": qty,
                "unit_price": unit_price,
                "subtotal": subtotal,
            }
        )

    return {
        "document_type": values["document_type"],
        "tax_included": values["tax_included"],
        "seller": {
            "name": values["seller_name"],
            "tax_id": values["seller_tax_id"],
            "address": values["seller_address"],
            "telephone": values["seller_telephone"],
        },
        "buyer": {
            "name": values["buyer_name"],
            "tax_id": values["buyer_tax_id"],
            "address": values["buyer_address"],
        },
        "document_number": values["document_number"],
        "document_date": normalize_date(values["document_date"]),
        "amount_before_tax": values["amount_before_tax"],
        "vat_rate": values["vat_rate"],
        "vat_amount": values["vat_amount"],
        "grand_total": values["grand_total"],
        "payment_method": values["payment_method"],
        "items": items,
    }


def build_receipt_csv(payload):
    output = StringIO()
    fieldnames = [
        "document_type",
        "document_number",
        "document_date",
        "seller_name",
        "seller_tax_id",
        "buyer_name",
        "buyer_tax_id",
        "tax_included",
        "amount_before_tax",
        "vat_rate",
        "vat_amount",
        "grand_total",
        "payment_method",
        "item_no",
        "item_description",
        "quantity",
        "unit_price",
        "item_subtotal",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    seller = payload.get("seller", {}) or {}
    buyer = payload.get("buyer", {}) or {}
    items = payload.get("items", []) or [{}]
    for index, item in enumerate(items, start=1):
        writer.writerow(
            {
                "document_type": payload.get("document_type", ""),
                "document_number": payload.get("document_number", ""),
                "document_date": payload.get("document_date", ""),
                "seller_name": seller.get("name", ""),
                "seller_tax_id": seller.get("tax_id", ""),
                "buyer_name": buyer.get("name", ""),
                "buyer_tax_id": buyer.get("tax_id", ""),
                "tax_included": "Y" if payload.get("tax_included") else "N",
                "amount_before_tax": f"{safe_float(payload.get('amount_before_tax')):.2f}",
                "vat_rate": f"{safe_float(payload.get('vat_rate')):.2f}",
                "vat_amount": f"{safe_float(payload.get('vat_amount')):.2f}",
                "grand_total": f"{safe_float(payload.get('grand_total')):.2f}",
                "payment_method": payload.get("payment_method", ""),
                "item_no": index,
                "item_description": item.get("item_description", ""),
                "quantity": f"{safe_float(item.get('quantity'), 1.0):.2f}",
                "unit_price": f"{safe_float(item.get('unit_price')):.2f}",
                "item_subtotal": f"{safe_float(item.get('subtotal')):.2f}",
            }
        )
    return output.getvalue()


def review_flags(data):
    flags = []
    if not get_nested(data, ["seller", "name"]):
        flags.append("ยังไม่พบชื่อร้านค้า ควรตรวจจากหัวใบเสร็จ")
    if not data.get("document_date"):
        flags.append("ยังไม่พบวันที่เอกสาร")
    if not data.get("document_number"):
        flags.append("ยังไม่พบเลขที่เอกสาร")
    if safe_float(data.get("grand_total")) <= 0:
        flags.append("ยอดรวมสุทธิยังเป็น 0 หรือไม่ชัดเจน")
    if not data.get("items"):
        flags.append("ยังไม่พบรายการสินค้า")
    return flags


def image_to_data_uri(image_np, rotation=0):
    image = image_np
    if rotation == 90:
        image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    elif rotation == 180:
        image = cv2.rotate(image, cv2.ROTATE_180)
    elif rotation == 270:
        image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

    if len(image.shape) == 2:
        ok, encoded = cv2.imencode(".png", image)
    else:
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        ok, encoded = cv2.imencode(".png", rgb)

    if not ok:
        return ""

    return "data:image/png;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")


def copy_button(label, text, key):
    payload = json.dumps(str(text), ensure_ascii=False)
    components.html(
        f"""
        <button id="copy-{key}" style="
            width:100%;min-height:44px;border-radius:8px;border:1px solid #b9af9c;
            background:#fffdf8;color:#24302f;font-size:16px;font-weight:720;cursor:pointer;">
            {label}
        </button>
        <script>
        const btn = document.getElementById("copy-{key}");
        btn.addEventListener("click", async () => {{
            await navigator.clipboard.writeText({payload});
            btn.innerText = "คัดลอกแล้ว";
            setTimeout(() => btn.innerText = {json.dumps(label, ensure_ascii=False)}, 1200);
        }});
        </script>
        """,
        height=54,
    )


def reset_app():
    for key in list(st.session_state.keys()):
        del st.session_state[key]


@st.cache_resource(show_spinner=False)
def init_supabase():
    if create_client is None:
        return None
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
    except Exception:
        return None
    if not url or not key:
        return None
    return create_client(url, key)


def save_to_supabase(payload):
    supabase = init_supabase()
    if supabase is None:
        raise RuntimeError("ยังไม่ได้ตั้งค่า SUPABASE_URL และ SUPABASE_KEY")

    seller = payload.get("seller", {}) or {}
    buyer = payload.get("buyer", {}) or {}

    seller_payload = {
        "name": seller.get("name") or "-",
        "tax_id": seller.get("tax_id") or "0000000000000",
        "address": seller.get("address") or None,
        "telephone": seller.get("telephone") or None,
    }
    seller_res = supabase.table("companies").upsert(seller_payload, on_conflict="tax_id").execute()
    seller_id = seller_res.data[0]["id"]

    buyer_id = None
    if buyer.get("name") or buyer.get("tax_id"):
        buyer_payload = {
            "name": buyer.get("name") or "-",
            "tax_id": buyer.get("tax_id") or "1111111111111",
            "address": buyer.get("address") or None,
        }
        buyer_res = supabase.table("companies").upsert(buyer_payload, on_conflict="tax_id").execute()
        buyer_id = buyer_res.data[0]["id"]

    receipt_payload = {
        "receipt_type": payload.get("document_type") or "ใบเสร็จรับเงิน",
        "document_number": payload.get("document_number") or "-",
        "document_date": payload.get("document_date") or None,
        "seller_id": seller_id,
        "buyer_id": buyer_id,
        "tax_included": bool(payload.get("tax_included", True)),
        "amount_before_tax": safe_float(payload.get("amount_before_tax")),
        "vat_rate": safe_int(payload.get("vat_rate"), 7),
        "vat_amount": safe_float(payload.get("vat_amount")),
        "grand_total": safe_float(payload.get("grand_total")),
    }
    receipt_res = supabase.table("receipts").insert(receipt_payload).execute()
    receipt_id = receipt_res.data[0]["id"]

    for item in payload.get("items", []) or []:
        supabase.table("receipt_items").insert(
            {
                "receipt_id": receipt_id,
                "item_description": item.get("item_description") or "-",
                "quantity": safe_int(item.get("quantity"), 1),
                "unit_price": safe_float(item.get("unit_price")),
                "subtotal": safe_float(item.get("subtotal")),
            }
        ).execute()

    return receipt_id


def run_pipeline(uploaded_file):
    file_bytes = uploaded_file.read()
    file_name = uploaded_file.name

    progress = st.progress(0, text="กำลังเตรียมภาพเอกสาร")
    img = load_image_or_pdf(file_bytes, file_name)
    if img is None:
        st.error("ไฟล์เอกสารเสียหาย หรือระบบไม่รองรับรูปแบบภาพนี้")
        st.stop()

    deskewed_img = deskew_image(img)
    processed_img = process_method_4_sharpening(deskewed_img)
    progress.progress(35, text="กำลังส่งภาพเข้า Typhoon OCR")

    raw_text = run_typhoon_ocr(processed_img)
    if "[ERROR]" in raw_text or not raw_text.strip():
        progress.empty()
        st.error(raw_text if raw_text.strip() else "ระบบไม่สามารถถอดข้อความจากใบเสร็จนี้ได้")
        st.stop()

    progress.progress(70, text="กำลังสกัดข้อมูลด้วย Typhoon LLM")
    extracted = call_typhoon_llm(raw_text)
    progress.progress(100, text="เสร็จสิ้น")
    progress.empty()

    if isinstance(extracted, dict) and "error" in extracted:
        st.error(extracted["error"])
        st.stop()

    st.session_state["processed_img"] = processed_img
    st.session_state["raw_text"] = raw_text
    st.session_state["formatted_ocr_text"] = clean_and_format_ocr(raw_text)
    st.session_state["result_json"] = normalize_result(extracted)
    st.session_state["file_name"] = file_name


def render_topbar(result=None):
    flags = review_flags(result or {}) if result else []
    review_badge = (
        '<span class="badge badge-warn">รอตรวจสอบบางช่อง</span>'
        if flags
        else '<span class="badge badge-ok">พร้อมยืนยันข้อมูล</span>'
    )
    filename = st.session_state.get("file_name", "ยังไม่ได้เลือกไฟล์")
    st.markdown(
        f"""
        <div class="app-topbar">
          <div class="topbar-grid">
            <div>
              <div class="brand">RecAipt Verification Workspace</div>
              <div class="subtitle">หน้าตรวจสอบใบเสร็จแบบถนอมสายตา แบ่งภาพต้นฉบับและข้อมูลดิจิทัลไว้คู่กัน</div>
            </div>
            <div class="status-row">
              <span class="badge badge-ok">OCR + LLM Pipeline</span>
              {review_badge}
              <span class="badge badge-warn">{filename}</span>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if "result_json" not in st.session_state:
    render_topbar()
    st.markdown(
        """
        <div class="upload-wrap">
          <div class="upload-title">อัปโหลดใบเสร็จเพื่อเริ่มตรวจสอบ</div>
          <div class="upload-subtitle">
            รองรับไฟล์ JPG, PNG และ PDF หน้าแรก ระบบจะปรับภาพด้วย Method 4 แล้วส่งเข้า Typhoon OCR และ Typhoon LLM
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "เลือกไฟล์ใบเสร็จ",
        type=["jpg", "jpeg", "png", "pdf"],
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        run_pipeline(uploaded_file)
        st.rerun()

    st.markdown(
        """
        <div class="upload-wrap">
          <div class="soft-callout">
            คำแนะนำ: วางไฟล์ในพื้นที่อัปโหลดหรือลากมาวางได้โดยตรง หลังประมวลผลแล้วให้ตรวจช่องสีเหลืองก่อน
            จากนั้นใช้ Tab เพื่อเลื่อนไปยังช่องถัดไป และส่งออกข้อมูลเมื่อยืนยันครบถ้วน
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()


result_json = st.session_state["result_json"]
render_topbar(result_json)

left, right = st.columns([0.95, 1.05], gap="medium")

with left:
    st.markdown(
        """
        <div class="pane">
          <div class="pane-head">
            <div class="pane-title">ภาพใบเสร็จหลังปรับคมชัด</div>
            <div class="pane-note">ใช้ซูมและหมุนภาพเพื่อเทียบตัวเลขกับข้อมูลด้านขวา ลดการสลับหน้าจอไปมา</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    zoom_col, rotate_col = st.columns([1, 1])
    with zoom_col:
        zoom = st.slider("ซูมภาพ", min_value=80, max_value=190, value=110, step=10)
    with rotate_col:
        rotation = st.selectbox("หมุนภาพ", [0, 90, 180, 270], format_func=lambda x: f"{x} องศา")

    data_uri = image_to_data_uri(st.session_state["processed_img"], rotation)
    st.markdown(
        f"""
        <div class="image-scroll">
          <img class="receipt-image" src="{data_uri}" style="width:{zoom}%;" alt="processed receipt">
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("ข้อความ OCR ดิบ"):
        st.caption("แสดงแบบจัดบรรทัดเพื่ออ่านง่ายขึ้น โดยยังคงข้อความ OCR ต้นทางไว้สำหรับตรวจสอบ")
        st.code(st.session_state.get("formatted_ocr_text", st.session_state.get("raw_text", "")), language="text")
        copy_button(
            "คัดลอกข้อความ OCR",
            st.session_state.get("formatted_ocr_text", st.session_state.get("raw_text", "")),
            "raw-ocr",
        )

with right:
    flags = review_flags(result_json)
    st.markdown(
        """
        <div class="pane">
          <div class="pane-head">
            <div class="pane-title">ข้อมูลดิจิทัลสำหรับตรวจสอบ</div>
            <div class="pane-note">แก้ไขได้ทุกช่อง ตารางรายการรองรับการใช้คีย์บอร์ดและการเพิ่มแถว</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-band">จุดที่ควรตรวจสอบก่อน</div>', unsafe_allow_html=True)
    if flags:
        st.markdown(
            "<ul class='review-list'>"
            + "".join(f"<li class='needs-check'>{flag}</li>" for flag in flags)
            + "</ul>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<ul class='review-list'><li class='looks-ok'>ข้อมูลหลักครบถ้วนแล้ว ตรวจทานรายการสินค้าและยอดรวมอีกครั้งก่อนส่งออก</li></ul>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="metric-grid">
          <div class="metric">
            <div class="metric-label">ชื่อร้านค้า</div>
            <div class="metric-value">{get_nested(result_json, ["seller", "name"], "-") or "-"}</div>
          </div>
          <div class="metric">
            <div class="metric-label">วันที่เอกสาร</div>
            <div class="metric-value">{result_json.get("document_date") or "-"}</div>
          </div>
          <div class="metric">
            <div class="metric-label">ยอดสุทธิ</div>
            <div class="metric-value">{safe_float(result_json.get("grand_total")):,.2f}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("receipt_verification_form", clear_on_submit=False):
        st.markdown('<div class="section-band">หัวเอกสาร</div>', unsafe_allow_html=True)
        doc_col1, doc_col2 = st.columns([1, 1])
        with doc_col1:
            document_type = st.text_input("ประเภทเอกสาร", value=result_json.get("document_type", ""))
            document_number = st.text_input("เลขที่เอกสาร", value=result_json.get("document_number", ""))
        with doc_col2:
            document_date = st.text_input("วันที่เอกสาร (YYYY-MM-DD)", value=result_json.get("document_date", ""))
            payment_method = st.text_input("วิธีชำระเงิน", value=result_json.get("payment_method", ""))

        st.markdown('<div class="section-band">ผู้ขายและผู้ซื้อ</div>', unsafe_allow_html=True)
        seller_col, buyer_col = st.columns([1, 1])
        with seller_col:
            seller_name = st.text_input("ชื่อร้านค้า / ผู้ขาย", value=get_nested(result_json, ["seller", "name"]))
            seller_tax_id = st.text_input("เลขผู้เสียภาษีผู้ขาย", value=get_nested(result_json, ["seller", "tax_id"]))
            seller_telephone = st.text_input("โทรศัพท์ผู้ขาย", value=get_nested(result_json, ["seller", "telephone"]))
            seller_address = st.text_area("ที่อยู่ผู้ขาย", value=get_nested(result_json, ["seller", "address"]))
        with buyer_col:
            buyer_name = st.text_input("ชื่อผู้ซื้อ", value=get_nested(result_json, ["buyer", "name"]))
            buyer_tax_id = st.text_input("เลขผู้เสียภาษีผู้ซื้อ", value=get_nested(result_json, ["buyer", "tax_id"]))
            buyer_address = st.text_area("ที่อยู่ผู้ซื้อ", value=get_nested(result_json, ["buyer", "address"]))

        st.markdown('<div class="section-band">รายการสินค้าและบริการ</div>', unsafe_allow_html=True)
        edited_items = st.data_editor(
            result_json.get("items", []),
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "รายการ": st.column_config.TextColumn("รายการ", width="large"),
                "จำนวน": st.column_config.NumberColumn("จำนวน", min_value=0.0, step=1.0, format="%.2f"),
                "ราคาต่อหน่วย": st.column_config.NumberColumn("ราคาต่อหน่วย", min_value=0.0, step=0.25, format="%.2f"),
                "รวม": st.column_config.NumberColumn("รวม", min_value=0.0, step=0.25, format="%.2f"),
                "สถานะ": st.column_config.SelectboxColumn(
                    "สถานะ",
                    options=["มั่นใจ", "ตรวจสอบ", "กรอกเอง"],
                    required=True,
                ),
            },
            key="items_editor",
        )

        st.markdown('<div class="section-band">สรุปยอด</div>', unsafe_allow_html=True)
        tax_mode = st.selectbox(
            "รูปแบบ VAT",
            ["VAT รวมในราคาสินค้า", "VAT แยกบวกเพิ่ม"],
            index=0 if result_json.get("tax_included", True) else 1,
            help="ใบเสร็จร้านค้าปลีก เช่น 7-Eleven มักเป็น VAT รวมในราคาสินค้า ไม่ควรบวก VAT ซ้ำอีกครั้ง",
        )
        tax_included = tax_mode == "VAT รวมในราคาสินค้า"
        total_col1, total_col2, total_col3 = st.columns([1, 1, 1])
        with total_col1:
            suggested_before_tax, suggested_vat = derive_vat_values(
                result_json.get("grand_total"),
                result_json.get("vat_rate", 7.0),
                tax_included=tax_included,
            )
            amount_before_tax = st.number_input(
                "ยอดก่อนภาษี",
                value=safe_float(result_json.get("amount_before_tax")) or suggested_before_tax,
                min_value=0.0,
                step=0.25,
                format="%.2f",
            )
        with total_col2:
            vat_rate = st.number_input(
                "VAT (%)",
                value=safe_float(result_json.get("vat_rate"), 7.0),
                min_value=0.0,
                step=0.5,
                format="%.2f",
            )
            vat_amount = st.number_input(
                "จำนวน VAT",
                value=safe_float(result_json.get("vat_amount")) or suggested_vat,
                min_value=0.0,
                step=0.25,
                format="%.2f",
            )
        with total_col3:
            grand_total = st.number_input(
                "ยอดสุทธิ",
                value=safe_float(result_json.get("grand_total")),
                min_value=0.0,
                step=0.25,
                format="%.2f",
            )

        st.markdown(
            """
            <div class="action-pad">
              <div class="tiny-note">
                ใช้ <span class="kbd">Tab</span> เพื่อย้ายช่องกรอกข้อมูล และตรวจช่องที่ยังเป็นสีเตือนก่อนบันทึก
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        save_local = st.form_submit_button("ยืนยันข้อมูลบนหน้านี้", type="primary", use_container_width=True)

    current_values = {
        "document_type": document_type,
        "document_number": document_number,
        "document_date": document_date,
        "payment_method": payment_method,
        "seller_name": seller_name,
        "seller_tax_id": seller_tax_id,
        "seller_telephone": seller_telephone,
        "seller_address": seller_address,
        "buyer_name": buyer_name,
        "buyer_tax_id": buyer_tax_id,
        "buyer_address": buyer_address,
        "tax_included": tax_included,
        "amount_before_tax": amount_before_tax,
        "vat_rate": vat_rate,
        "vat_amount": vat_amount,
        "grand_total": grand_total,
    }
    export_payload = build_export_payload(current_values, edited_items)

    if save_local:
        st.session_state["result_json"] = normalize_result(export_payload)
        st.success("บันทึกค่าที่ตรวจสอบไว้บนหน้านี้แล้ว")
        st.rerun()

    st.markdown('<div class="section-band">เครื่องมือส่งออก</div>', unsafe_allow_html=True)
    export_col1, export_col2, export_col3, export_col4 = st.columns([1, 1, 1, 1])
    with export_col1:
        output_name = (export_payload.get("document_number") or "receipt").replace("/", "-")
        st.download_button(
            "ดาวน์โหลด CSV",
            data=build_receipt_csv(export_payload).encode("utf-8-sig"),
            file_name=f"{output_name}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with export_col2:
        st.download_button(
            "ดาวน์โหลด JSON",
            data=json.dumps(export_payload, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"{output_name}.json",
            mime="application/json",
            use_container_width=True,
        )
    with export_col3:
        copy_button("คัดลอก JSON", json.dumps(export_payload, ensure_ascii=False, indent=2), "json")
    with export_col4:
        if st.button("เริ่มใบใหม่", use_container_width=True):
            reset_app()
            st.rerun()

    db_col, total_copy_col = st.columns([1, 1])
    with db_col:
        if st.button("ส่งออกไป Supabase", type="primary", use_container_width=True):
            try:
                receipt_id = save_to_supabase(export_payload)
                st.success(f"บันทึกลง Supabase แล้ว (receipt_id: {receipt_id})")
            except Exception as exc:
                st.error(f"ยังส่งออกไป Supabase ไม่สำเร็จ: {exc}")
    with total_copy_col:
        copy_button("คัดลอกยอดสุทธิ", f"{safe_float(export_payload.get('grand_total')):,.2f}", "grand-total")
