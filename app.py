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
# GLOBAL CSS
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

.stApp { 
    background-color: #FFF2F6 !important; 
}

.block-container {
    max-width: 100% !important;
    padding: 1.5rem 3rem !important;
}

.header-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 28px;
    margin-bottom: 40px;
    background: #FFFFFF;
    border-radius: 18px;
    box-shadow: 0 4px 15px rgba(74, 46, 53, 0.02);
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

.hero-title {
    text-align: center;
    color: #4A2E35;
    font-size: 32px;
    font-weight: 500;
    margin: 35px 0 10px;
}
.hero-subtitle {
    text-align: center;
    color: #C29BA4;
    font-size: 15px;
    margin-bottom: 45px;
}

section[data-testid="stFileUploader"] {
    max-width: 780px;
    margin: 0 auto !important;
    position: relative !important;
}

section[data-testid="stFileUploader"] > div {
    background-color: #FFFFFF !important;
    border: 2px dashed #F4C6D5 !important;
    border-radius: 28px !important;
    height: 240px !important;
    min-height: 240px !important;
    position: relative !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-shadow: 0 12px 35px rgba(74, 46, 53, 0.03) !important;
    padding: 0 !important;
}

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

div[data-testid="stFileUploaderDropzone"] {
    background: transparent !important;
    border: none !important;
    width: 100% !important;
    height: 240px !important;
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

section[data-testid="stFileUploader"]::after {
    content: "📄\A\A Choose or paste a file here (image or PDF)";
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
    line-height: 1.2;
}

/* ── Result wrapper ── */
.result-wrapper {
    background: #FFFFFF;
    border-radius: 32px;
    padding: 35px;
    max-width: 1450px;
    margin: 0 auto !important;
    box-shadow: 0 12px 40px rgba(74, 46, 53, 0.04);
}

div[data-testid="stHorizontalBlock"] {
    gap: 30px !important;
    align-items: flex-start !important;
}

.img-card-wrap {
    background: #FAFAFA;
    border-radius: 24px;
    padding: 15px;
    border: 1px solid #F8D7E3;
    position: relative;
}

/* ซ่อน expander ทั้งหมดใน result page */
.hide-expander [data-testid="stExpander"] {
    display: none !important;
}

/* zoom button overlay */
.zoom-btn-wrap {
    position: absolute;
    bottom: 24px;
    right: 24px;
}
.zoom-btn-wrap div[data-testid="stButton"] > button {
    width: 36px !important;
    height: 36px !important;
    border-radius: 50% !important;
    background: rgba(255,255,255,0.9) !important;
    color: #4A2E35 !important;
    font-size: 14px !important;
    padding: 0 !important;
    box-shadow: 0 2px 8px rgba(74,46,53,0.15) !important;
    border: 1px solid #F4C6D5 !important;
}

div[data-testid="stHtml"] {
    padding: 0 !important;
    margin: 0 !important;
}
iframe {
    display: block !important;
    margin: 0 auto !important;
    border-radius: 24px !important;
}

/* ── back button (ใน result card header) ── */
.back-icon-wrap div[data-testid="stButton"] > button {
    width: 36px !important;
    height: 36px !important;
    border-radius: 50% !important;
    background: #F8D7E3 !important;
    color: #A35271 !important;
    font-size: 16px !important;
    padding: 0 !important;
    border: none !important;
    margin: 0 !important;
}

/* ── export action bar buttons ── */
.action-bar-wrap {
    display: flex;
    gap: 10px;
    margin-top: 16px;
}
.action-bar-wrap div[data-testid="stButton"] {
    flex: 1;
}
.action-bar-wrap div[data-testid="stButton"] > button {
    width: 100% !important;
    height: 44px !important;
    font-size: 14px !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
}
/* ปุ่มส่งออกสีชมพูเข้ม */
.export-primary div[data-testid="stButton"] > button {
    background: #C97D98 !important;
    color: white !important;
}
.export-primary div[data-testid="stButton"] > button:hover {
    background: #A35271 !important;
}

/* ── bottom left back arrow ── */
.bottom-back-wrap div[data-testid="stButton"] > button {
    width: 44px !important;
    height: 44px !important;
    border-radius: 50% !important;
    background: #F8D7E3 !important;
    color: #A35271 !important;
    font-size: 18px !important;
    padding: 0 !important;
    border: none !important;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# HEADER COMPONENT
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
    """Card HTML พร้อม Edit/Delete icons ใน header ตรงตาม Target UI"""
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

    subtotal_row = f'<div class="t-row"><span>ยอดก่อน VAT :</span><span>{subtotal_val:,.2f} บาท</span></div>' if subtotal_val else ""
    vat_row      = f'<div class="t-row"><span>VAT 7% :</span><span>{vat_val:,.2f} บาท</span></div>' if vat_val else ""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:transparent; padding:2px; }}
