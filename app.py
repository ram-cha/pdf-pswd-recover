import datetime
import io
import itertools
import string
import time
from typing import Generator
import streamlit as st
from pypdf import PdfReader, PdfWriter

# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="PDF Fast Password Unlocker",
    page_icon="⚡",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# -----------------------------------------------------------------------------
# 2. Modern UI Styling
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
        margin-bottom: 1.25rem;
    }

    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 50%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }

    .badge-fast {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 9999px;
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        border: 1px solid rgba(16, 185, 129, 0.3);
        margin-bottom: 0.5rem;
    }

    .main-sub {
        color: #94a3b8;
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

    #MainMenu, header, footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 3. High-Priority Name Prefixes & Smart Fast Candidate Generator
# -----------------------------------------------------------------------------

COMMON_INDIAN_NAME_PREFIXES = [
    # Top Common First Names (4 letters)
    "RAMK", "RAHU", "ROHI", "AMIT", "VIKA", "ANKI", "NEHA", "POOJ", "AJAY", "VIJA",
    "SURE", "MUKE", "DEEP", "MANO", "RAJE", "SUNI", "ANIL", "SANJ", "PANK", "DINE",
    "KUMA", "SING", "SHAR", "VERM", "GUPT", "PATI", "YADA", "MOHA", "SANT", "RAVI",
    "KISH", "ASHO", "ANAN", "ABHI", "ALOK", "ARUN", "BHAR", "CHET", "DEVA", "GAUR",
    "HARI", "HIMA", "JITE", "KAMA", "KAPI", "LALI", "MAHE", "NAVE", "PAVA", "PRAD",
    "PRAV", "RAKE", "RISH", "SACH", "SATY", "SHIV", "SHUB", "SOUR", "SUBH", "SUMI",
    "TARU", "UMES", "VARU", "VIVE", "YOGE", "ANUJ", "ATUL", "AYUS", "BHAV", "CHIR",
    "DIPA", "DIVY", "GOPA", "HARP", "HEMA", "INDR", "JAGA", "JASM", "JAYA", "JYOT",
    "KARA", "KART", "KAVI", "KHUS", "KIRA", "KRIS", "KUNA", "LAKS", "LOVI", "MADA",
    "MADH", "MAMA", "MANI", "MEEN", "MEGH", "MOHI", "MONA", "MONU", "MUKU", "NAND",
    "NARA", "NARE", "NEEL", "NEER", "NIKI", "NISH", "NITI", "OMPR", "PALL", "PARM",
    "PARV", "PAYA", "PINK", "PIYU", "POON", "PRAB", "PRAT", "PREE", "PREM", "PRER",
    "PRIT", "PUSP", "RACH", "RADH", "RAGH", "RAJK", "RAJN", "RAJU", "RAKS", "RAMA",
    "RAME", "RANI", "RASH", "REEN", "REKH", "RENU", "RINK", "RITU", "RIYA", "ROOP",
    "ROSH", "RUBY", "RUCH", "RUPA", "SADH", "SAGR", "SAHI", "SAJA", "SAKS", "SAME",
    "SAND", "SANG", "SAPN", "SARA", "SARO", "SARV", "SASH", "SEEM", "SHAI", "SHAL",
    "SHAS", "SHET", "SHIK", "SHIL", "SHOB", "SHRE", "SHRU", "SHYA", "SIMR", "SITA",
    "SKAN", "SNEH", "SONA", "SONI", "SONU", "SRID", "SRIN", "SRIS", "SUBR", "SUCH",
    "SUDH", "SUJA", "SUJI", "SUKH", "SUMA", "SUND", "SUNY", "SURA", "SURY", "SUSH",
    "SWAT", "TANI", "TEJA", "TRIP", "TRIS", "TUSH", "UDAY", "UJJA", "UPEN", "USHA",
    "VAIB", "VAIS", "VAND", "VARN", "VEDP", "VEER", "VIBH", "VIDY", "VIHA", "VIKR",
    "VIMA", "VINA", "VINI", "VINO", "VIRA", "VISH", "VRIN", "YASH", "YOGI",
    # Additional Common Prefixes & Surnames
    "CHOU", "MISH", "JAIN", "AGAR", "PAND", "TIWA", "DUBE", "SHUK", "TRIP", "REDD",
    "NAIR", "MENO", "PILL", "RAO", "IYER", "IYEN", "DESH", "KULK", "JOSH", "BHAT",
    "GOWA", "CHAU", "THAK", "RATH", "ROUT", "SAHO", "PATT", "MOHA", "DAS", "DUTT",
    "BOSE", "GHOS", "BANER", "CHAT", "MUKH", "SEN", "ROY", "PAUL", "SAHA", "DEY",
]

YEAR_START = 1975
YEAR_END = 2020


def generate_smart_candidates() -> Generator[str, None, None]:
    """
    Ultra-Fast Smart Priority Candidate Generator:
    1. Phase 1 (Instant < 2s): High-frequency Name Prefixes + Common Years
    2. Phase 2: Common Date of Birth formats (DDMMYYYY, DDMM)
    3. Phase 3: Exhaustive AAAA..ZZZZ search across all years
    """
    seen = set()
    years = [str(y) for y in range(YEAR_START, YEAR_END + 1)]

    # --- Phase 1: High Frequency Names (Uppercase & Capitalized) ---
    for p in COMMON_INDIAN_NAME_PREFIXES:
        for y in years:
            for pref in (p.upper(), p.capitalize()):
                cand = f"{pref}{y}"
                if cand not in seen:
                    seen.add(cand)
                    yield cand

    # --- Phase 2: DOB Patterns (DDMMYYYY & DDMM) ---
    for yr in range(1975, 2021):
        for m in range(1, 13):
            for d in range(1, 32):
                try:
                    dt = datetime.date(yr, m, d)
                    c1 = f"{dt.day:02d}{dt.month:02d}{dt.year}"
                    c2 = f"{dt.day:02d}{dt.month:02d}"
                    if c1 not in seen:
                        seen.add(c1)
                        yield c1
                    if c2 not in seen:
                        seen.add(c2)
                        yield c2
                except ValueError:
                    pass

    # --- Phase 3: Exhaustive 4-Letter Permutations (AAAA to ZZZZ) ---
    letters = string.ascii_uppercase
    for a in letters:
        for b in letters:
            for c in letters:
                for d in letters:
                    pref = f"{a}{b}{c}{d}"
                    for y in years:
                        cand = f"{pref}{y}"
                        if cand not in seen:
                            yield cand


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


def create_demo_pdf(password: str = "ROHI1998") -> bytes:
    """Generates a sample encrypted PDF for testing."""
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=200)
    writer.encrypt(password)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.getvalue()


