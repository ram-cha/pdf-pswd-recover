import io
import itertools
import string
import time
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
# 2. Ultra-Clean Modern UI Styling
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
        padding: 1.5rem 1rem;
        background: linear-gradient(180deg, rgba(99, 102, 241, 0.15) 0%, rgba(15, 23, 42, 0) 100%);
        border-radius: 18px;
        border: 1px solid rgba(99, 102, 241, 0.3);
        margin-bottom: 1.5rem;
    }

    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 50%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }

    .main-sub {
        color: #94a3b8;
        font-size: 1rem;
    }

    .info-card {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem 0;
        text-align: center;
        color: #cbd5e1;
        font-size: 0.95rem;
    }

    .success-box {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.18) 0%, rgba(5, 150, 105, 0.08) 100%);
        border: 1px solid #10b981;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        text-align: center;
        box-shadow: 0 0 35px rgba(16, 185, 129, 0.2);
    }

    .pwd-pill {
        display: inline-block;
        font-size: 2rem;
        font-weight: 800;
        color: #10b981;
        background: #0b0f19;
        padding: 0.5rem 2rem;
        border-radius: 12px;
        font-family: 'Consolas', 'Courier New', monospace;
        letter-spacing: 3px;
        border: 2px dashed #10b981;
        margin: 0.75rem 0;
    }

    div.stButton > button {
        border-radius: 12px;
        font-weight: 700;
        font-size: 1.1rem;
        padding: 0.75rem 1.5rem;
        transition: all 0.2s ease;
    }

    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4);
    }

    #MainMenu, header, footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 3. Core Logic & Password Generator (Original Pattern: 4 Letters + Year)
# -----------------------------------------------------------------------------

YEAR_START = 1980
YEAR_END = 2015
NUM_PREFIXES = 26 ** 4  # 456,976
NUM_YEARS = YEAR_END - YEAR_START + 1  # 36
TOTAL_CANDIDATES = NUM_PREFIXES * NUM_YEARS  # 16,451,136


def generate_all_candidates():
    """Lazily yields all 4 uppercase letters + year (AAAA1980 to ZZZZ2015)."""
    years = [str(y) for y in range(YEAR_START, YEAR_END + 1)]
    letters = string.ascii_uppercase
    for a in letters:
        for b in letters:
            for c in letters:
                for d in letters:
                    prefix = f"{a}{b}{c}{d}"
                    for y in years:
                        yield f"{prefix}{y}"


def validate_pdf_stream(pdf_bytes: bytes) -> tuple[bool, str]:
    """Safely checks if the PDF is readable and password protected."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if not reader.is_encrypted:
            return False, "This PDF is not password-protected (No password required)."
        return True, "Valid encrypted PDF ready for search."
    except Exception as exc:
        return False, f"Could not read PDF: {exc}"


def generate_unlocked_pdf(pdf_bytes: bytes, password: str) -> bytes | None:
    """Decrypts and creates a clean unlocked PDF in memory."""
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


def create_demo_pdf(password: str = "AAAA1995") -> bytes:
    """Generates a sample encrypted PDF for testing."""
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=200)
    writer.encrypt(password)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.getvalue()


# -----------------------------------------------------------------------------
# 4. Header & Upload (Dead Simple 1-Click UI)
# -----------------------------------------------------------------------------

st.markdown(
    """
    <div class="main-header">
        <div class="main-title">🔓 PDF Password Unlocker</div>
        <div class="main-sub">Upload your locked PDF and recover the password automatically in 1-click.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# PDF Source selection
source_choice = st.radio(
    "Source:",
    ["📁 Upload My PDF File", "🧪 Test with Demo PDF (Password: AAAA1995)"],
    horizontal=True,
    label_visibility="collapsed",
)

pdf_bytes = None
file_name = "document.pdf"

if source_choice == "📁 Upload My PDF File":
    up_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        help="Upload the PDF you want to unlock.",
        label_visibility="collapsed",
    )
    if up_file is not None:
        pdf_bytes = up_file.getvalue()
        file_name = up_file.name
