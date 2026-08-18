import io
import itertools
import string
import time
import streamlit as st
from pypdf import PdfReader, PdfWriter

# -----------------------------------------------------------------------------
# 1. Page Configuration & Mobile-First Ultra-Modern CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="PDF KeyUnlock - Fast Password Recovery & Unprotected PDF",
    page_icon="🔓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    /* Google Font Import */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Container Spacing */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        max-width: 960px !important;
    }

    /* Hero Header */
    .hero-container {
        text-align: center;
        padding: 1.5rem 1rem 2rem 1rem;
        background: linear-gradient(180deg, rgba(99, 102, 241, 0.1) 0%, rgba(15, 23, 42, 0) 100%);
        border-radius: 20px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(99, 102, 241, 0.2);
    }
    
    .badge-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 9999px;
        background: rgba(99, 102, 241, 0.15);
        color: #818cf8;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 0.75rem;
        border: 1px solid rgba(99, 102, 241, 0.3);
    }

    .hero-title {
        font-size: clamp(1.8rem, 4vw, 2.6rem);
        font-weight: 800;
        background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #818cf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.2;
        margin-bottom: 0.5rem;
    }

    .hero-subtitle {
        color: #94a3b8;
        font-size: clamp(0.9rem, 2vw, 1.05rem);
        max-width: 600px;
        margin: 0 auto;
        line-height: 1.5;
    }

    /* Modern Card Styles */
    .glass-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.25rem;
        margin-bottom: 1.25rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }

    /* Mobile Responsive Metrics */
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
        gap: 0.75rem;
        margin: 1rem 0;
    }

    .metric-box {
        background: rgba(15, 23, 42, 0.8);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        padding: 0.85rem;
        text-align: center;
    }

    .metric-val {
        font-size: 1.25rem;
        font-weight: 700;
        color: #38bdf8;
        font-family: monospace;
    }

    .metric-lbl {
        font-size: 0.75rem;
        color: #94a3b8;
        margin-top: 0.25rem;
        text-transform: uppercase;
        font-weight: 600;
    }

    /* Success Card */
    .success-banner {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.05) 100%);
        border: 1px solid #10b981;
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1.5rem 0;
        text-align: center;
        box-shadow: 0 0 30px rgba(16, 185, 129, 0.15);
    }

    .password-display {
        font-size: 1.75rem;
        font-weight: 800;
        color: #10b981;
        background: #0b0f19;
        padding: 0.5rem 1.5rem;
        border-radius: 10px;
        display: inline-block;
        font-family: 'Consolas', 'Courier New', monospace;
        letter-spacing: 2px;
        border: 1px dashed #10b981;
        margin: 0.75rem 0;
    }

    /* Primary Buttons on Mobile */
    div.stButton > button {
        border-radius: 12px;
        font-weight: 600;
        padding: 0.65rem 1.25rem;
        transition: all 0.2s ease;
    }

    div.stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(99, 102, 241, 0.3);
    }
    
    /* Hide Streamlit footer branding */
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 2. Helper Functions & Core Decryption Engine
# -----------------------------------------------------------------------------

def validate_pdf_bytes(pdf_bytes: bytes) -> tuple[bool, str, int]:
    """Validates PDF readability and encryption status."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        num_pages = len(reader.pages)
        if not reader.is_encrypted:
            return False, "This PDF is already unprotected (No password required).", num_pages
        return True, "Valid encrypted PDF ready for unlocking.", num_pages
    except Exception as exc:
        return False, f"Could not read PDF file: {exc}", 0


def create_unlocked_pdf(pdf_bytes: bytes, password: str) -> bytes | None:
    """Decrypts and returns unprotected PDF bytes."""
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


def create_sample_demo_pdf(password: str = "RAMK1998") -> bytes:
    """Generates an in-memory sample encrypted PDF for instant 1-click testing."""
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=200)
    writer.encrypt(password)
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    return buf.getvalue()


# -----------------------------------------------------------------------------
# 3. Header & Hero Section
# -----------------------------------------------------------------------------

st.markdown(
    """
    <div class="hero-container">
        <span class="badge-pill">⚡ Ultra Fast & Secure</span>
        <div class="hero-title">PDF Password Recovery</div>
        <div class="hero-subtitle">
            Recover lost passwords for your authorized bank statements, pay slips, and documents in seconds — right from your browser.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 4. Step 1: Upload / Choose PDF
