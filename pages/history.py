"""
pages/history.py  — RecAipt Receipt History
ใช้ REST API ตรงแทน supabase-py เพื่อ compatibility กับ Python 3.14
"""
import json
import math
import requests as _req

import streamlit as st

st.set_page_config(
    page_title="RecAipt — ประวัติใบเสร็จ",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = """
<style>
:root {
    --bg: #f3f1ec; --panel: #fbfaf7; --panel-2: #f7f3ea;
    --ink: #24302f; --muted: #64706d; --line: #ddd8cc;
    --accent: #2f6f73; --accent-2: #285e62;
    --ok-bg: #e8f2e7; --ok-line: #9abe98; --ok-ink: #2c6330;
    --warn-bg: #fff3d8; --warn-line: #dfb65b; --warn-ink: #75520f;
    --bad-bg: #fae4e0; --bad-line: #d9958d; --bad-ink: #91382d;
}
header, footer, #MainMenu,
[data-testid="stToolbar"],
[data-testid="stDecoration"] { display: none !important; }
.stApp { background: var(--bg); color: var(--ink); }
.block-container { max-width: 100% !important; padding: 0 22px 18px !important; }
.hist-topbar {
    position: sticky; top: 0; z-index: 20;
    margin: 0 -22px 20px; padding: 16px 28px;
    background: #f9f7f1; border-bottom: 1px solid var(--line);
    display: flex; align-items: center; justify-content: space-between; gap: 16px;
}
.hist-brand { color: var(--ink); font-size: 1.28rem; font-weight: 720; }
.hist-sub { color: var(--muted); font-size: 0.94rem; margin-top: 2px; }
.badge {
    display: inline-flex; align-items: center;
    min-height: 28px; padding: 3px 10px;
    border-radius: 999px; font-size: 0.88rem; font-weight: 650; white-space: nowrap;
}
.badge-ok  { color: var(--ok-ink);  background: var(--ok-bg);  border: 1px solid var(--ok-line); }
.badge-warn{ color: var(--warn-ink);background: var(--warn-bg);border: 1px solid var(--warn-line);}
.badge-bad { color: var(--bad-ink); background: var(--bad-bg); border: 1px solid var(--bad-line);}
.section-band {
    margin-top: 12px; padding: 9px 12px;
    border-left: 4px solid var(--accent);
    background: #eff5f3; color: var(--ink);
    font-size: 1.02rem; font-weight: 720;
}
.hist-id   { color: var(--muted); font-size: 0.88rem; font-weight: 650; }
.hist-num  { color: var(--ink); font-size: 0.98rem; font-weight: 740; }
.hist-sub2 { color: var(--muted); font-size: 0.88rem; margin-top: 2px; }
.hist-total{ color: var(--accent); font-size: 1.08rem; font-weight: 760; text-align: right; padding-right: 12px; }
.hist-hdr {
    display: grid;
    grid-template-columns: 0.6fr 2.2fr 1.2fr 1.1fr 1.0fr 0.8fr 0.7fr;
    gap: 10px; padding: 6px 0;
    color: var(--muted); font-size: 0.86rem; font-weight: 650;
    border-bottom: 1px solid var(--line); margin-bottom: 6px;
}
div.stButton > button {
    min-height: 36px !important; border-radius: 8px !important;
    font-size: 0.92rem !important; font-weight: 680 !important;
    border: 1px solid #b9af9c !important;
    background: #fffdf8 !important; color: var(--ink) !important;
}
div.stButton > button:hover {
    border-color: var(--accent) !important; color: var(--accent-2) !important;
    background: #eef4f4 !important;
}
div.stButton > button[kind="primary"] {
    background: var(--accent) !important; color: #fff !important;
    border-color: var(--accent) !important;
}
div.stButton > button[kind="primary"]:hover { background: var(--accent-2) !important; }
.detail-pane {
    background: var(--panel); border: 1px solid var(--line);
    border-radius: 8px; padding: 20px 22px; margin-top: 12px;
}
.detail-grid {
    display: grid; grid-template-columns: repeat(3, 1fr);
    gap: 12px; margin-bottom: 16px;
}
.detail-field { padding: 10px 12px; border: 1px solid var(--line); border-radius: 8px; background: #fffdf8; }
.detail-label { color: var(--muted); font-size: 0.86rem; }
.detail-value { color: var(--ink); font-size: 1rem; font-weight: 680; margin-top: 3px; overflow-wrap: anywhere; }
.empty-state {
    text-align: center; padding: 48px 20px;
    color: var(--muted); font-size: 1.02rem; line-height: 1.7;
}
[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
.stTextInput input,
.stDateInput input,
.stSelectbox div[data-baseweb="select"] > div {
    min-height: 40px !important; font-size: 0.98rem !important;
    background: #fffefb !important;
    color: var(--ink) !important;
    border-color: #cfc8b8 !important;
    border-radius: 8px !important;
}
.stTextInput input::placeholder,
.stDateInput input::placeholder {
    color: var(--muted) !important;
    opacity: 1 !important;
}
[data-testid="stDataFrame"] {
    background: #fffdf8 !important;
    color: var(--ink) !important;
}
[data-testid="stDataFrame"] * {
    color: var(--ink) !important;
}
[data-testid="stAlert"] *,
[data-testid="stException"] * {
    color: var(--ink) !important;
}
@media (max-width: 900px) {
    .hist-hdr { grid-template-columns: 0.6fr 2.2fr 1.2fr 1.1fr 1.0fr 0.8fr 0.7fr; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def stretch_kwargs():
    return {"width": "stretch"}


# ── REST API helpers (ไม่ใช้ supabase-py) ────────────────────────────────────
def _get_creds():
    try:
        url = st.secrets.get("SUPABASE_URL", "").rstrip("/")
        key = st.secrets.get("SUPABASE_KEY", "")
        return url, key
    except Exception:
        return "", ""


def _headers(key):
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _rest_get(path, params=None):
    url, key = _get_creds()
    if not url or not key:
        return None, "ยังไม่ได้ตั้งค่า SUPABASE_URL / SUPABASE_KEY"
    try:
        r = _req.get(f"{url}/rest/v1/{path}", headers=_headers(key), params=params, timeout=10)
        if r.status_code == 200:
            return r.json(), None
        return None, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return None, str(e)


def _rest_delete(path, params=None):
    url, key = _get_creds()
    if not url or not key:
        raise RuntimeError("ยังไม่ได้ตั้งค่า Supabase")
    r = _req.delete(f"{url}/rest/v1/{path}", headers=_headers(key), params=params, timeout=10)
    if r.status_code not in (200, 204):
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")


def safe_float(value, default=0.0):
    try:
        if value in (None, ""):
            return default
        parsed = float(str(value).replace(",", "").strip())
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError):
        return default


def check_connection():
    data, err = _rest_get("receipts", {"select": "id", "limit": "1"})
    return err is None


def fetch_receipts(search_text="", date_from=None, date_to=None, status_filter="ทั้งหมด"):
    params = {
        "select": "id,receipt_type,document_number,document_date,grand_total,status,created_at,original_filename,seller_id",
        "order": "created_at.desc",
        "limit": "200",
    }
    if date_from:
        params["document_date"] = f"gte.{date_from}"
    if date_to:
        params["document_date"] = f"lte.{date_to}"
    if status_filter != "ทั้งหมด":
        params["status"] = f"eq.{status_filter}"

    rows, err = _rest_get("receipts", params)
    if err:
        st.error(f"ไม่สามารถดึงข้อมูลได้: {err}")
        return []
    rows = rows or []

    seller_ids = list({r["seller_id"] for r in rows if r.get("seller_id")})
    seller_map = {}
    if seller_ids:
        ids_str = ",".join(str(i) for i in seller_ids)
        companies, _ = _rest_get("companies", {"select": "id,name", "id": f"in.({ids_str})"})
        if companies:
            seller_map = {c["id"]: c["name"] for c in companies}

    for r in rows:
        r["seller_name"] = seller_map.get(r.get("seller_id"), "-")

    if search_text:
        q = search_text.lower()
        rows = [
            r for r in rows
            if q in str(r.get("document_number", "")).lower()
            or q in str(r.get("seller_name", "")).lower()
            or q in str(r.get("document_date", "")).lower()
        ]
    return rows


def fetch_receipt_detail(receipt_id):
    data, err = _rest_get("receipts", {"select": "*", "id": f"eq.{receipt_id}", "limit": "1"})
    if err or not data:
        st.error(f"ดึงรายละเอียดไม่ได้: {err}")
        return None, []
    receipt = data[0]

    if receipt.get("seller_id"):
        s_data, _ = _rest_get("companies", {
            "select": "name,tax_id,address,telephone,store_name",
            "id": f"eq.{receipt['seller_id']}",
            "limit": "1",
        })
        receipt["seller"] = s_data[0] if s_data else {}
    else:
        receipt["seller"] = {}

    if receipt.get("buyer_id"):
        b_data, _ = _rest_get("companies", {
            "select": "name,tax_id,address",
            "id": f"eq.{receipt['buyer_id']}",
            "limit": "1",
        })
        receipt["buyer"] = b_data[0] if b_data else {}
    else:
        receipt["buyer"] = {}

    items, _ = _rest_get("receipt_items", {
        "select": "*",
        "receipt_id": f"eq.{receipt_id}",
        "order": "id.asc",
    })
    return receipt, items or []


def delete_receipt(receipt_id):
    _rest_delete("receipt_items", {"receipt_id": f"eq.{receipt_id}"})
    _rest_delete("receipts", {"id": f"eq.{receipt_id}"})


# ── Topbar ────────────────────────────────────────────────────────────────────
supabase_ok = check_connection()
conn_badge = (
    '<span class="badge badge-ok">Supabase เชื่อมต่อแล้ว</span>'
    if supabase_ok
    else '<span class="badge badge-bad">ยังไม่ได้ตั้งค่า Supabase</span>'
)
st.markdown(
    f"""
    <div class="hist-topbar">
      <div>
        <div class="hist-brand">📚 ประวัติใบเสร็จ — RecAipt</div>
        <div class="hist-sub">รายการใบเสร็จทั้งหมดที่บันทึกลง Supabase แล้ว</div>
      </div>
      <div style="display:flex;gap:8px;align-items:center;">
        {conn_badge}
        <a href="/" target="_self" style="text-decoration:none;">
          <span class="badge badge-warn">← กลับหน้าสแกน</span>
        </a>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not supabase_ok:
    st.markdown(
        '<div class="empty-state">ยังไม่ได้ตั้งค่า SUPABASE_URL และ SUPABASE_KEY<br>'
        'เพิ่มใน <code>.streamlit/secrets.toml</code> ก่อนใช้งานหน้านี้</div>',
        unsafe_allow_html=True,
    )
    st.stop()


# ── Session state ─────────────────────────────────────────────────────────────
if "hist_detail_id" not in st.session_state:
    st.session_state["hist_detail_id"] = None
if "hist_confirm_delete" not in st.session_state:
    st.session_state["hist_confirm_delete"] = None


# ── Search / Filter bar ───────────────────────────────────────────────────────
st.markdown('<div class="section-band">ค้นหาและกรองใบเสร็จ</div>', unsafe_allow_html=True)
f1, f2, f3, f4, f5 = st.columns([2.5, 1.4, 1.4, 1.4, 0.8])
with f1:
    search_text = st.text_input("ค้นหา", placeholder="เลขเอกสาร / ชื่อร้าน / วันที่", label_visibility="collapsed")
with f2:
    date_from = st.date_input("ตั้งแต่วันที่", value=None, label_visibility="collapsed")
with f3:
    date_to = st.date_input("ถึงวันที่", value=None, label_visibility="collapsed")
with f4:
    status_filter = st.selectbox("สถานะ", ["ทั้งหมด", "verified", "draft"], label_visibility="collapsed")
with f5:
    do_refresh = st.button("🔄 โหลดใหม่", **stretch_kwargs())

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("กำลังโหลดข้อมูล..."):
    rows = fetch_receipts(
        search_text=search_text,
        date_from=date_from if date_from else None,
        date_to=date_to if date_to else None,
        status_filter=status_filter,
    )

# ── List view ─────────────────────────────────────────────────────────────────
st.markdown(f'<div class="section-band">รายการใบเสร็จ ({len(rows)} รายการ)</div>', unsafe_allow_html=True)

if not rows:
    st.markdown('<div class="empty-state">ไม่พบใบเสร็จที่ตรงกับเงื่อนไข</div>', unsafe_allow_html=True)
else:
    # Header row — ใช้ st.columns เดียวกับ data rows เพื่อให้ตรงกันทุก viewport
    _h = st.columns([0.6, 2.2, 1.2, 1.1, 1.0, 0.8, 0.7])
    for _col, _label in zip(_h, ["ID", "เลขที่เอกสาร / ร้านค้า", "วันที่", "ยอดสุทธิ", "สถานะ", "ดูรายละเอียด", "ลบ"]):
        _style = "text-align:right;padding-right:12px;" if _label == "ยอดสุทธิ" else ""
        _col.markdown(f'<div style="color:var(--muted);font-size:0.86rem;font-weight:650;padding:4px 0 6px;{_style}">{_label}</div>', unsafe_allow_html=True)
    st.markdown('<hr style="margin:0 0 6px;border:none;border-top:1px solid var(--line);">', unsafe_allow_html=True)

    for row in rows:
        rid = row.get("id")
        doc_num = row.get("document_number") or "-"
        seller_name = row.get("seller_name", "-")
        doc_date = row.get("document_date") or "-"
        grand_total = safe_float(row.get("grand_total"))
        status = row.get("status") or "draft"
        status_badge = (
            f'<span class="badge badge-ok">{status}</span>'
            if status == "verified"
            else f'<span class="badge badge-warn">{status}</span>'
        )

        col_id, col_info, col_date, col_total, col_status, col_view, col_del = st.columns(
            [0.6, 2.2, 1.2, 1.1, 1.0, 0.8, 0.7]
        )
        with col_id:
            st.markdown(f'<div class="hist-id">#{rid}</div>', unsafe_allow_html=True)
        with col_info:
            st.markdown(
                f'<div class="hist-num">{doc_num}</div><div class="hist-sub2">{seller_name}</div>',
                unsafe_allow_html=True,
            )
        with col_date:
            st.markdown(f'<div style="color:var(--muted);font-size:.92rem">{doc_date}</div>', unsafe_allow_html=True)
        with col_total:
            st.markdown(f'<div class="hist-total">{grand_total:,.2f}</div>', unsafe_allow_html=True)
        with col_status:
            st.markdown(status_badge, unsafe_allow_html=True)
        with col_view:
            if st.button("ดู", key=f"view_{rid}", **stretch_kwargs()):
                if st.session_state["hist_detail_id"] == rid:
                    st.session_state["hist_detail_id"] = None
                else:
                    st.session_state["hist_detail_id"] = rid
                    st.session_state["hist_confirm_delete"] = None
                st.rerun()
        with col_del:
            if st.session_state.get("hist_confirm_delete") == rid:
                if st.button("ยืนยัน", key=f"confirm_del_{rid}", type="primary", **stretch_kwargs()):
                    try:
                        delete_receipt(rid)
                        st.session_state["hist_confirm_delete"] = None
                        if st.session_state.get("hist_detail_id") == rid:
                            st.session_state["hist_detail_id"] = None
                        st.success(f"ลบใบเสร็จ #{rid} แล้ว")
                        st.rerun()
                    except Exception as e:
                        st.error(f"ลบไม่สำเร็จ: {e}")
            else:
                if st.button("ลบ", key=f"del_{rid}", **stretch_kwargs()):
                    st.session_state["hist_confirm_delete"] = rid
                    st.rerun()

        # ── Detail panel ──────────────────────────────────────────────────────
        if st.session_state.get("hist_detail_id") == rid:
            with st.spinner("กำลังโหลดรายละเอียด..."):
                receipt, items = fetch_receipt_detail(rid)

            if receipt:
                seller = receipt.get("seller") or {}
                buyer = receipt.get("buyer") or {}

                st.markdown('<div class="detail-pane">', unsafe_allow_html=True)
                st.markdown(f"**ใบเสร็จ #{rid} — {doc_num}**")
                st.markdown('<div class="detail-grid">', unsafe_allow_html=True)

                fields = [
                    ("ประเภทเอกสาร", receipt.get("receipt_type", "-")),
                    ("วันที่เอกสาร", receipt.get("document_date", "-")),
                    ("วิธีชำระเงิน", receipt.get("payment_method", "-") or "-"),
                    ("ชื่อผู้ขาย", seller.get("name", "-")),
                    ("เลขผู้เสียภาษีผู้ขาย", seller.get("tax_id", "-")),
                    ("โทรศัพท์ผู้ขาย", seller.get("telephone", "-") or "-"),
                    ("ชื่อผู้ซื้อ", buyer.get("name", "-") or "-"),
                    ("เลขผู้เสียภาษีผู้ซื้อ", buyer.get("tax_id", "-") or "-"),
                    ("ยอดก่อนภาษี", f"{safe_float(receipt.get('amount_before_tax')):,.2f}"),
                    ("VAT (%)", f"{safe_float(receipt.get('vat_rate'), 7.0):.1f}%"),
                    ("จำนวน VAT", f"{safe_float(receipt.get('vat_amount')):,.2f}"),
                    ("ยอดสุทธิ", f"{safe_float(receipt.get('grand_total')):,.2f}"),
                ]
                for label, value in fields:
                    st.markdown(
                        f'<div class="detail-field"><div class="detail-label">{label}</div>'
                        f'<div class="detail-value">{value}</div></div>',
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)

                if items:
                    st.markdown("**รายการสินค้า**")
                    st.dataframe(
                        [
                            {
                                "#": i + 1,
                                "รายการ": item.get("item_description", "-"),
                                "จำนวน": safe_float(item.get("quantity"), 1.0),
                                "ราคา/หน่วย": safe_float(item.get("unit_price")),
                                "รวม": safe_float(item.get("subtotal")),
                            }
                            for i, item in enumerate(items)
                        ],
                        **stretch_kwargs(),
                        hide_index=True,
                        column_config={
                            "จำนวน": st.column_config.NumberColumn(format="%.2f"),
                            "ราคา/หน่วย": st.column_config.NumberColumn(format="%.2f"),
                            "รวม": st.column_config.NumberColumn(format="%.2f"),
                        },
                    )

                with st.expander("JSON ต้นฉบับ (extracted_json)"):
                    st.json(receipt.get("extracted_json") or {})

                if st.button("ปิดรายละเอียด", key=f"close_{rid}"):
                    st.session_state["hist_detail_id"] = None
                    st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div style="height:2px;"></div>', unsafe_allow_html=True)
