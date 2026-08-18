import io
import string
import time
from typing import Iterator
import streamlit as st
import pikepdf
from pypdf import PdfReader, PdfWriter

# -----------------------------------------------------------------------------
# Constants - Exact same as original pdf_tester.py
# -----------------------------------------------------------------------------
UPPERCASE_LETTERS = string.ascii_uppercase  # A-Z
YEAR_START = 1990
YEAR_END = 2007

NUM_PREFIXES = 26 ** 4        # 456,976
NUM_YEARS = YEAR_END - YEAR_START + 1  # 18
TOTAL_CANDIDATES = NUM_PREFIXES * NUM_YEARS  # 8,225,568
BATCH_SIZE = 2000  # UI refresh every N candidates


def generate_candidates() -> Iterator[str]:
    """Yields XXXXYYYY passwords: 4 uppercase letters + year 1990-2007."""
    years = [str(y) for y in range(YEAR_START, YEAR_END + 1)]
    for a in UPPERCASE_LETTERS:
        for b in UPPERCASE_LETTERS:
            for c in UPPERCASE_LETTERS:
                for d in UPPERCASE_LETTERS:
                    prefix = f"{a}{b}{c}{d}"
                    for year in years:
                        yield f"{prefix}{year}"


def validate_pdf(pdf_bytes: bytes) -> tuple[bool, str]:
    """Check PDF is valid and encrypted."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if not reader.is_encrypted:
            return False, "This PDF is not password-protected."
        return True, "OK"
    except Exception as exc:
        return False, f"Cannot read PDF: {exc}"


def try_password_pikepdf(pdf_bytes: bytes, password: str) -> bool:
    """Try a password using pikepdf's C++ qpdf engine."""
    try:
        with pikepdf.open(io.BytesIO(pdf_bytes), password=password):
            return True
    except pikepdf.PasswordError:
        return False
    except Exception:
        return False


def generate_unlocked_pdf(pdf_bytes: bytes, password: str) -> bytes | None:
    """Generate unlocked (no-password) PDF using pikepdf."""
    try:
        with pikepdf.open(io.BytesIO(pdf_bytes), password=password) as pdf:
            out = io.BytesIO()
            pdf.save(out)
            out.seek(0)
            return out.getvalue()
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Page config
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="PDF Password Recovery",
    page_icon="🔓",
    layout="centered",
)

# -----------------------------------------------------------------------------
# CSS - Clean Modern Dark UI
# -----------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

.stApp { max-width: 720px; margin: 0 auto; }

.hero {
    background: linear-gradient(135deg, rgba(99,102,241,0.12) 0%, rgba(168,85,247,0.08) 100%);
    border: 1px solid rgba(99,102,241,0.25);
    border-radius: 16px;
    padding: 1.5rem;
    text-align: center;
    margin-bottom: 1.5rem;
}