# -----------------------------------------------------------------------------

st.markdown("### 📄 Step 1: Select Your PDF File")

pdf_source = st.radio(
    "Choose PDF source:",
    ["📤 Upload My PDF File", "🧪 Test with Demo Locked PDF (Password: RAMK1998)"],
    horizontal=True,
    label_visibility="collapsed",
)

pdf_bytes = None
file_name = "document.pdf"

if pdf_source == "📤 Upload My PDF File":
    uploaded_file = st.file_uploader(
        "Upload locked PDF",
        type=["pdf"],
        help="All processing happens securely in-memory. Your files are never stored.",
        label_visibility="collapsed",
    )
    if uploaded_file is not None:
        pdf_bytes = uploaded_file.getvalue()
        file_name = uploaded_file.name
else:
    pdf_bytes = create_sample_demo_pdf("RAMK1998")
    file_name = "demo_sample_encrypted.pdf"
    st.info("🧪 **Demo PDF Active**: Password is set to `RAMK1998` (Initials `RAMK` + Year `1998`). Test Smart Mode below!")

# Validation
pdf_ready = False
if pdf_bytes is not None:
    is_valid, msg, pages = validate_pdf_bytes(pdf_bytes)
    if is_valid:
        st.success(f"✅ **{file_name}** ({pages} page{'s' if pages>1 else ''}) is encrypted and ready.")
        pdf_ready = True
    else:
        st.error(f"❌ {msg}")
        pdf_ready = False
else:
    st.caption("👆 Tap or drag-and-drop your `.pdf` file above to begin.")

st.divider()

# -----------------------------------------------------------------------------
# 5. Step 2: Choose Search Strategy (Mobile-Friendly Tabs)
# -----------------------------------------------------------------------------

st.markdown("### ⚡ Step 2: Choose Password Pattern")

tab_smart, tab_pin, tab_full, tab_wordlist = st.tabs([
    "🚀 Smart Pattern (Name/Letters + Year)",
    "🔢 Numeric PIN (4–8 Digits)",
    "🔤 Full A-Z Search",
    "📝 Custom Wordlist",
])

candidates_list: list[str] | None = None
lazy_generator = None
estimated_total = 0

# --- Tab 1: Smart Mode (Most popular for Indian bank statements, Aadhaar, salary slips) ---
with tab_smart:
    st.markdown("💡 *Best for Pay Slips, Bank Statements, PAN (e.g. `RAMK1998`, `KUMAR2001`, `ab1995`)*")
    
    col_p1, col_p2 = st.columns([1.5, 1])
    with col_p1:
        prefix_input = st.text_input(
            "Known Name Initials / Prefix Letters",
            value="RAMK" if pdf_source != "📤 Upload My PDF File" else "",
            placeholder="e.g. RAMK, RA, AKSHAY",
            help="Upper, lower, and capitalized variations will be checked automatically.",
        ).strip()
    with col_p2:
        preset = st.selectbox(
            "Preset format:",
            ["Custom", "First 4 Letters of Name", "Full First Name", "PAN Format (5 Letters)"],
            index=0,
        )

    col_yr1, col_yr2 = st.columns(2)
    with col_yr1:
        smart_y_start = st.number_input("Start Birth Year", min_value=1940, max_value=2030, value=1985, key="sm_y1")
    with col_yr2:
        smart_y_end = st.number_input("End Birth Year", min_value=1940, max_value=2030, value=2015, key="sm_y2")

    if smart_y_start > smart_y_end:
        st.error("Start year must be <= End year")
    else:
        years = [str(y) for y in range(int(smart_y_start), int(smart_y_end) + 1)]
        if prefix_input:
            prefixes = [prefix_input.upper(), prefix_input.lower(), prefix_input.capitalize()]
            prefixes = list(dict.fromkeys(prefixes))
            candidates_list = [f"{p}{y}" for p in prefixes for y in years]
        else:
            candidates_list = years
        estimated_total = len(candidates_list)
        st.caption(f"📊 Total search space: **{estimated_total:,} passwords** (Estimated time: **< 1 second**)")

