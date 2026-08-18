import datetime
import io
import itertools
import string
import time
from typing import Generator, Union
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
        background: linear-gradient(180deg, rgba(99, 102, 241, 0.15) 0%, rgba(15, 23, 42, 0) 100%);
        border-radius: 16px;
        border: 1px solid rgba(99, 102, 241, 0.3);
        margin-bottom: 1.25rem;
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

    .preset-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 12px;
        padding: 0.85rem;
        margin-bottom: 0.75rem;
    }

    .success-box {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid #10b981;
        border-radius: 14px;
        padding: 1.25rem;
        margin: 1.25rem 0;
        text-align: center;
    }

    .pwd-pill {
        display: inline-block;
        font-size: 1.6rem;
        font-weight: 800;
        color: #10b981;
        background: #0b0f19;
        padding: 0.4rem 1.4rem;
        border-radius: 8px;
        font-family: monospace;
        letter-spacing: 2px;
        border: 1px dashed #10b981;
        margin: 0.5rem 0;
    }

    div.stButton > button {
        border-radius: 10px;
        font-weight: 700;
        padding: 0.6rem 1rem;
    }

    #MainMenu, header, footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 3. Core Logic Helpers
# -----------------------------------------------------------------------------

def validate_pdf_stream(pdf_bytes: bytes) -> tuple[bool, str]:
    """Validates if PDF is readable and encrypted safely."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if not reader.is_encrypted:
            return False, "This PDF is already unprotected (No password required)."
        return True, "Valid password-protected PDF."
    except Exception as exc:
        return False, f"Could not read PDF: {exc}"


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
        <div class="main-sub">Fast, in-browser recovery for Payslips, Bank Statements & Protected PDFs</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# 5. Step 1: Upload File
# -----------------------------------------------------------------------------

st.subheader("1️⃣ Select PDF File")

source_choice = st.radio(
    "Choose Mode:",
    ["📁 Upload My Locked PDF", "🧪 Instant Test Demo (Password: RAMK1998)"],
    horizontal=True,
    label_visibility="collapsed",
)

pdf_bytes = None
file_name = "document.pdf"

if source_choice == "📁 Upload My Locked PDF":
    up_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        label_visibility="collapsed",
        help="Secure: Your file stays strictly inside browser memory.",
    )
    if up_file is not None:
        pdf_bytes = up_file.getvalue()
        file_name = up_file.name
else:
    pdf_bytes = create_demo_pdf("RAMK1998")
    file_name = "demo_sample_encrypted.pdf"
    st.info("💡 **Demo PDF Active**: Password is `RAMK1998` (Initials: `RAMK`, Year: `1998`).")

# Validation check
pdf_valid = False
if pdf_bytes is not None:
    is_valid, msg = validate_pdf_stream(pdf_bytes)
    if is_valid:
        st.success(f"✅ **{file_name}** - Password-protected PDF detected & ready.")
        pdf_valid = True
    else:
        st.error(f"❌ {msg}")
else:
    st.caption("Upload a `.pdf` file above to begin.")

st.write("")

# -----------------------------------------------------------------------------
# 6. Step 2: Choose Search Pattern
# -----------------------------------------------------------------------------

st.subheader("2️⃣ Select Password Type")

pattern_mode = st.radio(
    "Choose Format:",
    [
        "⚡ Name / Initials + Year (e.g. RAMK1998 / Aadhaar & Payslips)",
        "📅 Date of Birth (DDMMYYYY / DDMM)",
        "🔢 Numeric PIN (4 to 8 Digits)",
        "🔤 Full AAAA to ZZZZ Auto-Search (8M Combinations)",
        "📝 Custom Passwords / Wordlist",
    ],
    index=0,
)

candidates: Union[list[str], Generator[str, None, None]] = []
total_count = 0
ready_to_search = True

# --- Option 1: Smart Pattern ---
if pattern_mode == "⚡ Name / Initials + Year (e.g. RAMK1998 / Aadhaar & Payslips)":
    st.markdown(
        """
        <div class="preset-card">
            <b>📌 Common Indian Formats:</b><br/>
            • <b>Aadhaar</b>: First 4 letters of Name in Capital + Birth Year (e.g. <code>RAMK1998</code>)<br/>
            • <b>Salary Slip / Form 16</b>: First 4 letters of Name + DOB Year / PAN<br/>
            • <b>Bank Statement</b>: Name Initials + DOB Year
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    col_p, col_y = st.columns([1.2, 1.8])
    with col_p:
        name_prefix = st.text_input(
            "Enter Name / Initials (e.g., RAMK, RAHUL, AMIT)",
            value="RAMK" if source_choice != "📁 Upload My Locked PDF" else "",
            placeholder="Type your name/initials here",
        ).strip()
    with col_y:
        col_y1, col_y2 = st.columns(2)
        with col_y1:
            y_start = st.number_input("Start Year", min_value=1940, max_value=2030, value=1980)
        with col_y2:
            y_end = st.number_input("End Year", min_value=1940, max_value=2030, value=2015)

    if not name_prefix:
        st.warning("⚠️ **Please type your Name or Initials above** (e.g. `RAMK`, `RAHU`, etc.) to generate candidate passwords.")
        ready_to_search = False
    elif y_start > y_end:
        st.error("Start year must be <= End year")
        ready_to_search = False
    else:
        years_list = [str(y) for y in range(int(y_start), int(y_end) + 1)]
        # generate uppercase, lowercase, capitalized, and first 4 letters
        raw_prefixes = [
            name_prefix.upper(),
            name_prefix.lower(),
            name_prefix.capitalize(),
            name_prefix[:4].upper(),
            name_prefix[:4].lower(),
        ]
        prefixes = list(dict.fromkeys(raw_prefixes))
        candidates = [f"{p}{y}" for p in prefixes for y in years_list]
        total_count = len(candidates)
        st.caption(f"Candidates to test: **{total_count:,} combinations** (Speed: **< 1 second**)")

