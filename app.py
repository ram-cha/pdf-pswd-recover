import io
import string
import time
import zipfile
from typing import Iterator
import streamlit as st
import pikepdf
from pypdf import PdfReader, PdfWriter

# -----------------------------------------------------------------------------
# Constants - Same as original
# -----------------------------------------------------------------------------
UPPERCASE_LETTERS = string.ascii_uppercase
YEAR_START = 1990
YEAR_END = 2007

NUM_PREFIXES = 26 ** 4
NUM_YEARS = YEAR_END - YEAR_START + 1
TOTAL_CANDIDATES = NUM_PREFIXES * NUM_YEARS  # 8,225,568
BATCH_SIZE = 1500


def generate_candidates() -> Iterator[str]:
    """Yields XXXXYYYY: 4 uppercase letters + year 1990-2007."""
    years = [str(y) for y in range(YEAR_START, YEAR_END + 1)]
    for a in UPPERCASE_LETTERS:
        for b in UPPERCASE_LETTERS:
            for c in UPPERCASE_LETTERS:
                for d in UPPERCASE_LETTERS:
                    prefix = f"{a}{b}{c}{d}"
                    for year in years:
                        yield f"{prefix}{year}"


def is_encrypted(pdf_bytes: bytes) -> bool:
    """Returns True if PDF is password-protected."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return reader.is_encrypted
    except Exception:
        return False


def try_password(pdf_bytes: bytes, password: str) -> bool:
    """Test a password against a PDF using C++ qpdf engine."""
    try:
        with pikepdf.open(io.BytesIO(pdf_bytes), password=password):
            return True
    except pikepdf.PasswordError:
        return False
    except Exception:
        return False


def unlock_pdf(pdf_bytes: bytes, password: str) -> bytes | None:
    """Return decrypted PDF bytes using pikepdf."""
    try:
        with pikepdf.open(io.BytesIO(pdf_bytes), password=password) as pdf:
            out = io.BytesIO()
            pdf.save(out)
            out.seek(0)
            return out.getvalue()
    except Exception:
        return None


def make_zip(files: list[tuple[str, bytes]]) -> bytes:
    """Pack multiple (filename, bytes) pairs into a ZIP."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files:
            zf.writestr(name, data)
    buf.seek(0)
    return buf.getvalue()


# -----------------------------------------------------------------------------
# Page Setup
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="PDF Password Recovery",
    page_icon="🔓",
    layout="centered",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif;
}

.stApp { max-width: 760px; margin: 0 auto; }