# --- Tab 2: Numeric PIN ---
with tab_pin:
    st.markdown("💡 *Best for 4-digit or 6-digit numeric PINs (Aadhaar, Credit Card Statements, Mobile PIN)*")
    pin_len = st.slider("Select PIN Length", min_value=4, max_value=8, value=4, step=1)
    estimated_total_pin = 10 ** pin_len
    st.caption(f"📊 Total combinations: **{estimated_total_pin:,}** (`{'0'*pin_len}` to `{'9'*pin_len}`)")

    def make_pin_gen(l: int):
        fmt = f"{{:0{l}d}}"
        for i in range(10 ** l):
            yield fmt.format(i)

    if tab_pin:
        # If user is in this mode
        pass

# --- Tab 3: Full 4-Letter Combination ---
with tab_full:
    st.warning("⚠️ Full search over all 4 letters (AAAA to ZZZZ) has ~8 Million candidates. May take a few minutes in browser.")
    col_fy1, col_fy2 = st.columns(2)
    with col_fy1:
        full_y1 = st.number_input("Start Year", min_value=1970, max_value=2030, value=1990, key="f_y1")
    with col_fy2:
        full_y2 = st.number_input("End Year", min_value=1970, max_value=2030, value=2005, key="f_y2")

    num_yrs = max(1, int(full_y2 - full_y1 + 1))
    estimated_total_full = (26 ** 4) * num_yrs
    st.caption(f"📊 Total candidates: **{estimated_total_full:,}** (456,976 prefixes × {num_yrs} years)")

    def make_full_gen(y_start: int, y_end: int):
        years_s = [str(y) for y in range(y_start, y_end + 1)]
        for a, b, c, d in itertools.product(string.ascii_uppercase, repeat=4):
            p = f"{a}{b}{c}{d}"
            for y in years_s:
                yield f"{p}{y}"

# --- Tab 4: Custom Wordlist ---
with tab_wordlist:
    st.markdown("💡 *Upload a `.txt` wordlist or paste common passwords line-by-line.*")
    wl_file = st.file_uploader("Upload Wordlist (.txt)", type=["txt"], key="wl_up")
    wl_text = st.text_area("Or enter passwords (one per line):", placeholder="Pass@123\nWelcome2024\n123456\nAdmin#1", height=100)
    
    words = []
    if wl_file:
        words.extend(wl_file.read().decode("utf-8", errors="ignore").splitlines())
    if wl_text.strip():
        words.extend(wl_text.splitlines())
    custom_words = list(dict.fromkeys([w.strip() for w in words if w.strip()]))
    estimated_total_wl = len(custom_words)
    st.caption(f"📊 Total words loaded: **{estimated_total_wl:,}**")

st.divider()

# -----------------------------------------------------------------------------
# 6. Step 3: Execution & Real-Time Performance Monitor
# -----------------------------------------------------------------------------

st.markdown("### 🚀 Step 3: Run Recovery")

active_tab = st.selectbox(
    "Confirm Search Mode to Execute:",
    [
        "🚀 Smart Pattern (Prefix + Year)",
        "🔢 Numeric PIN",
        "🔤 Full A-Z Search",
        "📝 Custom Wordlist",
    ],
    index=0,
)

# Assign generator based on chosen active mode
if active_tab == "🚀 Smart Pattern (Prefix + Year)":
    chosen_gen = candidates_list
    total_candidates_to_test = estimated_total
elif active_tab == "🔢 Numeric PIN":
    chosen_gen = make_pin_gen(pin_len)
    total_candidates_to_test = estimated_total_pin
elif active_tab == "🔤 Full A-Z Search":
    chosen_gen = make_full_gen(int(full_y1), int(full_y2))
    total_candidates_to_test = estimated_total_full
