import io
import itertools
import string
import time
from typing import Generator, Iterable, Union
import streamlit as st
from pypdf import PdfReader, PdfWriter

# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="PDF Password Unlocker",
    page_icon="🔓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# 2. Modern Mobile-Friendly CSS
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .main-header {
        text-align: center;
        padding: 1.2rem 1rem;
        background: linear-gradient(180deg, rgba(99, 102, 241, 0.12) 0%, rgba(15, 23, 42, 0) 100%);
        border-radius: 16px;
        border: 1px solid rgba(99, 102, 241, 0.25);
        margin-bottom: 1.5rem;
    }

    .main-title {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 50%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }

    .main-sub {
        color: #94a3b8;
        font-size: 0.95rem;
    }

    .card-box {
        background: #131b2e;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    .success-box {
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid #10b981;
        border-radius: 14px;
        padding: 1.25rem;
        margin: 1.25rem 0;
        text-align: center;
    }

    .pwd-pill {
        display: inline-block;
        font-size: 1.5rem;
        font-weight: 700;
        color: #10b981;
        background: #0b0f19;
        padding: 0.4rem 1.2rem;
        border-radius: 8px;
        font-family: monospace;
        letter-spacing: 1.5px;
        border: 1px dashed #10b981;
        margin: 0.5rem 0;
    }

    div.stButton > button {
        border-radius: 10px;
        font-weight: 600;
        padding: 0.5rem 1rem;
    }

    #MainMenu, header, footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 3. Core Logic Helpers
# -----------------------------------------------------------------------------

def validate_pdf_stream(pdf_bytes: bytes) -> tuple[bool, str, int]:
    """Validates if PDF is readable and encrypted."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        num_pages = len(reader.pages)
        if not reader.is_encrypted:
            return False, "This PDF is already unprotected (No password required).", num_pages
        return True, "Valid password-protected PDF.", num_pages
    except Exception as exc:
        return False, f"Could not read PDF: {exc}", 0


def generate_unlocked_pdf(pdf_bytes: bytes, password: str) -> bytes | None:
    """Decrypts and creates a clean unprotected PDF in memory."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        reader.decrypt(password)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        out_buf = io.BytesIO()
        writer.write(out_buf)
        out_buf.seek(0)
        return out_buf.getvalue()
    except Exception:
        return None


def create_demo_pdf(password: str = "RAMK1998") -> bytes:
    """Generates an in-memory sample encrypted PDF for testing."""
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=200)
    writer.encrypt(password)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.getvalue()


# -----------------------------------------------------------------------------
# 4. Header
# -----------------------------------------------------------------------------