.hero {
    background: linear-gradient(135deg, rgba(99,102,241,0.12), rgba(168,85,247,0.08));
    border: 1px solid rgba(99,102,241,0.28);
    border-radius: 16px;
    padding: 1.4rem 1.5rem;
    text-align: center;
    margin-bottom: 1.5rem;
}
.hero h1 {
    font-size: 1.85rem; font-weight: 700;
    background: linear-gradient(135deg, #e0e7ff, #a5b4fc, #818cf8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0 0 0.3rem 0;
}
.hero p { color: #94a3b8; margin: 0; font-size: 0.88rem; }

.badge {
    display: inline-block;
    background: rgba(16,185,129,0.14);
    border: 1px solid rgba(16,185,129,0.32);
    color: #34d399; font-size: 0.72rem; font-weight: 600;
    padding: 2px 10px; border-radius: 999px; margin-bottom: 0.6rem;
    letter-spacing: 0.04em;
}

/* PDF card */
.pdf-card {
    background: rgba(30,41,59,0.55);
    border: 1px solid rgba(71,85,105,0.4);
    border-radius: 12px;
    padding: 0.85rem 1.1rem;
    margin-bottom: 0.75rem;
}
.pdf-name {
    font-weight: 600; font-size: 0.92rem; color: #e2e8f0;
    margin-bottom: 0.3rem; word-break: break-all;
}
.pdf-status-wait  { color: #94a3b8; font-size: 0.82rem; }
.pdf-status-found { color: #10b981; font-size: 0.88rem; font-weight: 600; }
.pdf-status-fail  { color: #f87171; font-size: 0.82rem; }

.pwd-tag {
    display: inline-block;
    background: rgba(16,185,129,0.12);
    border: 1px solid #10b981;
    color: #34d399;
    font-family: 'Consolas', monospace;
    font-size: 1.1rem; font-weight: 700;
    padding: 2px 14px; border-radius: 6px;
    letter-spacing: 1.5px; margin-left: 6px;
}

.stat-bar {
    background: rgba(15,23,42,0.6);
    border: 1px solid rgba(71,85,105,0.35);
    border-radius: 10px;
    padding: 0.7rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.82rem; color: #94a3b8;
}

div.stButton > button {
    border-radius: 10px; font-weight: 600; font-size: 0.95rem;
    padding: 0.55rem 1.1rem; width: 100%;
}

#MainMenu, header, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Header
# -----------------------------------------------------------------------------
st.markdown("""
<div class="hero">
    <span class="badge">⚡ C++ qpdf Engine (pikepdf)</span>
    <h1>🔓 PDF Password Recovery</h1>
    <p>Upload one or more locked PDFs. Password found automatically shown below each file.<br>
    Pattern: <strong>AAAA1990 → ZZZZ2007</strong> &nbsp;·&nbsp; 8,225,568 combinations</p>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Upload
# -----------------------------------------------------------------------------
st.subheader("📁 Upload PDF Files")
uploaded_files = st.file_uploader(
    "Choose one or multiple password-protected PDFs",
    type=["pdf"],
    accept_multiple_files=True,
    label_visibility="collapsed",
    help="Files are processed in-memory. Nothing is stored.",
)

# Validate all uploaded files
valid_files = []  # list of (name, bytes)
if uploaded_files:
    for f in uploaded_files:
        data = f.getvalue()
        if is_encrypted(data):
            valid_files.append((f.name, data))
        else:
            st.warning(f"⚠️ **{f.name}** is not password-protected — skipped.")

    if valid_files:
        st.success(f"✅ {len(valid_files)} encrypted PDF(s) ready to unlock.")
    else:
        st.info("No encrypted PDFs found in uploaded files.")
else:
    st.caption("⬆️ Drag & drop or click to browse. Multiple files supported.")

st.write("")

# -----------------------------------------------------------------------------
# Start Search
# -----------------------------------------------------------------------------
start = st.button(
    "🔓 Start Password Search for All PDFs",
    type="primary",
    disabled=len(valid_files) == 0,
)

if start and valid_files:
    n = len(valid_files)

    # Track results per file: None = searching, str = found, False = not found
    results: dict[str, str | bool | None] = {name: None for name, _ in valid_files}
    unlocked_pdfs: dict[str, bytes] = {}

    # --- UI placeholders for each PDF card ---
    card_placeholders = {}
    for name, _ in valid_files:
        card_placeholders[name] = st.empty()

    def render_cards():
        for fname, _ in valid_files:
            r = results[fname]
            if r is None:
                status_html = '<span class="pdf-status-wait">🔄 Searching...</span>'
            elif r is False:
                status_html = '<span class="pdf-status-fail">❌ Password not found in range.</span>'
            else:
                status_html = f'<span class="pdf-status-found">✅ Password Found: <span class="pwd-tag">{r}</span></span>'
            card_placeholders[fname].markdown(
                f'<div class="pdf-card"><div class="pdf-name">📄 {fname}</div>{status_html}</div>',
                unsafe_allow_html=True,
            )

    render_cards()

    # --- Global progress / stats ---
    prog_bar = st.progress(0.0)
    stat_ph = st.empty()

    # --- Search ---
    t_start = time.monotonic()
    tested = 0
    remaining = list(valid_files)  # files still being searched

    for candidate in generate_candidates():
        if not remaining:
            break

        newly_found = []
        for fname, pdf_data in remaining:
            if try_password(pdf_data, candidate):
                results[fname] = candidate
                unlocked = unlock_pdf(pdf_data, candidate)
                if unlocked:
                    unlocked_pdfs[fname] = unlocked
                newly_found.append(fname)

        # Remove found files from remaining list
        remaining = [(n, d) for n, d in remaining if n not in newly_found]

        tested += 1

        if newly_found or tested % BATCH_SIZE == 0:
            now = time.monotonic()
            elapsed = now - t_start
            rate = tested / elapsed if elapsed > 0 else 0.0
            pct = min(1.0, tested / TOTAL_CANDIDATES)
            found_count = n - len(remaining)

            prog_bar.progress(pct)
            stat_ph.markdown(
                f'<div class="stat-bar">'
                f'⏱ <b>{elapsed:.0f}s</b> elapsed &nbsp;·&nbsp; '
                f'🔑 Tested: <b>{tested:,}</b> &nbsp;·&nbsp; '
                f'🚀 Speed: <b>{rate:,.0f}/s</b> &nbsp;·&nbsp; '
                f'✅ Unlocked: <b>{found_count}/{n}</b>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if newly_found:
                render_cards()

    # Mark remaining (not found) files
    for fname, _ in remaining:
        results[fname] = False
    render_cards()

    prog_bar.progress(1.0)
    total_elapsed = time.monotonic() - t_start
    found_count = sum(1 for v in results.values() if v not in (None, False))
    stat_ph.markdown(
        f'<div class="stat-bar">'
        f'✅ Done in <b>{total_elapsed:.1f}s</b> &nbsp;·&nbsp; '
        f'Unlocked: <b>{found_count}/{n}</b> files &nbsp;·&nbsp; '
        f'Tested: <b>{tested:,}</b> candidates'
        f'</div>',
        unsafe_allow_html=True,
    )

    # --- Individual download buttons ---
    if unlocked_pdfs:
        st.subheader("📥 Download Unlocked Files")
        for fname, data in unlocked_pdfs.items():
            st.download_button(
                label=f"⬇️ Download unlocked_{fname}",
                data=data,
                file_name=f"unlocked_{fname}",
                mime="application/pdf",
            )

        # --- ZIP download if more than 1 ---
        if len(unlocked_pdfs) > 1:
            zip_data = make_zip(
                [(f"unlocked_{n}", d) for n, d in unlocked_pdfs.items()]
            )
            st.download_button(
                label="📦 Download All Unlocked PDFs (.ZIP)",
                data=zip_data,
                file_name="unlocked_pdfs.zip",
                mime="application/zip",
                type="primary",
            )

# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------
st.markdown("""
<div style="text-align:center;color:#475569;font-size:0.78rem;margin-top:2.5rem;
border-top:1px solid rgba(255,255,255,0.06);padding-top:1rem;">
🔒 Files processed in-memory. Nothing stored or transmitted externally.
</div>
""", unsafe_allow_html=True)