else:
    chosen_gen = custom_words
    total_candidates_to_test = estimated_total_wl

col_btn, col_info = st.columns([1.5, 2.5])
with col_btn:
    start_btn = st.button("🔓 Start Password Recovery", type="primary", use_container_width=True, disabled=not pdf_ready)
with col_info:
    if pdf_ready:
        st.write(f"Ready to test **{total_candidates_to_test:,}** candidate combinations.")
    else:
        st.write("Please select or upload a valid encrypted PDF above first.")

if start_btn and pdf_ready:
    if total_candidates_to_test == 0:
        st.error("❌ No candidates configured. Please enter prefix/passwords in Step 2.")
    else:
        progress_bar = st.progress(0.0)
        status_msg = st.empty()
        
        # Real-time metrics grid
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            m_tested = st.empty()
        with col2:
            m_candidate = st.empty()
        with col3:
            m_rate = st.empty()
        with col4:
            m_elapsed = st.empty()

        reader = PdfReader(io.BytesIO(pdf_bytes))
        start_time = time.monotonic()
        tested = 0
        found_password = None
        last_ui_refresh = start_time
        
        status_msg.info("🔄 Searching for matching password...")
        
        for candidate in chosen_gen:
            try:
                is_match = reader.decrypt(candidate)
            except Exception:
                is_match = 0

            tested += 1

            if is_match:
                found_password = candidate
                break

            now = time.monotonic()
            if (now - last_ui_refresh) >= 0.25 or (tested % 400 == 0):
                elapsed = now - start_time
                rate = tested / elapsed if elapsed > 0 else 0.0
                pct = min(1.0, tested / total_candidates_to_test) if total_candidates_to_test > 0 else 0.0
                
                progress_bar.progress(pct)
                m_tested.metric("Tested", f"{tested:,}")
                m_candidate.metric("Current", candidate)
                m_rate.metric("Speed", f"{rate:,.0f} /s")
                m_elapsed.metric("Elapsed", f"{elapsed:.1f}s")
                last_ui_refresh = now

        elapsed_total = time.monotonic() - start_time
        progress_bar.progress(1.0 if found_password else min(1.0, tested / total_candidates_to_test if total_candidates_to_test > 0 else 1.0))
        status_msg.empty()

        if found_password:
            st.balloons()
            st.markdown(
                f"""
                <div class="success-banner">
                    <h2 style="color: #10b981; margin: 0 0 0.5rem 0;">🎉 Password Successfully Found!</h2>
                    <div>The password for <b>{file_name}</b> is:</div>
                    <div class="password-display">{found_password}</div>
                    <div style="color: #94a3b8; font-size: 0.9rem;">
                        Tested <b>{tested:,}</b> passwords in <b>{elapsed_total:.2f}s</b> ({tested/elapsed_total if elapsed_total>0 else 0:,.0f} passwords/sec).
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 1-Click Decrypted PDF Download
            unlocked_pdf = create_unlocked_pdf(pdf_bytes, found_password)
            if unlocked_pdf:
                st.markdown("#### ⬇️ Step 4: Download Unlocked (No Password) PDF")
                st.download_button(
                    label="📥 Click to Download Unprotected PDF",
                    data=unlocked_pdf,
                    file_name=f"unlocked_{file_name}",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                )
                st.success("✨ Downloaded PDF will never ask for a password again!")
        else:
            st.error(
                f"❌ Password not found among the **{tested:,}** tested candidates ({elapsed_total:.1f}s).\n\n"
                "**Tips**: Try checking the Smart Pattern with your full name or try a wider birth year range."
            )

# -----------------------------------------------------------------------------
# 7. Footer & Security Assurance
# -----------------------------------------------------------------------------
st.markdown(
    """
    <div style="text-align: center; margin-top: 3rem; color: #64748b; font-size: 0.8rem; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 1.5rem;">
        🔒 <b>100% In-Memory & Private</b>: PDF files and passwords are never sent to external servers or logged.
    </div>
    """,
    unsafe_allow_html=True,
)