st.markdown(
    """
    <div class="main-header">
        <div class="main-title">🔓 PDF Password Unlocker</div>
        <div class="main-sub">Fast, secure in-browser recovery for salary slips, bank statements & personal PDFs</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 5. Step 1: Upload File
# -----------------------------------------------------------------------------

st.subheader("1️⃣ Upload PDF File")

col_src1, col_src2 = st.columns(2)
with col_src1:
    source_choice = st.radio(
        "Choose Mode:",
        ["📁 My PDF Document", "🧪 Instant Test Demo (Sample PDF)"],
        label_visibility="collapsed",
    )

pdf_bytes = None
file_name = "document.pdf"

if source_choice == "📁 My PDF Document":
    up_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        label_visibility="collapsed",
        help="Secure: File stays strictly inside your session memory.",
    )
    if up_file is not None:
        pdf_bytes = up_file.getvalue()
        file_name = up_file.name
else:
    pdf_bytes = create_demo_pdf("RAMK1998")
    file_name = "sample_test.pdf"
    st.info("💡 **Demo PDF Active**: Password is set to `RAMK1998` (Initials `RAMK` + Year `1998`).")

# Validation check
pdf_valid = False
if pdf_bytes is not None:
    is_valid, msg, pages = validate_pdf_stream(pdf_bytes)
    if is_valid:
        st.success(f"✅ **{file_name}** ({pages} page{'s' if pages>1 else ''}) - Locked & Ready to Search.")
        pdf_valid = True
    else:
        st.error(f"❌ {msg}")
else:
    st.caption("Upload a `.pdf` file above to begin.")

st.write("")

# -----------------------------------------------------------------------------
# 6. Step 2: Recovery Pattern
# -----------------------------------------------------------------------------

st.subheader("2️⃣ Choose Search Pattern")

pattern_mode = st.radio(
    "Pattern Type",
    [
        "⚡ Smart Pattern (Name / Initials + Birth Year)",
        "🔢 Numeric PIN (4 to 8 Digits)",
        "🔤 Full Pattern (AAAA to ZZZZ + Years)",
        "📝 Custom Passwords List",
    ],
    index=0,
)

candidates: Union[list[str], Generator[str, None, None]] = []
total_count = 0

if pattern_mode == "⚡ Smart Pattern (Name / Initials + Birth Year)":
    st.caption("Common format for Payslips, Bank Statements & PAN (e.g. `RAMK1995`, `AKSHAY2000`)")
    
    col_p, col_y = st.columns([1.2, 1.8])
    with col_p:
        name_prefix = st.text_input(
            "Known Name / Initials",
            value="RAMK" if source_choice != "📁 My PDF Document" else "",
            placeholder="e.g. RAMK, RA, AKSHAY",
        ).strip()
    with col_y:
        col_y1, col_y2 = st.columns(2)
        with col_y1:
            y_start = st.number_input("Start Year", min_value=1940, max_value=2030, value=1980)
        with col_y2:
            y_end = st.number_input("End Year", min_value=1940, max_value=2030, value=2015)
            
    if y_start > y_end:
        st.error("Start year must be <= End year")
    else:
        years_list = [str(y) for y in range(int(y_start), int(y_end) + 1)]
        if name_prefix:
            variants = [name_prefix.upper(), name_prefix.lower(), name_prefix.capitalize()]
            variants = list(dict.fromkeys(variants))
            candidates = [f"{v}{y}" for v in variants for y in years_list]
        else:
            candidates = years_list
        total_count = len(candidates)
        st.caption(f"Candidates to test: **{total_count:,}** (Instant: < 1 second)")

elif pattern_mode == "🔢 Numeric PIN (4 to 8 Digits)":
    st.caption("Common format for Aadhaar, Bank PIN, Credit Cards (e.g. `0000` to `9999`)")
    pin_digits = st.slider("PIN Length", min_value=4, max_value=8, value=4)
    total_count = 10 ** pin_digits
    st.caption(f"Total PIN combinations: **{total_count:,}**")

    def pin_generator(length: int):
        fmt = f"{{:0{length}d}}"
        for i in range(10 ** length):
            yield fmt.format(i)

    candidates = pin_generator(pin_digits)

elif pattern_mode == "🔤 Full Pattern (AAAA to ZZZZ + Years)":
    st.caption("Brute forces all 4 uppercase letters combinations (A-Z) + Year range.")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fy1 = st.number_input("From Year", min_value=1960, max_value=2030, value=1990)
    with col_f2:
        fy2 = st.number_input("To Year", min_value=1960, max_value=2030, value=2005)
        
    num_years = max(1, int(fy2 - fy1 + 1))
    total_count = (26 ** 4) * num_years
    st.caption(f"Total candidates: **{total_count:,}** (456,976 prefixes × {num_years} years)")

    def full_generator(start_y: int, end_y: int):
        yrs = [str(y) for y in range(start_y, end_y + 1)]
        for a, b, c, d in itertools.product(string.ascii_uppercase, repeat=4):
            pref = f"{a}{b}{c}{d}"
            for yr in yrs:
                yield f"{pref}{yr}"

    candidates = full_generator(int(fy1), int(fy2))

else:
    st.caption("Upload a `.txt` wordlist or paste passwords line-by-line.")
    uploaded_txt = st.file_uploader("Upload Wordlist (.txt)", type=["txt"])
    text_input = st.text_area("Or enter passwords (one per line):", height=90)
    words = []
    if uploaded_txt:
        words.extend(uploaded_txt.read().decode("utf-8", errors="ignore").splitlines())
    if text_input.strip():
        words.extend(text_input.splitlines())
    candidates = list(dict.fromkeys([w.strip() for w in words if w.strip()]))
    total_count = len(candidates)
    st.caption(f"Loaded passwords: **{total_count:,}**")

st.write("")

# -----------------------------------------------------------------------------
# 7. Step 3: Run Recovery
# -----------------------------------------------------------------------------

st.subheader("3️⃣ Run Recovery")

start_action = st.button(
    "🚀 Start Password Search",
    type="primary",
    use_container_width=True,
    disabled=not pdf_valid,
)

if start_action and pdf_valid:
    if total_count == 0:
        st.warning("⚠️ No passwords to test. Please check Step 2.")
    else:
        p_bar = st.progress(0.0)
        status_box = st.empty()
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            val_tested = st.empty()
        with c2:
            val_current = st.empty()
        with c3:
            val_speed = st.empty()
        with c4:
            val_time = st.empty()

        reader = PdfReader(io.BytesIO(pdf_bytes))
        t_start = time.monotonic()
        tested_num = 0
        found_pwd = None
        last_refresh = t_start

        status_box.info("🔄 Searching for correct password...")

        for cand in candidates:
            try:
                matched = reader.decrypt(cand)
            except Exception:
                matched = 0

            tested_num += 1

            if matched:
                found_pwd = cand
                break

            t_now = time.monotonic()
            if (t_now - last_refresh) >= 0.25 or (tested_num % 300 == 0):
                elapsed_s = t_now - t_start
                rate = tested_num / elapsed_s if elapsed_s > 0 else 0.0
                progress_fraction = min(1.0, tested_num / total_count) if total_count > 0 else 0.0

                p_bar.progress(progress_fraction)
                val_tested.metric("Tested", f"{tested_num:,}")
                val_current.metric("Current", cand)
                val_speed.metric("Speed", f"{rate:,.0f} /s")
                val_time.metric("Elapsed", f"{elapsed_s:.1f}s")
                last_refresh = t_now

        total_elapsed = time.monotonic() - t_start
        p_bar.progress(1.0 if found_pwd else min(1.0, tested_num / total_count if total_count > 0 else 1.0))
        status_box.empty()

        if found_pwd:
            st.balloons()
            st.markdown(
                f"""
                <div class="success-box">
                    <h3 style="color: #10b981; margin: 0 0 0.4rem 0;">🎉 Password Found!</h3>
                    <div>Password for <b>{file_name}</b>:</div>
                    <div class="pwd-pill">{found_pwd}</div>
                    <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.3rem;">
                        Tested <b>{tested_num:,}</b> candidates in <b>{total_elapsed:.2f}s</b> ({tested_num/total_elapsed if total_elapsed>0 else 0:,.0f} passwords/sec).
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Unlocked PDF direct download
            unlocked_data = generate_unlocked_pdf(pdf_bytes, found_pwd)
            if unlocked_data:
                st.download_button(
                    label="📥 Download Unlocked (No Password) PDF",
                    data=unlocked_data,
                    file_name=f"unlocked_{file_name}",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                )
        else:
            st.error(
                f"❌ Password not found among **{tested_num:,}** tested candidates ({total_elapsed:.1f}s).\n\n"
                "Try adjusting the name initials or expanding the birth year range in Step 2."
            )

# -----------------------------------------------------------------------------
# 8. Footer
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div style="text-align: center; margin-top: 2.5rem; color: #64748b; font-size: 0.8rem; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 1rem;">
        🔒 <b>100% Client-Side Privacy</b>: Files are processed strictly in temporary session memory and never saved.
    </div>
    """,
    unsafe_allow_html=True,
)
