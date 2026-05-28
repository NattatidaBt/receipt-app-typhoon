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
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20,400,1,0');

.material-symbols-rounded {
    font-family: 'Material Symbols Rounded';
    font-weight: normal;
    font-style: normal;
    font-size: 20px;
    line-height: 1;
    letter-spacing: normal;
    text-transform: none;
    display: inline-block;
    white-space: nowrap;
    word-wrap: normal;
    direction: ltr;
    -webkit-font-feature-settings: 'liga';
    font-feature-settings: 'liga';
    -webkit-font-smoothing: antialiased;
}

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

/* ── Header Bar ── */
.header-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 28px;
    margin-bottom: 40px;
    background: #FFFFFF;
    border-radius: 18px;
    box-shadow: 0 4px 15px rgba(74,46,53,0.02);
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

/* ── Hero text ── */
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

/* ══════════════════════════════════════════
   UPLOAD ZONE
══════════════════════════════════════════ */
[data-testid="stFileUploader"] {
    max-width: 780px !important;
    margin: 0 auto !important;
    display: block !important;
}

[data-testid="stFileUploaderDropzone"] {
    background: #FFFFFF !important;
    border: 2px dashed #F4C6D5 !important;
    border-radius: 28px !important;
    min-height: 220px !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 40px 30px !important;
    box-shadow: 0 12px 35px rgba(74,46,53,0.03) !important;
    cursor: pointer !important;
}

[data-testid="stFileUploaderDropzone"] svg {
    display: none !important;
}

[data-testid="stFileUploaderDropzoneInstructions"] > div > span,
[data-testid="stFileUploaderDropzoneInstructions"] > div > small {
    display: none !important;
}

[data-testid="stFileUploaderDropzoneInstructions"] {
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
    gap: 0 !important;
}
[data-testid="stFileUploaderDropzoneInstructions"]::before {
    content: "description";
    font-family: 'Material Symbols Rounded';
    font-size: 48px;
    color: #C97D98;
    line-height: 1;
    margin-bottom: 14px;
    display: block;
    font-weight: normal;
    font-style: normal;
    -webkit-font-feature-settings: 'liga';
    font-feature-settings: 'liga';
}
[data-testid="stFileUploaderDropzoneInstructions"]::after {
    content: "Choose or paste a file here (image or PDF)";
    color: #A3858C;
    font-size: 15px;
    display: block;
    margin-top: 10px;
    text-align: center;
}

[data-testid="stFileUploader"] label {
    display: none !important;
}

[data-testid="stFileUploaderDropzoneInputButton"] {
    opacity: 0 !important;
    position: absolute !important;
    width: 100% !important;
    height: 100% !important;
    top: 0 !important;
    left: 0 !important;
    cursor: pointer !important;
}

/* ── Result wrapper ── */
.result-wrapper {
    background: #FFFFFF;
    border-radius: 32px;
    padding: 35px;
    max-width: 1450px;
    margin: 0 auto !important;
    box-shadow: 0 12px 40px rgba(74,46,53,0.04);
}

[data-testid="stHorizontalBlock"] {
    gap: 30px !important;
    align-items: flex-start !important;
}

.img-card-wrap {
    background: #F5F5F5;
    border-radius: 24px;
    overflow: hidden;
    border: 1px solid #F8D7E3;
    position: relative;
}