else:
    pdf_bytes = create_demo_pdf("AAAA1995")
    file_name = "demo_sample.pdf"
    st.info("🧪 **Demo PDF Loaded**: Password is `AAAA1995`. Click Start below to see it find it in real-time!")

# PDF Validation
pdf_ready = False
if pdf_bytes is not None:
    is_valid, msg = validate_pdf_stream(pdf_bytes)
    if is_valid:
        st.success(f"✅ **{file_name}** - Password-protected PDF detected & ready.")
        pdf_ready = True
    else:
        st.error(f"❌ {msg}")
else:
    st.caption("👆 Upload your `.pdf` file above to start.")

st.markdown(
    f"""
    <div class="info-card">
        🎯 <b>Automatic Pattern:</b> 4-Letter Name/Initials + Year (<code>AAAA1980</code> → <code>ZZZZ2015</code>)<br/>
        ⚡ Total combinations: <b>{TOTAL_CANDIDATES:,}</b>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 5. One-Click Start Execution
# -----------------------------------------------------------------------------

start_btn = st.button(
    "🚀 Start Password Search",
    type="primary",
    use_container_width=True,
    disabled=not pdf_ready,
)

if start_btn and pdf_ready:
    progress_bar = st.progress(0.0)
    status_placeholder = st.empty()
    
    # 4 Real-time Metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        m_tested = st.empty()
    with c2:
        m_current = st.empty()
    with c3:
        m_speed = st.empty()
    with c4:
        m_elapsed = st.empty()

    reader = PdfReader(io.BytesIO(pdf_bytes))
    start_time = time.monotonic()
    tested = 0
    found_password = None
    last_ui_update = start_time
    
    status_placeholder.info("🔄 Searching for matching password...")

    for candidate in generate_all_candidates():
        try:
            match = reader.decrypt(candidate)
        except Exception:
            match = 0

        tested += 1

        if match:
            found_password = candidate
            break

        now = time.monotonic()
        if (now - last_ui_update) >= 0.25 or (tested % 400 == 0):
            elapsed = now - start_time
            rate = tested / elapsed if elapsed > 0 else 0.0
            pct = min(1.0, tested / TOTAL_CANDIDATES)

            progress_bar.progress(pct)
            m_tested.metric("Tested", f"{tested:,}")
            m_current.metric("Current", candidate)
            m_speed.metric("Speed", f"{rate:,.0f} /s")
            m_elapsed.metric("Elapsed", f"{elapsed:.1f}s")
            last_ui_update = now

    total_elapsed = time.monotonic() - start_time
    progress_bar.progress(1.0 if found_password else min(1.0, tested / TOTAL_CANDIDATES))
    status_placeholder.empty()

    if found_password:
        st.balloons()
        st.markdown(
            f"""
            <div class="success-box">
                <h2 style="color: #10b981; margin: 0 0 0.5rem 0;">🎉 Password Found!</h2>
                <div style="font-size: 1.1rem; color: #cbd5e1;">The password for <b>{file_name}</b> is:</div>
                <div class="pwd-pill">{found_password}</div>
                <div style="color: #94a3b8; font-size: 0.9rem;">
                    Tested <b>{tested:,}</b> passwords in <b>{total_elapsed:.2f} seconds</b> ({tested/total_elapsed if total_elapsed>0 else 0:,.0f} passwords/sec).
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 1-Click Unlocked PDF Download
        unlocked_pdf = generate_unlocked_pdf(pdf_bytes, found_password)
        if unlocked_pdf:
            st.download_button(
                label="📥 Download Unlocked (No Password) PDF",
                data=unlocked_pdf,
                file_name=f"unlocked_{file_name}",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )
            st.success("✨ This PDF is now permanently unlocked and won't ask for a password.")
    else:
        st.error(
            f"❌ Password not found in the 4-letter + year pattern after testing {tested:,} candidates ({total_elapsed:.1f}s)."
        )

# -----------------------------------------------------------------------------
# 6. Footer
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div style="text-align: center; margin-top: 3rem; color: #64748b; font-size: 0.8rem; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 1rem;">
        🔒 <b>100% In-Memory & Client-Side Privacy</b>: Your files and passwords are never saved or sent to external servers.
    </div>
    """,
    unsafe_allow_html=True,
)