.hero h1 {
    font-size: 1.9rem;
    font-weight: 700;
    background: linear-gradient(135deg, #e0e7ff, #a5b4fc, #818cf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 0.4rem 0;
}

.hero p { color: #94a3b8; margin: 0; font-size: 0.9rem; }

.engine-badge {
    display: inline-block;
    background: rgba(16,185,129,0.15);
    border: 1px solid rgba(16,185,129,0.35);
    color: #34d399;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 999px;
    margin-bottom: 0.75rem;
    letter-spacing: 0.04em;
}

.info-box {
    background: rgba(30,41,59,0.6);
    border: 1px solid rgba(71,85,105,0.4);
    border-radius: 10px;
    padding: 0.85rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.88rem;
    color: #cbd5e1;
}
.info-box code {
    background: rgba(99,102,241,0.15);
    color: #a5b4fc;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.85rem;
}

.result-card {
    background: linear-gradient(135deg, rgba(16,185,129,0.15), rgba(5,150,105,0.08));
    border: 1px solid #10b981;
    border-radius: 14px;
    padding: 1.5rem;
    text-align: center;
    margin: 1rem 0;
}
.result-card h3 { color: #34d399; margin: 0 0 0.5rem 0; font-size: 1.1rem; }
.password-show {
    font-size: 1.8rem;
    font-weight: 700;
    font-family: 'Consolas', monospace;
    color: #10b981;
    background: rgba(0,0,0,0.3);
    padding: 0.4rem 1.5rem;
    border-radius: 8px;
    border: 1px dashed #10b981;
    display: inline-block;
    margin: 0.5rem 0;
    letter-spacing: 2px;
}
.result-meta { color: #64748b; font-size: 0.82rem; margin-top: 0.4rem; }

div.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    font-size: 1rem;
    padding: 0.6rem 1.2rem;
    width: 100%;
    transition: opacity 0.2s;
}
div.stButton > button:hover { opacity: 0.9; }

#MainMenu, header, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
st.markdown("""
<div class="hero">
    <span class="engine-badge">⚡ C++ qpdf Engine (pikepdf)</span>
    <h1>🔓 PDF Password Recovery</h1>
    <p>Upload a locked PDF. Password is recovered automatically using the fast C++ engine.<br/>
    Format: <strong>XXXX + Year (1990–2007)</strong> — 8,225,568 combinations</p>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Info box
# -----------------------------------------------------------------------------
st.markdown(f"""
<div class="info-box">
    🎯 <strong>Search Pattern:</strong> <code>AAAA1990</code> → <code>ZZZZ2007</code>
    &nbsp;&nbsp;|&nbsp;&nbsp;
    📊 <strong>Total:</strong> {NUM_PREFIXES:,} prefixes × {NUM_YEARS} years = <strong>{TOTAL_CANDIDATES:,} passwords</strong>
    &nbsp;&nbsp;|&nbsp;&nbsp;
    🚀 <strong>Engine:</strong> C++ qpdf via pikepdf
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Step 1: Upload
# -----------------------------------------------------------------------------
st.subheader("📁 Upload PDF")
uploaded = st.file_uploader(
    "Choose your password-protected PDF file",
    type=["pdf"],
    label_visibility="collapsed",
    help="File is processed in memory. Never stored.",
)

pdf_valid = False
pdf_bytes = None

if uploaded:
    pdf_bytes = uploaded.getvalue()
    ok, msg = validate_pdf(pdf_bytes)
    if ok:
        st.success(f"✅ **{uploaded.name}** — Encrypted PDF ready.")
        pdf_valid = True
    else:
        st.error(f"❌ {msg}")
else:
    st.caption("⬆️ Drag & drop or browse your `.pdf` file above.")

st.write("")

# -----------------------------------------------------------------------------
# Step 2: Start Search
# -----------------------------------------------------------------------------
st.subheader("🚀 Start Recovery")

start = st.button(
    "🔓 Start Password Search",
    type="primary",
    disabled=not pdf_valid,
)

if start and pdf_valid:
    progress_bar = st.progress(0.0)
    status = st.empty()

    col1, col2, col3, col4 = st.columns(4)
    m_tested  = col1.empty()
    m_current = col2.empty()
    m_speed   = col3.empty()
    m_elapsed = col4.empty()

    # Start search
    t_start = time.monotonic()
    tested = 0
    found = None
    last_ui = t_start
    total = TOTAL_CANDIDATES

    status.info("⚡ C++ Engine searching...")

    for candidate in generate_candidates():
        if try_password_pikepdf(pdf_bytes, candidate):
            found = candidate
            tested += 1
            break

        tested += 1

        if tested % BATCH_SIZE == 0:
            now = time.monotonic()
            elapsed = now - t_start
            rate = tested / elapsed if elapsed > 0 else 0.0
            pct = tested / total

            progress_bar.progress(min(1.0, pct))
            m_tested.metric("Tested", f"{tested:,}")
            m_current.metric("Current", candidate)
            m_speed.metric("Speed", f"{rate:,.0f}/s")
            m_elapsed.metric("Elapsed", f"{elapsed:.0f}s")

    total_elapsed = time.monotonic() - t_start
    status.empty()

    if found:
        progress_bar.progress(1.0)
        st.balloons()

        rate_final = tested / total_elapsed if total_elapsed > 0 else 0
        st.markdown(f"""
        <div class="result-card">
            <h3>🎉 Password Found!</h3>
            <div class="password-show">{found}</div>
            <div class="result-meta">
                {tested:,} candidates tested &nbsp;·&nbsp;
                {total_elapsed:.1f}s elapsed &nbsp;·&nbsp;
                {rate_final:,.0f} passwords/sec
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Download unlocked PDF
        unlocked = generate_unlocked_pdf(pdf_bytes, found)
        if unlocked:
            st.download_button(
                label="📥 Download Unlocked PDF (No Password)",
                data=unlocked,
                file_name=f"unlocked_{uploaded.name}",
                mime="application/pdf",
                type="primary",
            )
    else:
        progress_bar.progress(1.0)
        st.warning(
            f"❌ Password not found in {tested:,} candidates ({total_elapsed:.0f}s). "
            "The password may be outside the `AAAA1990–ZZZZ2007` range."
        )

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.markdown("""
<div style="text-align:center; color:#475569; font-size:0.78rem; margin-top:2.5rem;
border-top:1px solid rgba(255,255,255,0.06); padding-top:1rem;">
🔒 Files processed in-memory. Nothing is stored or transmitted.
</div>
""", unsafe_allow_html=True)