.card {{ background:#FFF6F8; border-radius:24px; border:1px solid #F8D7E3; padding:24px 28px; overflow:hidden; }}

/* ── Header row: back + title + icons ── */
.dc-header {{
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:20px;
}}
.dc-back {{
    width:32px; height:32px;
    border-radius:50%;
    background:#F8D7E3;
    color:#A35271;
    border:none;
    font-size:16px;
    cursor:pointer;
    display:flex; align-items:center; justify-content:center;
    flex-shrink:0;
}}
.dc-title {{
    font-size:17px;
    font-weight:700;
    color:#4A2E35;
    flex:1;
    text-align:center;
}}
.dc-icons {{
    display:flex;
    gap:8px;
    flex-shrink:0;
}}
.icon-btn {{
    width:32px; height:32px;
    border-radius:8px;
    background:#FFF0F5;
    color:#A35271;
    border:1px solid #F4C6D5;
    font-size:14px;
    cursor:pointer;
    display:flex; align-items:center; justify-content:center;
}}
.icon-btn:hover {{ background:#F4C6D5; }}

.dc-body {{ margin-top:4px; }}
.badge {{ display:inline-block; background:#FFF0F5; color:#A35271; border:1px solid #F4C6D5; border-radius:8px; font-size:12px; padding:4px 12px; margin-bottom:16px; }}
.info-row {{ display:flex; gap:8px; font-size:13px; margin-bottom:12px; align-items:baseline; }}
.lbl {{ color:#7A5A63; min-width:130px; flex-shrink:0; font-weight:500; }}
.val {{ color:#4A2E35; font-weight:600; }}
.divider {{ border:none; border-top:1px solid #F4E0E8; margin:16px 0; }}
.sec-lbl {{ font-size:13px; color:#4A2E35; font-weight:bold; margin-bottom:12px; }}
.tbl {{ width:100%; border-collapse:collapse; font-size:13px; }}
.tbl th {{ color:#C29BA4; font-weight:400; padding:4px 6px 9px; border-bottom:1px solid #F4E0E8; text-align:center; }}
.tbl th:nth-child(2) {{ text-align:left; }}
.tbl td {{ padding:8px 6px; color:#4A2E35; text-align:center; border-bottom:1px dashed #FFF0F5; }}
.tbl td:nth-child(2) {{ text-align:left; }}
.num {{ color:#C29BA4; font-size:12px; }}
.totals {{ padding-top:14px; }}
.t-row {{ display:flex; justify-content:space-between; font-size:13px; color:#A07A85; margin-bottom:8px; }}
.grand {{ color:#4A2E35; font-weight:700; font-size:15px; }}
</style>
</head>
<body>
<div class="card">
  <!-- Header: back + title + edit/delete -->
  <div class="dc-header">
    <button class="dc-back" onclick="window.parent.postMessage('back','*')">←</button>
    <span class="dc-title">รายละเอียดใบเสร็จ</span>
    <div class="dc-icons">
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
    <div class="sec-lbl">📦 รายการสินค้า</div>
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
</div>
</body>
</html>"""


# =========================================================
# PAGE 1 : UPLOAD
# =========================================================
if "processed_img" not in st.session_state or st.session_state.get("file_uploaded") is None:

    st.markdown("<div class='hero-title'>Receipt scanning and data collection tools</div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>Upload an image or PDF of your receipt to store it using OCR</div>", unsafe_allow_html=True)

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

        # ปุ่ม zoom มุมล่างขวาของรูป
        st.markdown('<div class="zoom-btn-wrap">', unsafe_allow_html=True)
        st.button("⤢", key="zoom_btn")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)  # img-card-wrap

        # ── ปุ่ม back arrow ใต้รูป (ซ้ายล่าง) ──
        st.markdown('<div class="bottom-back-wrap">', unsafe_allow_html=True)
        st.button("←", key="back_btn", on_click=reset_app)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── RIGHT: รายละเอียดใบเสร็จ ─────────────────────────
    with col_right:
        if has_error:
            st.error(f"❌ {extracted_json['error']}")
        else:
            items_count = len(extracted_json.get("items", []) or [])
            card_height = 430 + max(0, items_count - 2) * 38

            # render HTML card (มี back/edit/delete ใน header แล้ว)
            components.html(
                build_detail_card_html(extracted_json),
                height=card_height,
                scrolling=False,
            )

            # ── Action bar: 3 ปุ่มล่างสุด ──
            st.markdown('<div class="action-bar-wrap">', unsafe_allow_html=True)

            btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1.4])

            with btn_col1:
                st.button("📋  คัดลอก", key="copy_btn")

            with btn_col2:
                st.button("📤  แชร์", key="share_btn")

            with btn_col3:
                st.markdown('<div class="export-primary">', unsafe_allow_html=True)
                if st.button("⬇️  ส่งออก", key="export_btn"):
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

            st.markdown('</div>', unsafe_allow_html=True)  # action-bar-wrap

    st.markdown('</div>', unsafe_allow_html=True)  # result-wrapper