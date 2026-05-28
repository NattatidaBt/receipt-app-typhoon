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
    max-width:100% !important;
    padding:1.5rem 3rem !important;
}

.header-bar {
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:14px 28px;
    margin-bottom:40px;
    background:#FFFFFF;
    border-radius:18px;
    box-shadow:0 4px 15px rgba(74,46,53,0.02);
}

.logo-text {
    color:#4A2E35;
    font-size:20px;
    font-weight:700;
    display:flex;
    align-items:center;
    gap:8px;
}

.lang-pill {
    background:#C97D98;
    color:white;
    padding:7px 16px;
    border-radius:10px;
    font-size:13px;
    font-weight:500;
}

.hero-title {
    text-align:center;
    color:#4A2E35;
    font-size:32px;
    font-weight:500;
    margin:35px 0 10px;
}

.hero-subtitle {
    text-align:center;
    color:#C29BA4;
    font-size:15px;
    margin-bottom:45px;
}

/* Upload Zone */

[data-testid="stFileUploader"] {
    max-width:780px !important;
    margin:0 auto !important;
    display:block !important;
}

[data-testid="stFileUploaderDropzone"] {
    background:#FFFFFF !important;
    border:2px dashed #F4C6D5 !important;
    border-radius:28px !important;
    min-height:220px !important;
    display:flex !important;
    flex-direction:column !important;
    align-items:center !important;
    justify-content:center !important;
    padding:40px 30px !important;
    box-shadow:0 12px 35px rgba(74,46,53,0.03) !important;
    cursor:pointer !important;
}

[data-testid="stFileUploaderDropzone"] svg {
    display:none !important;
}

[data-testid="stFileUploaderDropzoneInstructions"] > div > span,
[data-testid="stFileUploaderDropzoneInstructions"] > div > small {
    display:none !important;
}

[data-testid="stFileUploaderDropzoneInstructions"] {
    display:flex !important;
    flex-direction:column !important;
    align-items:center !important;
}

[data-testid="stFileUploaderDropzoneInstructions"]::before {
    content:"📄";
    font-size:44px;
    line-height:1;
    margin-bottom:14px;
    display:block;
}

[data-testid="stFileUploaderDropzoneInstructions"]::after {
    content:"Choose or paste a file here (image or PDF)";
    color:#A3858C;
    font-size:15px;
    display:block;
    margin-top:10px;
    text-align:center;
}

[data-testid="stFileUploader"] label {
    display:none !important;
}

[data-testid="stFileUploaderDropzoneInputButton"] {
    opacity:0 !important;
    position:absolute !important;
    width:100% !important;
    height:100% !important;
    top:0 !important;
    left:0 !important;
    cursor:pointer !important;
}

/* Result wrapper */

.result-wrapper {
    background:#FFFFFF;
    border-radius:32px;
    padding:35px;
    max-width:1450px;
    margin:0 auto !important;
    box-shadow:0 12px 40px rgba(74,46,53,0.04);
}

[data-testid="stHorizontalBlock"] {
    gap:30px !important;
    align-items:flex-start !important;
}

.img-card-wrap {
    background:#F5F5F5;
    border-radius:24px;
    overflow:hidden;
    border:1px solid #F8D7E3;
}

[data-testid="stHtml"] {
    padding:0 !important;
    margin:0 !important;
}

iframe {
    display:block !important;
    margin:0 auto !important;
    border-radius:24px !important;
}

[data-testid="stElementToolbar"] {
    display:none !important;
}