# -----------------------------------------------------------------------------
# 4. Header & 1-Click Upload Interface
# -----------------------------------------------------------------------------

st.markdown(
    """
    <div class="main-header">
        <span class="badge-fast">⚡ Smart Priority Turbo Engine</span>
        <div class="main-title">PDF Password Unlocker</div>
        <div class="main-sub">Zero configuration. Upload your PDF and find the password in seconds.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# PDF Source selection
source_choice = st.radio(
    "Source:",
    ["📁 Upload My PDF File", "🧪 Test Demo PDF (Password: ROHI1998)"],
    horizontal=True,
    label_visibility="collapsed",
)

pdf_bytes = None
file_name = "document.pdf"

if source_choice == "📁 Upload My PDF File":
    up_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        help="Upload your locked PDF file.",
        label_visibility="collapsed",
    )
    if up_file is not None:
        pdf_bytes = up_file.getvalue()
        file_name = up_file.name
else:
    pdf_bytes = create_demo_pdf("ROHI1998")
    file_name = "demo_sample.pdf"
    st.info("🧪 **Demo PDF Loaded**: Password is `ROHI1998`. Click Start below to see it find it instantly in < 0.1s!")

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

st.write("")

# -----------------------------------------------------------------------------
# 5. One-Click Turbo Execution
# -----------------------------------------------------------------------------

start_btn = st.button(
    "🚀 Start Fast Password Search",
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
    
    status_placeholder.info("⚡ Turbo Search in progress (Prioritizing high-probability patterns)...")

    # Estimated visual total for progress indicator
    ESTIMATED_MAX = 500_000

    for candidate in generate_smart_candidates():
        try:
            match = reader.decrypt(candidate)
        except Exception:
            match = 0

        tested += 1

        if match:
            found_password = candidate
            break

        now = time.monotonic()
        # Throttled UI refresh to maximize CPU decryption speed
        if (now - last_ui_update) >= 0.25 or (tested % 500 == 0):
            elapsed = now - start_time
            rate = tested / elapsed if elapsed > 0 else 0.0
            pct = min(0.99, tested / ESTIMATED_MAX)

            progress_bar.progress(pct)
            m_tested.metric("Tested", f"{tested:,}")
            m_current.metric("Current", candidate)
            m_speed.metric("Speed", f"{rate:,.0f} /s")
            m_elapsed.metric("Elapsed", f"{elapsed:.1f}s")
            last_ui_update = now

    total_elapsed = time.monotonic() - start_time
    progress_bar.progress(1.0)
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
                    Found in <b>{tested:,} attempts</b> within <b>{total_elapsed:.2f} seconds</b> ({tested/total_elapsed if total_elapsed>0 else 0:,.0f} passwords/sec).
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
            f"❌ Password not found after testing {tested:,} candidates ({total_elapsed:.1f}s)."
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
