import io
import itertools
import string
import time
import streamlit as st
from pypdf import PdfReader, PdfWriter

# -----------------------------------------------------------------------------
# Page Configuration & Custom CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="PDF Password Recovery & Unlocker",
    page_icon="🔓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Gradient Header */
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .hero-subtitle {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    /* Stat Cards */
    .metric-card {
        background: #1e293b;
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid #334155;
        text-align: center;
    }
    .metric-value {
        font-size: 1.4rem;
        font-weight: 700;
        color: #38bdf8;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
    }
    /* Result Box */
    .success-card {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid #10b981;
        border-radius: 12px;
        padding: 1.2rem;
        margin-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

def validate_pdf(pdf_bytes: bytes) -> tuple[bool, str, int]:
    """Validates the PDF bytes and checks encryption."""
    try:
        stream = io.BytesIO(pdf_bytes)
        reader = PdfReader(stream)
        num_pages = len(reader.pages)
        is_encrypted = reader.is_encrypted
        if not is_encrypted:
            return False, "This PDF is not password-protected.", num_pages
        return True, "Valid encrypted PDF.", num_pages
    except Exception as exc:
        return False, f"Could not read PDF: {exc}", 0


def generate_decrypted_pdf(pdf_bytes: bytes, password: str) -> bytes | None:
    """Decrypts and returns the unprotected PDF bytes."""
    try:
        stream = io.BytesIO(pdf_bytes)
        reader = PdfReader(stream)
        reader.decrypt(password)
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        out_stream = io.BytesIO()
        writer.write(out_stream)
        out_stream.seek(0)
        return out_stream.getvalue()
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Main Application Layout
# -----------------------------------------------------------------------------

st.markdown('<div class="hero-title">🔓 PDF Password Recovery & Unlocker</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-subtitle">Fast, secure candidate password search & instant 1-click PDF unlocking for authorized files.</div>', unsafe_allow_html=True)

# Sidebar: Attack Configuration
with st.sidebar:
    st.header("⚙️ Search Configuration")
    
    search_mode = st.selectbox(
        "Select Search Mode",
        [
            "⚡ Smart Pattern (Prefix + Year)",
            "🔤 Full Pattern (4 Letters + Year)",
            "🔢 Numeric PIN (4 to 8 Digits)",
            "📝 Custom Wordlist / Candidate List",
        ],
        index=0,
    )
    
    candidates_list: list[str] | None = None
    lazy_generator = None
    estimated_total = 0
    
    if search_mode == "⚡ Smart Pattern (Prefix + Year)":
        st.info("💡 Enter known details (e.g. Name Initials / Letters) for instant speed.")
        known_prefix = st.text_input(
            "Known Prefix / Initials (e.g., RAMK, AB, K)",
            value="AAAA",
            help="Upper/lowercase letters will be tested automatically.",
        ).strip()
        
        col_y1, col_y2 = st.columns(2)
        with col_y1:
            year_start = st.number_input("Start Year", min_value=1950, max_value=2030, value=1990)
        with col_y2:
            year_end = st.number_input("End Year", min_value=1950, max_value=2030, value=2010)
            
        if year_start > year_end:
            st.error("Start year must be <= End year")
        else:
            years = [str(y) for y in range(int(year_start), int(year_end) + 1)]
            prefixes = [known_prefix.upper(), known_prefix.lower(), known_prefix.capitalize()] if known_prefix else [""]
            prefixes = list(dict.fromkeys(prefixes))
            candidates_list = [f"{p}{y}" for p in prefixes for y in years]
            estimated_total = len(candidates_list)
            st.caption(f"Total candidates: **{estimated_total:,}** (Runs in < 1 second)")

    elif search_mode == "🔤 Full Pattern (4 Letters + Year)":
        st.warning("⚠️ Full search over all 4 letters (A-Z) has ~8M combinations.")
        col_y1, col_y2 = st.columns(2)
        with col_y1:
            year_start = st.number_input("Start Year", min_value=1950, max_value=2030, value=1990, key="full_y1")
        with col_y2:
            year_end = st.number_input("End Year", min_value=1950, max_value=2030, value=2007, key="full_y2")
            
        num_years = max(1, int(year_end - year_start + 1))
        estimated_total = (26 ** 4) * num_years
        st.caption(f"Total candidates: **{estimated_total:,}** (456,976 prefixes × {num_years} years)")
        
        def full_generator(y_start: int, y_end: int):
            years_str = [str(y) for y in range(y_start, y_end + 1)]
            for a, b, c, d in itertools.product(string.ascii_uppercase, repeat=4):
                prefix = f"{a}{b}{c}{d}"
                for year in years_str:
                    yield f"{prefix}{year}"
                    
        lazy_generator = full_generator(int(year_start), int(year_end))

    elif search_mode == "🔢 Numeric PIN (4 to 8 Digits)":
        pin_length = st.slider("PIN Length (Digits)", min_value=4, max_value=8, value=4)
        estimated_total = 10 ** pin_length
        st.caption(f"Total combinations: **{estimated_total:,}** (0000 to {'9'*pin_length})")
        
        def pin_generator(length: int):
            fmt = f"{{:0{length}d}}"
            for i in range(10 ** length):
                yield fmt.format(i)
                
        lazy_generator = pin_generator(pin_length)

    elif search_mode == "📝 Custom Wordlist / Candidate List":
        uploaded_wordlist = st.file_uploader("Upload Wordlist (.txt)", type=["txt"])
        custom_text = st.text_area("Or type candidate passwords (one per line)", height=120)
        
        words = []
        if uploaded_wordlist is not None:
            words.extend(uploaded_wordlist.read().decode("utf-8", errors="ignore").splitlines())
        if custom_text.strip():
            words.extend(custom_text.splitlines())
            
        candidates_list = [w.strip() for w in words if w.strip()]
        candidates_list = list(dict.fromkeys(candidates_list))  # remove duplicates
        estimated_total = len(candidates_list)
        st.caption(f"Total candidate words: **{estimated_total:,}**")

    st.divider()
    st.caption("🔒 **Security & Privacy**: Files and passwords are processed in memory and never stored permanently.")

# Main Body: File Upload & Search Execution
uploaded_file = st.file_uploader(
    "📁 Upload your password-protected PDF",
    type=["pdf"],
    help="Upload the PDF file you own or have permission to access.",
)

if uploaded_file is None:
    st.info("👆 Please upload a PDF file above to begin.")
else:
    pdf_bytes = uploaded_file.getvalue()
    is_valid, msg, page_count = validate_pdf(pdf_bytes)
    
    if not is_valid:
        st.error(f"❌ {msg}")
    else:
        st.success(f"✅ PDF loaded successfully ({page_count} pages) - Status: **Encrypted / Password Protected**")
        
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            start_search = st.button("🚀 Start Search", type="primary", use_container_width=True)
            
        if start_search:
            if estimated_total == 0:
                st.warning("Please configure candidate passwords in the sidebar first.")
            else:
                progress_bar = st.progress(0.0)
                status_placeholder = st.empty()
                
                # Stats grid
                stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
                with stat_col1:
                    tested_metric = st.empty()
                with stat_col2:
                    current_metric = st.empty()
                with stat_col3:
                    rate_metric = st.empty()
                with stat_col4:
                    elapsed_metric = st.empty()
                
                # Streamlit search runner
                reader = PdfReader(io.BytesIO(pdf_bytes))
                start_time = time.monotonic()
                tested = 0
                found_password = None
                
                generator = candidates_list if candidates_list is not None else lazy_generator
                
                last_ui_update = start_time
                status_placeholder.info("🔄 Search in progress...")
                
                for candidate in generator:
                    try:
                        is_match = reader.decrypt(candidate)
                    except Exception:
                        is_match = 0
                        
                    tested += 1
                    
                    if is_match:
                        found_password = candidate
                        break
                    
                    now = time.monotonic()
                    if (now - last_ui_update) >= 0.25 or (tested % 500 == 0):
                        elapsed = now - start_time
                        rate = tested / elapsed if elapsed > 0 else 0.0
                        pct = min(1.0, tested / estimated_total) if estimated_total > 0 else 0.0
                        
                        progress_bar.progress(pct)
                        tested_metric.metric("Tested", f"{tested:,}")
                        current_metric.metric("Current", candidate)
                        rate_metric.metric("Speed", f"{rate:,.0f}/sec")
                        elapsed_metric.metric("Elapsed", f"{elapsed:.1f}s")
                        last_ui_update = now
                
                elapsed_total = time.monotonic() - start_time
                progress_bar.progress(1.0 if found_password else min(1.0, tested / estimated_total if estimated_total > 0 else 1.0))
                
                if found_password:
                    status_placeholder.empty()
                    st.balloons()
                    st.markdown(
                        f"""
                        <div class="success-card">
                            <h3 style="color: #10b981; margin-top: 0;">🎉 Password Found!</h3>
                            <p style="font-size: 1.3rem; font-weight: bold; margin: 0.5rem 0;">Password: <span style="color: #38bdf8; background: #0f172a; padding: 4px 12px; border-radius: 6px; font-family: monospace;">{found_password}</span></p>
                            <p style="color: #94a3b8; margin: 0;">Checked <b>{tested:,}</b> candidates in <b>{elapsed_total:.2f} seconds</b> ({tested/elapsed_total if elapsed_total>0 else 0:,.0f} passwords/sec).</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    
                    # Generate unlocked PDF for instant download
                    unlocked_pdf_bytes = generate_decrypted_pdf(pdf_bytes, found_password)
                    if unlocked_pdf_bytes:
                        st.download_button(
                            label="⬇️ Download Unlocked (No Password) PDF",
                            data=unlocked_pdf_bytes,
                            file_name=f"unlocked_{uploaded_file.name}",
                            mime="application/pdf",
                            type="primary",
                        )
                else:
                    status_placeholder.warning(f"❌ Password not found among the {tested:,} tested candidates ({elapsed_total:.1f}s). Try expanding the range or choosing another mode in the sidebar.")
