import io
import string
import time
from typing import Iterator
import streamlit as st
from pypdf import PdfReader, PdfWriter

# -----------------------------------------------------------------------------
# 1. Constants (Exact Same as Original Python pdf_tester.py)
# -----------------------------------------------------------------------------
UPPERCASE_LETTERS = string.ascii_uppercase  # "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
PREFIX_LENGTH = 4
YEAR_START = 1990
YEAR_END = 2007  # inclusive

NUM_PREFIXES = len(UPPERCASE_LETTERS) ** PREFIX_LENGTH  # 26**4 = 456,976
NUM_YEARS = YEAR_END - YEAR_START + 1  # 18
TOTAL_CANDIDATES = NUM_PREFIXES * NUM_YEARS  # 8,225,568
BATCH_INTERVAL = 1000  # Fast batch interval to eliminate UI render overhead


def _generate_prefixes() -> Iterator[str]:
    """Lazily yield every 4-letter uppercase combination, AAAA..ZZZZ."""
    letters = UPPERCASE_LETTERS
    for a in letters:
        for b in letters:
            for c in letters:
                for d in letters:
                    yield a + b + c + d


def generate_candidates() -> Iterator[str]:
    """
    Lazily yield candidate passwords in the form XXXXYYYY, where XXXX is
    an uppercase 4-letter combination and YYYY is a year in [1990, 2007].
    """
    years = [str(y) for y in range(YEAR_START, YEAR_END + 1)]
    for prefix in _generate_prefixes():
        for year in years:
            yield prefix + year


def validate_pdf(pdf_bytes: bytes) -> tuple[bool, str]:
    """Verify the file is a valid, encrypted PDF."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if not reader.is_encrypted:
            return False, "This PDF is not password-protected. There is no password to search for."
        return True, "Valid password-protected PDF."
    except Exception as exc:
        return False, f"Could not read PDF: {exc}"


def generate_unlocked_pdf(pdf_bytes: bytes, password: str) -> bytes | None:
    """Creates decrypted PDF for download."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        reader.decrypt(password)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        out = io.BytesIO()
        writer.write(out)
        out.seek(0)
        return out.getvalue()
    except Exception:
        return None


# -----------------------------------------------------------------------------
# 2. Page Configuration & Clean UI
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="PDF Password Tester",
    page_icon="⚡",
    layout="centered",
)

st.title("⚡ PDF Password Tester (Fast Batching)")

# Section 1: PDF Selection
st.subheader("1. PDF File")
uploaded_file = st.file_uploader(
    "Choose a password-protected PDF",
    type=["pdf"],
    label_visibility="collapsed",
)

pdf_ready = False
pdf_bytes = None

if uploaded_file is not None:
    pdf_bytes = uploaded_file.getvalue()
    is_valid, msg = validate_pdf(pdf_bytes)
    if is_valid:
        st.success(f"Ready: **{uploaded_file.name}**")
        pdf_ready = True
    else:
        st.error(msg)
else:
    st.info("Select a PDF file to begin.")

# Section 2: Search Settings (Exact same as Original GUI)
with st.expander("Search Settings", expanded=True):
    st.write("**Password format:** `XXXXYYYY`")
    st.write("`X` = uppercase letter (A-Z) &nbsp;&nbsp;&nbsp;&nbsp; `YYYY` = year")
    st.write(f"**Years:** {YEAR_START} - {YEAR_END}")
    st.write(f"**Total candidate passwords:** {NUM_PREFIXES:,} x {NUM_YEARS} = **{TOTAL_CANDIDATES:,}**")

# Section 3: Controls & Progress
st.subheader("2. Progress & Search")

start_clicked = st.button(
    "🚀 Start Search (Fast Batching)",
    type="primary",
    use_container_width=True,
    disabled=not pdf_ready,
)

if start_clicked and pdf_ready:
    progress_bar = st.progress(0.0)
    status_text = st.empty()
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        stat_candidate = st.empty()
    with col2:
        stat_tested = st.empty()
    with col3:
        stat_elapsed = st.empty()
    with col4:
        stat_rate = st.empty()
    with col5:
        stat_pct = st.empty()

    reader = PdfReader(io.BytesIO(pdf_bytes))
    decrypt_fn = reader.decrypt
    start_time = time.monotonic()
    tested = 0
    found_password = None
    total = TOTAL_CANDIDATES
    
    status_text.info("⚡ Fast batch search in progress...")

    for candidate in generate_candidates():
        try:
            if decrypt_fn(candidate):
                found_password = candidate
                tested += 1
                break
        except Exception:
            pass

        tested += 1

        # Fast batch trigger every 1,000 attempts
        if tested % BATCH_INTERVAL == 0:
            now = time.monotonic()
            elapsed = now - start_time
            rate = tested / elapsed if elapsed > 0 else 0.0
            pct = (tested / total) * 100.0

            progress_bar.progress(min(1.0, tested / total))
            stat_candidate.metric("Current", candidate)
            stat_tested.metric("Tested", f"{tested:,}")
            stat_elapsed.metric("Elapsed", f"{elapsed:.1f}s")
            stat_rate.metric("Rate", f"{rate:,.0f}/s")
            stat_pct.metric("Progress", f"{pct:.3f}%")

    total_elapsed = time.monotonic() - start_time
    status_text.empty()

    if found_password:
        progress_bar.progress(1.0)
        stat_pct.metric("Progress", "100.0%")
        st.success(f"🎉 **Password Found: `{found_password}`**")
        st.write(f"• **Attempts:** {tested:,}")
        st.write(f"• **Elapsed time:** {total_elapsed:.1f}s ({tested/total_elapsed if total_elapsed>0 else 0:,.0f} passwords/sec)")
        st.balloons()

        # Download Unlocked PDF
        unlocked = generate_unlocked_pdf(pdf_bytes, found_password)
        if unlocked:
            st.download_button(
                label="📥 Download Unlocked PDF",
                data=unlocked,
                file_name=f"unlocked_{uploaded_file.name}",
                mime="application/pdf",
                type="primary",
            )
    else:
        st.warning("Password not found in the specified pattern/range.")