[data-testid="stHtml"] {
    padding: 0 !important;
    margin: 0 !important;
}
iframe {
    display: block !important;
    margin: 0 auto !important;
    border-radius: 24px !important;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# HEADER
# =========================================================
st.markdown("""
<div class="header-bar">
    <div class="logo-text">
        <span class="material-symbols-rounded" style="font-size:22px;color:#C97D98">receipt_long</span>
        RecAipt
    </div>
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
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20,400,1,0" rel="stylesheet">
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    background:transparent;
    padding:2px;
}}
.material-symbols-rounded {{
    font-family:'Material Symbols Rounded';
    font-weight:normal;
    font-style:normal;
    font-size:18px;
    line-height:1;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    -webkit-font-feature-settings:'liga';
    font-feature-settings:'liga';
    -webkit-font-smoothing:antialiased;
    user-select:none;
}}
.card {{
    background:#FFF6F8;
    border-radius:24px;
    border:1px solid #F8D7E3;
    padding:24px 28px;
    overflow:hidden;
}}
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
    cursor:pointer;
    display:flex; align-items:center; justify-content:center;
    flex-shrink:0;
    transition:background 0.15s;
}}
.dc-back:hover {{ background:#F4C6D5; }}
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
    cursor:pointer;
    display:flex; align-items:center; justify-content:center;
    transition:background 0.15s;
}}
.icon-btn:hover {{ background:#F4C6D5; }}
.badge {{
    display:inline-block;
    background:#FFF0F5;
    color:#A35271;
    border:1px solid #F4C6D5;
    border-radius:8px;
    font-size:12px;
    padding:4px 12px;
    margin-bottom:16px;
}}
.info-row {{
    display:flex; gap:8px;
    font-size:13px;
    margin-bottom:12px;
    align-items:baseline;
}}
.lbl {{ color:#7A5A63; min-width:130px; flex-shrink:0; font-weight:500; }}
.val {{ color:#4A2E35; font-weight:600; }}
.divider {{ border:none; border-top:1px solid #F4E0E8; margin:16px 0; }}
.sec-lbl {{
    font-size:13px; color:#4A2E35; font-weight:bold;
    margin-bottom:12px;
    display:flex; align-items:center; gap:6px;
}}
.tbl {{ width:100%; border-collapse:collapse; font-size:13px; }}
.tbl th {{
    color:#C29BA4; font-weight:400;
    padding:4px 6px 9px;
    border-bottom:1px solid #F4E0E8;
    text-align:center;
}}
.tbl th:nth-child(2) {{ text-align:left; }}
.tbl td {{
    padding:8px 6px; color:#4A2E35;
    text-align:center;
    border-bottom:1px dashed #FFF0F5;
}}
.tbl td:nth-child(2) {{ text-align:left; }}
.num {{ color:#C29BA4; font-size:12px; }}
.totals {{ padding-top:14px; }}
.t-row {{
    display:flex;
    justify-content:space-between;
    font-size:13px; color:#A07A85; margin-bottom:8px;
}}
.grand {{ color:#4A2E35; font-weight:700; font-size:15px; }}
</style>
</head>
<body>
<div class="card">
  <div class="dc-header">
    <button class="dc-back">
      <span class="material-symbols-rounded">arrow_back</span>
    </button>
    <span class="dc-title">รายละเอียดใบเสร็จ</span>
    <div class="dc-icons">
      <button class="icon-btn" title="แก้ไข">
        <span class="material-symbols-rounded">edit</span>
      </button>
      <button class="icon-btn" title="ลบ">
        <span class="material-symbols-rounded">delete</span>
      </button>
    </div>
  </div>
  <div class="dc-body">
    <span class="badge">{receipt_type}</span>
    <div class="info-row"><span class="lbl">ร้านค้า / ผู้ขาย :</span><span class="val">{merchant}</span></div>
    <div class="info-row"><span class="lbl">เลขที่ใบเสร็จ :</span><span class="val">{receipt_no}</span></div>
    <div class="info-row"><span class="lbl">วันที่ :</span><span class="val">{date_val}</span></div>
    <hr class="divider">
    <div class="sec-lbl">
      <span class="material-symbols-rounded" style="color:#C97D98;font-size:16px">inventory_2</span>
      รายการสินค้า
    </div>
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


def build_action_bar_html():
    """Action bar 3 ปุ่มเรียงแถวเดียว พร้อม Material Icons"""
    return """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20,400,1,0" rel="stylesheet">
<style>
* { box-sizing:border-box; margin:0; padding:0; }
body {
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    background:transparent;
}
.material-symbols-rounded {
    font-family:'Material Symbols Rounded';
    font-weight:normal;
    font-style:normal;
    font-size:18px;
    line-height:1;
    display:inline-flex;
    align-items:center;
    -webkit-font-feature-settings:'liga';
    font-feature-settings:'liga';
    -webkit-font-smoothing:antialiased;
    user-select:none;
}
.bar {
    display:flex;
    gap:10px;
    width:100%;
    padding:2px;
}
.btn {
    flex:1;
    height:44px;
    border-radius:12px;
    display:flex;
    align-items:center;
    justify-content:center;
    gap:7px;
    font-size:14px;
    font-weight:600;
    cursor:pointer;
    border:1px solid #F4C6D5;
    background:#FFF0F5;
    color:#A35271;
    transition:background 0.15s, transform 0.1s;
    font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
}
.btn:hover { background:#F4C6D5; transform:translateY(-1px); }
.btn:active { transform:translateY(0); }
.btn.primary {
    background:#C97D98;
    color:#FFFFFF;
    border:none;
}
.btn.primary:hover { background:#A35271; }
</style>
</head>
<body>
<div class="bar">
  <button class="btn">
    <span class="material-symbols-rounded">content_copy</span>
    คัดลอก
  </button>
  <button class="btn">
    <span class="material-symbols-rounded">share</span>
    แชร์
  </button>
  <button class="btn primary">
    <span class="material-symbols-rounded">download</span>
    ส่งออก
  </button>
</div>
</body>
</html>"""


def build_img_controls_html():
    """ปุ่ม back (ซ้าย) และ zoom (ขวา) ใต้รูป เรียงแถวเดียวกัน"""
    return """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20,400,1,0" rel="stylesheet">
<style>
* { box-sizing:border-box; margin:0; padding:0; }
body { background:transparent; }
.material-symbols-rounded {
    font-family:'Material Symbols Rounded';
    font-weight:normal;
    font-style:normal;
    font-size:20px;
    line-height:1;
    display:inline-flex;
    align-items:center;
    justify-content:center;
    -webkit-font-feature-settings:'liga';
    font-feature-settings:'liga';
    -webkit-font-smoothing:antialiased;
    user-select:none;
}
.row {
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:10px 2px 2px;
}
.round-btn {
    width:42px; height:42px;
    border-radius:50%;
    background:#FFFFFF;
    border:1px solid #F4C6D5;
    display:flex; align-items:center; justify-content:center;
    cursor:pointer;
    box-shadow:0 2px 8px rgba(74,46,53,0.08);
    color:#4A2E35;
    transition:background 0.15s;
}
.round-btn:hover { background:#F8D7E3; }
</style>
</head>
<body>
<div class="row">
  <button class="round-btn" onclick="window.parent.postMessage('back','*')">
    <span class="material-symbols-rounded">arrow_back</span>
  </button>
  <button class="round-btn">
    <span class="material-symbols-rounded">open_in_full</span>
  </button>
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

    # hidden back button เพื่อรับ trigger จาก postMessage (ถ้าต้องการ)
    if st.session_state.get("_back_triggered"):
        st.session_state.clear()
        st.rerun()

    st.markdown('<div class="result-wrapper">', unsafe_allow_html=True)
    col_left, col_right = st.columns([1, 1])

    # ════════════════════════════════════════
    # LEFT — รูปใบเสร็จ
    # ════════════════════════════════════════
    with col_left:
        st.markdown('<div class="img-card-wrap">', unsafe_allow_html=True)

        if len(processed_img.shape) == 2:
            display_img = cv2.cvtColor(processed_img, cv2.COLOR_GRAY2RGB)
        else:
            display_img = cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)

        st.image(display_img, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ── ปุ่ม back + zoom เรียงแถวเดียวกันใต้รูป ──
        components.html(build_img_controls_html(), height=58, scrolling=False)

        # hidden st.button สำหรับ fallback back navigation
        st.markdown("""
        <style>
        div[data-testid="stButton"].hidden-back { display:none !important; }
        </style>
        """, unsafe_allow_html=True)
        st.markdown('<div class="hidden-back">', unsafe_allow_html=True)
        st.button("back", key="back_btn", on_click=reset_app)
        st.markdown('</div>', unsafe_allow_html=True)

    # ════════════════════════════════════════
    # RIGHT — detail card + action bar
    # ════════════════════════════════════════
    with col_right:
        if has_error:
            st.error(f"❌ {extracted_json['error']}")
        else:
            items_count = len(extracted_json.get("items", []) or [])
            card_height = 430 + max(0, items_count - 2) * 38

            # Detail card
            components.html(
                build_detail_card_html(extracted_json),
                height=card_height,
                scrolling=False,
            )

            # Action bar (3 ปุ่ม icon แถวเดียว)
            components.html(build_action_bar_html(), height=58, scrolling=False)

            # Export logic ผ่าน hidden st.button
            st.markdown("""
            <style>
            div[data-testid="stButton"].hidden-export { display:none !important; }
            </style>
            """, unsafe_allow_html=True)
            st.markdown('<div class="hidden-export">', unsafe_allow_html=True)
            if st.button("export", key="export_btn"):
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
                st.success("บันทึกข้อมูลเรียบร้อยแล้ว")
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