button[title="View fullscreen"] {
    display:none !important;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# HELPERS
# =========================================================
def reset_app():
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def safe_float(value, default=0.0):
    try:
        return float(str(value).replace(",", "").strip())
    except:
        return default


def safe_int(value, default=1):
    try:
        return int(float(str(value).replace(",", "").strip()))
    except:
        return default


# =========================================================
# FIXED JAVASCRIPT MESSAGE ENGINE
# =========================================================
st.markdown("""
<script>

if (!window.hasRecAiptListener) {

    window.hasRecAiptListener = true;

    window.addEventListener('message', function(e) {

        if (e.data && e.data.type === 'recalpt_action') {

            const url = new URL(window.parent.location.href);

            url.searchParams.set(
                "triggered_event",
                e.data.value
            );

            // update url without reload
            window.parent.history.pushState(
                {},
                '',
                url.toString()
            );

            // force streamlit rerun
            window.parent.dispatchEvent(
                new PopStateEvent('popstate')
            );
        }
    });
}

</script>
""", unsafe_allow_html=True)

HTML_POST_BRIDGE = """
<script>

function executeAction(actValue) {

    window.parent.postMessage(
        {
            type: 'recalpt_action',
            value: actValue
        },
        '*'
    );
}

</script>
"""

# =========================================================
# SVG ICONS
# =========================================================
SVG_BACK   = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>'
SVG_EDIT   = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>'
SVG_DELETE = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>'
SVG_COPY   = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>'
SVG_SHARE  = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>'
SVG_DL     = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>'
SVG_ZOOM   = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>'

# =========================================================
# SIMPLE HTML BUILDERS
# =========================================================
def build_action_bar_html():

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">

    <style>

    body {{
        margin:0;
        padding:0;
        background:transparent;
        font-family:sans-serif;
    }}

    .bar {{
        display:flex;
        gap:10px;
        width:100%;
    }}

    .btn {{
        flex:1;
        height:44px;
        border-radius:12px;
        border:none;
        cursor:pointer;
        background:#FFF0F5;
        color:#A35271;
        font-weight:600;
    }}

    .btn.primary {{
        background:#C97D98;
        color:white;
    }}

    </style>

    {HTML_POST_BRIDGE}

    </head>

    <body>

    <div class="bar">

        <button class="btn"
            onclick="executeAction('copy')">
            {SVG_COPY} Copy
        </button>

        <button class="btn"
            onclick="executeAction('share')">
            {SVG_SHARE} Share
        </button>

        <button class="btn primary"
            onclick="executeAction('export')">
            {SVG_DL} Export
        </button>

    </div>

    </body>
    </html>
    """


# =========================================================
# PAGE 1
# =========================================================
if (
    "processed_img" not in st.session_state
    or st.session_state.get("file_uploaded") is None
):

    st.markdown(
        "<div class='hero-title'>Receipt scanning and data collection tools</div>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<div class='hero-subtitle'>Upload an image or PDF of your receipt to store it using OCR</div>",
        unsafe_allow_html=True
    )

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

            raw_text = run_typhoon_ocr(
                st.session_state["processed_img"]
            )

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
# PAGE 2
# =========================================================
else:

    processed_img  = st.session_state["processed_img"]
    extracted_json = st.session_state["extracted_json"]

    action = st.query_params.get("triggered_event", "")

    # =====================================================
    # HANDLE EVENTS
    # =====================================================

    if action == "back":

        if "triggered_event" in st.query_params:
            del st.query_params["triggered_event"]

        reset_app()
        st.rerun()

    elif action == "edit":

        if "triggered_event" in st.query_params:
            del st.query_params["triggered_event"]

        st.toast("✏️ Edit clicked")

    elif action == "delete":

        if "triggered_event" in st.query_params:
            del st.query_params["triggered_event"]

        st.toast("🗑️ Delete clicked")

    elif action == "copy":

        if "triggered_event" in st.query_params:
            del st.query_params["triggered_event"]

        st.toast("📋 Copy clicked")

    elif action == "share":

        if "triggered_event" in st.query_params:
            del st.query_params["triggered_event"]

        st.toast("🔗 Share clicked")

    elif action == "export":

        if "triggered_event" in st.query_params:
            del st.query_params["triggered_event"]

        st.success("✅ Export completed")

        st.json(extracted_json)

    # =====================================================
    # UI
    # =====================================================
    st.markdown(
        '<div class="result-wrapper">',
        unsafe_allow_html=True
    )

    col_left, col_right = st.columns([1, 1])

    # LEFT
    with col_left:

        st.markdown(
            '<div class="img-card-wrap">',
            unsafe_allow_html=True
        )

        display_img = (
            cv2.cvtColor(processed_img, cv2.COLOR_GRAY2RGB)
            if len(processed_img.shape) == 2
            else cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB)
        )

        st.image(
            display_img,
            use_container_width=True
        )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )

    # RIGHT
    with col_right:

        st.subheader("Receipt Information")

        st.json(extracted_json)

        components.html(
            build_action_bar_html(),
            height=60,
            scrolling=False
        )

    st.markdown(
        '</div>',
        unsafe_allow_html=True
    )