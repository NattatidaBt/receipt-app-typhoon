import cv2
import streamlit as st
import streamlit.components.v1 as components

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
# INJECT CSS + JS (stable กว่า st.markdown สำหรับ uploader)
# =========================================================
components.html("""
<script>
function applyStyles() {
    // ── ซ่อน Streamlit chrome ──
    const hide = ['header','footer','#MainMenu',
        '[data-testid="stToolbar"]','[data-testid="stSidebar"]'];
    hide.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => {
            el.style.cssText = 'visibility:hidden!important;display:none!important;height:0!important';
        });
    });

    // ── Uploader dropzone ──
    document.querySelectorAll('[data-testid="stFileUploaderDropzone"]').forEach(el => {
        el.style.cssText = `
            background: white !important;
            border: 2px dashed #F4C6D5 !important;
            border-radius: 28px !important;
            min-height: 220px !important;
            display: flex !important;
            flex-direction: column !important;
            align-items: center !important;
            justify-content: center !important;
            cursor: pointer !important;
        `;
        // ซ่อน SVG icon เดิม
        el.querySelectorAll('svg').forEach(s => s.style.display = 'none');
    });

    // ── ปุ่ม Browse เดิม ──
    document.querySelectorAll('[data-testid="stFileUploaderDropzone"] button').forEach(btn => {
        btn.style.cssText = `
            background: #F8D7E3 !important;
            color: #A35271 !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            padding: 8px 24px !important;
        `;
    });
}

// รัน 3 รอบเพื่อให้แน่ใจว่า DOM โหลดครบ
applyStyles();
setTimeout(applyStyles, 500);
setTimeout(applyStyles, 1500);

// Observer สำหรับ dynamic re-render
const observer = new MutationObserver(applyStyles);
observer.observe(document.body, { childList: true, subtree: true });
</script>
""", height=0)