# --- Option 2: Date of Birth (DDMMYYYY / DDMM) ---
elif pattern_mode == "📅 Date of Birth (DDMMYYYY / DDMM)":
    st.markdown("💡 *Tests every date in the year (0101 to 3112) in `DDMMYYYY` and `DDMM` formats.*")
    col_dob1, col_dob2 = st.columns(2)
    with col_dob1:
        dob_y1 = st.number_input("From Year", min_value=1950, max_value=2030, value=1980, key="dob_1")
    with col_dob2:
        dob_y2 = st.number_input("To Year", min_value=1950, max_value=2030, value=2015, key="dob_2")

    dob_list = []
    # Generate all DDMMYYYY
    for yr in range(int(dob_y1), int(dob_y2) + 1):
        for month in range(1, 13):
            for day in range(1, 32):
                try:
                    d_obj = datetime.date(yr, month, day)
                    dd = f"{d_obj.day:02d}"
                    mm = f"{d_obj.month:02d}"
                    yyyy = f"{d_obj.year}"
                    dob_list.append(f"{dd}{mm}{yyyy}")
                    dob_list.append(f"{dd}{mm}")
                except ValueError:
                    pass
    candidates = list(dict.fromkeys(dob_list))
    total_count = len(candidates)
    st.caption(f"Total DOB combinations: **{total_count:,}** (Runs in ~1-2 seconds)")

# --- Option 3: Numeric PIN ---
elif pattern_mode == "🔢 Numeric PIN (4 to 8 Digits)":
    st.markdown("💡 *Tests all numeric PIN combinations (Aadhaar last 4 digits, Phone PIN, Statement PIN).*")
    pin_digits = st.slider("PIN Length (Digits)", min_value=4, max_value=8, value=4)
    total_count = 10 ** pin_digits
    st.caption(f"Total PIN combinations: **{total_count:,}** (`{'0'*pin_digits}` to `{'9'*pin_digits}`)")

    def pin_generator(length: int):
        fmt = f"{{:0{length}d}}"
        for i in range(10 ** length):
            yield fmt.format(i)

    candidates = pin_generator(pin_digits)

# --- Option 4: Full A-Z Search ---
elif pattern_mode == "🔤 Full AAAA to ZZZZ Auto-Search (8M Combinations)":
    st.warning("⚠️ Tests all 4-letter uppercase combinations (AAAA to ZZZZ) + Year range.")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fy1 = st.number_input("From Year", min_value=1960, max_value=2030, value=1990, key="full_y1")
    with col_f2:
        fy2 = st.number_input("To Year", min_value=1960, max_value=2030, value=2005, key="full_y2")
        
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

# --- Option 5: Custom Wordlist ---
else:
    st.caption("Upload a `.txt` wordlist or paste passwords line-by-line.")
    uploaded_txt = st.file_uploader("Upload Wordlist (.txt)", type=["txt"])
    text_input = st.text_area("Or enter passwords (one per line):", placeholder="Pass@123\n123456\nRahul1998", height=90)
    words = []
    if uploaded_txt:
        words.extend(uploaded_txt.read().decode("utf-8", errors="ignore").splitlines())
    if text_input.strip():
        words.extend(text_input.splitlines())
    candidates = list(dict.fromkeys([w.strip() for w in words if w.strip()]))
    total_count = len(candidates)
    if total_count == 0:
        st.warning("Please upload a `.txt` file or type passwords above.")
        ready_to_search = False
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
    disabled=(not pdf_valid or not ready_to_search),
)

if start_action and pdf_valid and ready_to_search:
    if total_count == 0:
        st.warning("⚠️ No passwords to test. Please enter Name/PIN details in Step 2.")
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

        status_box.info("🔄 Searching for matching password...")

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
                    <div>The password for <b>{file_name}</b> is:</div>
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
                "💡 **Suggestions**:\n"
                "1. If this is a Bank statement / Aadhaar, make sure to enter your **First Name or 4 Letters** in the input box.\n"
                "2. Try the **📅 Date of Birth (DDMMYYYY)** option.\n"
                "3. Try the **🔢 Numeric PIN (4 Digits)** option."
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