# =========================================================
# GLOBAL CSS (ส่วนที่ไม่เกี่ยวกับ uploader)
# =========================================================
st.markdown("""
<style>
header, footer, #MainMenu,
[data-testid="stToolbar"],
[data-testid="stSidebar"] {
    visibility: hidden !important;
    display: none !important;
    height: 0 !important;
}

.stApp { background-color: #FFF3F7 !important; }

.block-container {
    max-width: 100% !important;
    padding: 1.5rem 3rem !important;
}

/* Header */
.header-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 28px;
    margin-bottom: 40px;
    background: #FFFFFF;
    border-radius: 18px;
    box-shadow: 0 2px 12px rgba(74,46,53,0.06);
}
.logo-text {
    color: #4A2E35;
    font-size: 20px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 8px;
}
.lang-pill {
    background: #C97D98;
    color: white;
    padding: 7px 16px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 500;
}

/* Hero */
.hero-title {
    text-align: center;
    color: #4A2E35;
    font-size: 32px;
    font-weight: 500;
    margin: 20px 0 10px;
}
.hero-subtitle {
    text-align: center;
    color: #C29BA4;
    font-size: 15px;
    margin-bottom: 36px;
}

/* Uploader container width */
section[data-testid="stFileUploader"] {
    max-width: 780px;
    margin: 0 auto 32px;
}

/* Result wrapper */
.result-wrapper {
    background: white;
    border-radius: 26px;
    padding: 26px;
    border: 1px solid #F4E0E8;
    box-shadow: 0 8px 30px rgba(0,0,0,0.03);
}
div[data-testid="stHorizontalBlock"] {
    gap: 26px !important;
    align-items: flex-start !important;
}

/* Image card */
.img-card-wrap {
    background: #FAFAFA;
    border-radius: 18px;
    padding: 14px;
    border: 1px solid #F4C6D5;
}

/* Streamlit buttons */
div[data-testid="stButton"] > button {
    background: #F8D7E3 !important;
    color: #A35271 !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
}
.back-wrap div[data-testid="stButton"] > button {
    width: 42px !important;
    height: 42px !important;
    font-size: 18px !important;
    padding: 0 !important;
    margin-top: 10px !important;
}
.export-wrap div[data-testid="stButton"] > button {
    width: 100% !important;
    height: 44px !important;
    font-size: 14px !important;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# HEADER
# =========================================================
st.markdown("""
<div class="header-bar">
    <div class="logo-text">📄 RecAipt</div>
    <div class="lang-pill">English ▾</div>
</div>
""", unsafe_allow_html=True)


# =========================================================
# HELPERS
# =========================================================
def reset_app():
    st.session_state.clear()

def safe_float(value, default=0.0):
    try:
        return float(str(value).replace(",", "").strip())
    except Exception:
        return default

def safe_int(value, default=1):
    try:
        return int(float(str(value).replace(",", "").strip()))
    except Exception:
        return default

def build_detail_card_html(extracted_json):
    """สร้าง HTML ของ detail card — render ด้วย components.html() เพื่อหลีกเลี่ยง Streamlit escape"""
    merchant     = extracted_json.get("store_name",   "—") or "—"
    receipt_no   = extracted_json.get("receipt_no",   "—") or "—"
    date_val     = extracted_json.get("date",         "—") or "—"
    receipt_type = extracted_json.get("receipt_type", "ใบกำกับภาษีอย่างย่อ") or "ใบกำกับภาษีอย่างย่อ"
    items_list   = extracted_json.get("items", []) or []
    subtotal_val = safe_float(extracted_json.get("subtotal", 0))
    vat_val      = safe_float(extracted_json.get("vat",      0))
    total_val    = safe_float(extracted_json.get("total",    0))

    rows_html = ""
    for idx, item in enumerate(items_list):
        name  = item.get("name", "")
        qty   = safe_int(item.get("qty", 1))
        price = safe_float(item.get("unit_price", 0))
        amt   = qty * price
        rows_html += f"""
        <tr>
            <td class="num">{idx + 1}</td>
            <td>{name}</td>
            <td>{qty}</td>
            <td>{price:,.2f}</td>
            <td style="text-align:right">{amt:,.2f}</td>
        </tr>"""

    if not rows_html:
        rows_html = '<tr><td colspan="5" style="text-align:center;color:#C29BA4;padding:16px 0">ไม่พบรายการสินค้า</td></tr>'

    subtotal_row = (f'<div class="t-row"><span>ยอดก่อน VAT :</span>'
                    f'<span>{subtotal_val:,.2f} บาท</span></div>') if subtotal_val else ""
    vat_row      = (f'<div class="t-row"><span>VAT 7% :</span>'
                    f'<span>{vat_val:,.2f} บาท</span></div>') if vat_val else ""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:transparent; }}
.card {{ background:white; border-radius:18px; border:1px solid #F4C6D5; overflow:hidden; }}
.dc-header {{
    display:flex; justify-content:space-between; align-items:center;
    padding:14px 18px; border-bottom:1px solid #F4E0E8;
}}
.dc-title {{ font-size:15px; font-weight:700; color:#4A2E35; }}
.icon-btn {{
    background:transparent; border:none; cursor:pointer;
    font-size:17px; padding:3px 6px; border-radius:6px; color:#C97D98;
}}
.icon-btn:hover {{ background:#FFF0F5; }}
.dc-body {{ padding:16px 18px; }}
.badge {{
    display:inline-block; background:#FFF0F5; color:#A35271;
    border:1px solid #F4C6D5; border-radius:8px;
    font-size:12px; padding:4px 12px; margin-bottom:16px;
}}
.info-row {{ display:flex; gap:8px; font-size:13px; margin-bottom:9px; align-items:baseline; }}
.lbl {{ color:#C29BA4; min-width:120px; flex-shrink:0; }}
.val {{ color:#4A2E35; font-weight:600; }}
.divider {{ border:none; border-top:1px solid #F4E0E8; margin:14px 0; }}
.sec-lbl {{ font-size:12px; color:#C29BA4; margin-bottom:8px; }}
.tbl {{ width:100%; border-collapse:collapse; font-size:13px; }}
.tbl th {{
    color:#C29BA4; font-weight:400; padding:4px 6px 9px;
    border-bottom:1px solid #F4E0E8; text-align:center;
}}
.tbl th:nth-child(2) {{ text-align:left; }}
.tbl td {{ padding:8px 6px; color:#4A2E35; text-align:center; }}
.tbl td:nth-child(2) {{ text-align:left; }}
.num {{ color:#C29BA4; font-size:12px; }}
.totals {{ padding-top:4px; }}
.t-row {{
    display:flex; justify-content:space-between;
    font-size:13px; color:#A07A85; margin-bottom:7px;
}}
.grand {{ color:#4A2E35; font-weight:700; font-size:14px; margin-bottom:0; }}
.dc-footer {{
    display:flex; justify-content:flex-end; align-items:center;
    gap:8px; padding:11px 18px 15px; border-top:1px solid #F4E0E8;
}}
.f-btn {{
    background:white; border:1px solid #F4C6D5; color:#A35271;
    border-radius:10px; width:36px; height:36px; font-size:15px;
    cursor:pointer; display:inline-flex; align-items:center; justify-content:center;
}}
.f-btn:hover {{ background:#FFF0F5; }}
</style>
</head>
<body>
<div class="card">
  <div class="dc-header">
    <span class="dc-title">รายละเอียดใบเสร็จ</span>
    <div>
      <button class="icon-btn" title="แก้ไข">✏️</button>
      <button class="icon-btn" title="ลบ">🗑️</button>
    </div>
  </div>
  <div class="dc-body">
    <span class="badge">{receipt_type}</span>
    <div class="info-row"><span class="lbl">ร้านค้า / ผู้ขาย :</span><span class="val">{merchant}</span></div>
    <div class="info-row"><span class="lbl">เลขที่ใบเสร็จ :</span><span class="val">{receipt_no}</span></div>
    <div class="info-row"><span class="lbl">วันที่ :</span><span class="val">{date_val}</span></div>
    <hr class="divider">
    <div class="sec-lbl">รายการสินค้า</div>
    <table class="tbl">
      <thead>
        <tr>
          <th style="width:32px">ลำดับ</th>
          <th>รายการ</th>
          <th style="width:50px">จำนวน</th>
          <th style="width:60px">ราคา</th>
          <th style="width:60px;text-align:right">รวม</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    <hr class="divider">
    <div class="totals">
      {subtotal_row}
      {vat_row}
      <div class="t-row grand">
        <span>ยอดรวม :</span>
        <span>{total_val:,.2f} บาท</span>
      </div>
    </div>
  </div>
  <div class="dc-footer">
    <button class="f-btn" title="คัดลอก">📋</button>
    <button class="f-btn" title="แชร์">↑</button>
  </div>
</div>
</body>
</html>"""


# =========================================================
# PAGE 1 : UPLOAD
# =========================================================
if "processed_img" not in st.session_state or st.session_state.get("file_uploaded") is None:

    st.markdown("<div class='hero-title'>Receipt scanning and data collection tools</div>",
                unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>Upload an image or PDF of your receipt to store it using OCR</div>",
                unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "",
        type=["jpg", "jpeg", "png", "pdf"],
        key="uploader_widget",
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        st.session_state["file_uploaded"] = uploaded_file
        file_bytes = uploaded_file.read()
        file_name  = uploaded_file.name

        with st.spinner("⏳ Processing image..."):
            img = load_image_or_pdf(file_bytes, file_name)
            if img is None:
                st.error("❌ Unsupported file")
                st.stop()
            deskewed  = deskew_image(img)
            processed = process_method_4_sharpening(deskewed)
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
# PAGE 2 : RESULT
# =========================================================
else:
    processed_img  = st.session_state["processed_img"]
    raw_text       = st.session_state["raw_text"]
    extracted_json = st.session_state["extracted_json"]

    has_error = (
        isinstance(extracted_json, dict)
        and "error" in extracted_json
        and extracted_json["error"]
    )

    st.markdown('<div class="result-wrapper">', unsafe_allow_html=True)
    col_left, col_right = st.columns([1, 1])

    # ── LEFT: รูปใบเสร็จ ──────────────────────────────────
    with col_left:
        st.markdown('<div class="img-card-wrap">', unsafe_allow_html=True)

        if len(processed_img.shape) == 2:
            display_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2RGB)
        else:
            display_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)

        st.image(display_img, use_container_width=True)

        with st.expander("📄 Raw OCR Text"):
            st.code(raw_text, language="text")

        st.markdown('<div class="back-wrap">', unsafe_allow_html=True)
        st.button("←", key="back_btn", on_click=reset_app)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)  # img-card-wrap

    # ── RIGHT: รายละเอียดใบเสร็จ ─────────────────────────
    with col_right:
        if has_error:
            st.error(f"❌ {extracted_json['error']}")
        else:
            # คำนวณความสูง card
            items_count = len(extracted_json.get("items", []) or [])
            card_height = 500 + max(0, items_count - 3) * 38

            # render HTML ผ่าน iframe เพื่อหลีกเลี่ยง Streamlit escaping
            components.html(
                build_detail_card_html(extracted_json),
                height=card_height,
                scrolling=False,
            )

            # ปุ่ม ส่งออก
            st.markdown('<div class="export-wrap">', unsafe_allow_html=True)
            if st.button("📤  ส่งออก", key="export_btn"):
                items_list = extracted_json.get("items", []) or []
                export_items = [
                    {
                        "name":       it.get("name", ""),
                        "qty":        safe_int(it.get("qty", 1)),
                        "unit_price": safe_float(it.get("unit_price", 0)),
                        "amount":     safe_int(it.get("qty", 1)) * safe_float(it.get("unit_price", 0)),
                    }
                    for it in items_list
                ]
                st.success("🎉 บันทึกข้อมูลเรียบร้อยแล้ว")
                st.json({
                    "store_name": extracted_json.get("store_name", "—"),
                    "receipt_no": extracted_json.get("receipt_no",  "—"),
                    "date":       extracted_json.get("date",        "—"),
                    "items":      export_items,
                    "subtotal":   safe_float(extracted_json.get("subtotal", 0)),
                    "vat":        safe_float(extracted_json.get("vat",      0)),
                    "total":      safe_float(extracted_json.get("total",    0)),
                })
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)  # result-wrapper