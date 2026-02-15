import json
import requests
import streamlit as st
import pandas as pd
import io
import textwrap

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
except ImportError:
    st.error("""
    ❌ **Dependency Error: `reportlab` not found.**

    You are likely running Streamlit from the base environment instead of the project's virtual environment.

    **Please run the app using the helper script:**
    ```bash
    ./run_app.sh
    ```
    """)
    st.stop()


API_BASE_URL = "http://127.0.0.1:5001"

st.set_page_config(
    page_title="Patient Report Intelligence",
    page_icon="🩺",
    layout="wide",
)

# -------------------------------
# Sidebar: API + Health Check
# -------------------------------
st.sidebar.title("⚙️ Settings")

api_url = st.sidebar.text_input(
    "API base URL",
    API_BASE_URL,
    help="Flask backend URL (keep default if running locally)",
)

st.sidebar.info("🧠 Knowledge Source: **Hybrid** (Local Guidelines + Live Web Search)")
knowledge_source_value = "hybrid"

st.sidebar.markdown("---")
st.sidebar.markdown("**Backend status:**")
try:
    health_resp = requests.get(f"{api_url}/health", timeout=3)
    if health_resp.status_code == 200:
        st.sidebar.success("✅ API is running")
    else:
        st.sidebar.warning(f"⚠️ API responded with {health_resp.status_code}")
except Exception as e:
    st.sidebar.error("❌ Cannot reach API")
    st.sidebar.write(str(e))


# -------------------------------
# Main Title
# -------------------------------
st.title("🩺 Patient Report Intelligence – Demo UI")
st.markdown(
    "Upload lab report PDFs and view AI-generated summaries with trends, "
    "escalation, specialists, and references."
)


# -------------------------------
# Helpers
# -------------------------------
def _flag_style(val: str) -> str:
    if val in ("Low", "High"):
        return "color: red; font-weight: 700;"
    if val == "Normal":
        return "color: green; font-weight: 700;"
    return ""


def _escalation_style(val: str) -> str:
    if val == "Urgent":
        return "color: red; font-weight: 800;"
    if val == "Follow-up":
        return "color: orange; font-weight: 700;"
    if val == "Routine":
        return "color: green; font-weight: 700;"
    return ""


def _clinical_trend_style(val: str) -> str:
    if val == "Worsening":
        return "color: red; font-weight: 800;"
    if val == "Improving":
        return "color: green; font-weight: 800;"
    if val == "Stable":
        return "color: #666; font-weight: 700;"
    return ""


def render_tests_table(label: str, report: dict | None):
    if not report:
        return
    tests = report.get("tests", [])
    if not tests:
        return

    st.subheader(f"🧪 Extracted Tests – {label}")

    df = pd.DataFrame(
        [
            {
                "Code": t.get("code"),
                "Test Name": t.get("name"),
                "Value": t.get("value"),
                "Unit": t.get("unit"),
                "Normal Low": t.get("normal_range_low"),
                "Normal High": t.get("normal_range_high"),
                "Flag": t.get("flag"),
            }
            for t in tests
        ]
    )

    styled = df.style.applymap(_flag_style, subset=["Flag"])
    st.dataframe(styled, use_container_width=True)


def render_logs(logs: list[str] | None):
    if not logs:
        return
    with st.expander("🔍 Debug Logs (tool & node execution)"):
        for line in logs:
            st.text(line)


def render_parsed_json(label: str, report: dict | None):
    if not report:
        return
    with st.expander(f"📄 Parsed {label} report JSON"):
        st.json(report)


def create_report_pdf(final_report_text: str, patient_name: str, patient_id: str) -> io.BytesIO:
    """
    Create a simple PDF from the final_report markdown text.
    Plain text, wrapped, demo friendly.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin = 20 * mm
    y = height - margin

    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, y, "Patient Report Intelligence – Summary")
    y -= 20

    c.setFont("Helvetica", 10)
    if patient_name:
        c.drawString(margin, y, f"Patient: {patient_name}")
        y -= 12
    if patient_id:
        c.drawString(margin, y, f"Patient ID: {patient_id}")
        y -= 12

    y -= 8

    # Body – wrap text
    c.setFont("Helvetica", 10)
    paragraphs = final_report_text.split("\n\n")
    for para in paragraphs:
        clean_para = para.replace("### ", "").replace("## ", "").replace("# ", "")
        lines = textwrap.wrap(clean_para, width=100)

        for line in lines:
            if y < margin:
                c.showPage()
                y = height - margin
                c.setFont("Helvetica", 10)
            c.drawString(margin, y, line)
            y -= 12

        y -= 6

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def render_analysis_table_with_trends(analysis: list[dict] | None):
    """
    STEP 7E:
      - Trend Table with direction + clinical_trend
      - Styled flags + escalation + clinical_trend
    """
    if not analysis:
        return

    st.subheader("📊 Abnormal Test Analysis (with Clinical Trends)")

    rows = []
    for row in analysis:
        rows.append(
            {
                "Code": row.get("code"),
                "Test Name": row.get("name"),
                "Current": row.get("current_value"),
                "Prev": row.get("previous_value"),
                "Unit": row.get("unit"),
                "Flag": row.get("current_flag"),
                "Direction": row.get("direction"),               # up/down/stable
                "Clinical Trend": row.get("clinical_trend"),     # Improving/Worsening/Stable/Unknown
                "Escalation": row.get("escalation_level"),
                "Specialists": ", ".join(row.get("specialists", [])),
            }
        )

    df = pd.DataFrame(rows)

    styled = (
        df.style
        .applymap(_flag_style, subset=["Flag"])
        .applymap(_escalation_style, subset=["Escalation"])
        .applymap(_clinical_trend_style, subset=["Clinical Trend"])
    )

    st.dataframe(styled, use_container_width=True)


def render_correlations(correlations: str):
    """
    Renders the cross-test correlation section.
    """
    if not correlations:
        return
    
    st.subheader("🔗 Potential Correlations")
    st.info(correlations)


def render_action_plan(action_plan: str):
    """
    Renders the actionable next steps section.
    """
    if not action_plan:
        return
    
    st.subheader("📝 Actionable Next Steps")
    st.markdown(action_plan)


def render_medication_analysis(medication_analysis: str):
    """
    Renders the medication insights section.
    """
    if not medication_analysis:
        return
    
    st.subheader("💊 Medication & Risk Insights")
    st.info(medication_analysis)


def render_dietary_plan(dietary_plan: str):
    """
    Renders the Personalized 3-Day Meal Plan.
    """
    if not dietary_plan:
        return
    
    with st.expander("🥗 Personalized 3-Day Meal Plan", expanded=True):
        st.markdown(dietary_plan)


def render_mini_charts_from_analysis(analysis: list[dict] | None):
    """
    STEP 7E mini charts:
      Uses analysis[*].series_last_5 (list of {date,value,unit})
    """
    if not analysis:
        return

    st.subheader("📈 Mini Trend Charts (Last 5 values)")

    for row in analysis:
        code = row.get("code")
        name = row.get("name") or code
        series = row.get("series_last_5") or []

        series_clean = [x for x in series if x.get("value") is not None and x.get("date")]
        if len(series_clean) < 2:
            continue

        df = pd.DataFrame(series_clean)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")

        unit = None
        if len(df) > 0:
            unit = df.iloc[-1].get("unit")

        # Compact layout
        with st.expander(f"{name} ({code}) trend", expanded=True):
            st.caption(
                f"Clinical trend: **{row.get('clinical_trend','Unknown')}**, "
                f"Short: **{row.get('direction','Unknown')}**, "
                f"Long: **{row.get('direction_long','Unknown')}** "
                f"(net {row.get('net_change','')})"
            )
            st.line_chart(df.set_index("date")["value"])
            if unit:
                st.caption(f"Unit: {unit}")


def render_citations(citations: list[dict] | None):
    """
    Renders the global citations list returned by the API.
    Expected shape: [{"ref_id": 1, "title": "...", "url": "...", "snippet": "..."}]
    """
    if not citations:
        st.info("No citations received from backend.")
        return

    st.subheader("📚 References / Citations")

    rows = []
    for c in citations:
        rows.append({
            "Ref": c.get("ref_id"),
            "Title": c.get("title"),
            "URL": c.get("url"),
            "Snippet": (c.get("snippet") or "")[:250],
        })

    df = pd.DataFrame(rows).sort_values("Ref")

    # Show clickable links
    st.dataframe(df, use_container_width=True)

    # Optional: pretty list format too
    with st.expander("🔗 Clickable reference list"):
        for c in sorted(citations, key=lambda x: x.get("ref_id", 0)):
            rid = c.get("ref_id")
            title = c.get("title", "Source")
            url = c.get("url", "")
            snippet = (c.get("snippet") or "").strip()
            if url:
                st.markdown(f"**[Ref {rid}]** [{title}]({url})")
            else:
                st.markdown(f"**[Ref {rid}]** {title}")
            if snippet:
                st.caption(snippet)


# -------------------------------
# Upload Section
# -------------------------------
st.header("📑 Analyze PDF Reports")
st.markdown(
    "For demo, use the synthetic PDFs you generated "
    "(e.g., `sample_report_current.pdf` and `sample_report_prev.pdf`)."
)

col1, col2 = st.columns(2)


with col1:
    current_pdf = st.file_uploader(
        "Current report PDF (required)",
        type=["pdf"],
        key="current_pdf",
    )
    # previous_pdf = st.file_uploader(
    #     "Previous report PDF (optional, for trends)",
    #     type=["pdf"],
    #     key="previous_pdf",
    # )

with col2:
    st.subheader("Patient metadata")
    patient_id = st.text_input("Patient ID", "P001")
    patient_name = st.text_input("Patient Name", "Test Patient")
    sex = st.selectbox("Sex", ["F", "M"], index=0)
    dob = st.text_input("DOB (YYYY-MM-DD)", "1985-01-01")
    current_date = st.text_input("Current report date (YYYY-MM-DD)", "2025-12-10")
    # previous_date = st.text_input("Previous report date (YYYY-MM-DD, optional)", "2025-11-01")

# -------------------------------
# Patient Profile (Load/Save)
# -------------------------------
with st.expander("📝 Patient Context (Medications & History)", expanded=False):
    # Load / Save buttons
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("📂 Load Profile (by Patient ID)"):
            try:
                resp = requests.get(f"{api_url}/patient-profile", params={"patient_id": patient_id}, timeout=5)
                if resp.status_code == 200:
                    prof = resp.json()
                    # Directly update the widget keys to force refresh
                    st.session_state["meds_input_key"] = prof.get("medications", "")
                    st.session_state["hist_input_key"] = prof.get("medical_history", "")
                    st.success("Profile Loaded!")
                    st.rerun()  # Rerun to show new values immediately
                else:
                    st.error("Profile not found or error.")
            except Exception as e:
                st.error(f"Load failed: {e}")

    # Layout inputs
    medications_input = st.text_area(
        "Current Medications (comma separated)", 
        help="E.g. Atorvastatin, Metformin, Vitamin D",
        key="meds_input_key"
    )
    history_input = st.text_area(
        "Medical History", 
        help="E.g. Type 2 Diabetes, Hypertension, Family history of Thyroid cancer",
        key="hist_input_key"
    )

    with c2:
        if st.button("💾 Save Profile"):
            try:
                payload = {
                    "patient_id": patient_id,
                    "medications": medications_input,
                    "medical_history": history_input
                }
                resp = requests.post(f"{api_url}/patient-profile", json=payload, timeout=5)
                if resp.status_code == 200:
                    st.success("Profile Saved!")
                else:
                    st.error(f"Save failed: {resp.text}")
            except Exception as e:
                st.error(f"Save failed: {e}")

analyze_button = st.button("🔍 Analyze PDF")


# -------------------------------
# Call backend on click
# -------------------------------
# -------------------------------
# Call backend on click
# -------------------------------
if analyze_button:
    if not current_pdf:
        st.error("Please upload at least the current report PDF.")
    else:
        with st.spinner("Analyzing reports with backend..."):
            try:
                files = {
                    "current_pdf": (current_pdf.name, current_pdf.getvalue(), "application/pdf")
                }

                data = {
                    "patient_id": patient_id,
                    "patient_name": patient_name,
                    "sex": sex,
                    "dob": dob,
                    "current_date": current_date,
                    "knowledge_source": knowledge_source_value,
                    "medications": medications_input,
                    "medical_history": history_input,
                }

                resp = requests.post(
                    f"{api_url}/analyze-pdf",
                    files=files,
                    data=data,
                    timeout=300,
                )

                if resp.status_code != 200:
                    st.error(f"API error: {resp.status_code}")
                    try:
                        st.json(resp.json())
                    except Exception:
                        st.write(resp.text)
                else:
                    # SUCCESS: Store result in session state
                    st.session_state["analysis_result"] = resp.json()
                    st.success("Analysis complete ✅")
                    
                    # Clear old chat history on new analysis
                    st.session_state["chat_history"] = []

            except Exception as e:
                st.error("Request to API failed.")
                st.write(str(e))

# -------------------------------
# Render Report if Data Exists
# -------------------------------
if "analysis_result" in st.session_state:
    result = st.session_state["analysis_result"]

    # Final report
    st.subheader("🧾 Final Report")
    final_report = result.get("final_report", "")
    st.markdown(final_report)
    render_citations(result.get("citations", []))

    # Download as PDF button
    if final_report:
        pdf_bytes = create_report_pdf(final_report, patient_name, patient_id)
        st.download_button(
            label="⬇️ Download report as PDF",
            data=pdf_bytes,
            file_name=f"patient_report_{patient_id}.pdf",
            mime="application/pdf",
        )

    # STEP 7E: Trend table + mini charts from analysis
    analysis = result.get("analysis", [])
    render_analysis_table_with_trends(analysis)
    
    # NEW: Correlations
    render_correlations(result.get("correlations"))
    
    # NEW: Action Plan
    render_action_plan(result.get("action_plan"))
    
    # NEW: Medication Analysis
    render_medication_analysis(result.get("medication_analysis"))
    
    # NEW: Dietary Plan
    render_dietary_plan(result.get("dietary_plan"))
    
    render_mini_charts_from_analysis(analysis)

    # Extracted tests tables
    current_parsed = result.get("current_report_parsed")
    render_tests_table("Current", current_parsed)

    # Optional: show raw parsed JSON + logs
    render_parsed_json("current", current_parsed)
    render_logs(result.get("logs", []))

    # ----------------------------------------------------
    #  NEW: Evaluation / Feedback Loop (RLHF)
    # ----------------------------------------------------
    st.markdown("---") 
    st.subheader("📝 Report Evaluation")
    st.caption("Help us improve the Medical AI by rating this report.")
    
    # Generate a pseudo-ID for this session's report
    report_id = f"report_{patient_id}_{current_date}"
    
    # Thumbs up=1, Thumbs down=0. Using 'thumbs' feedback.
    feedback = st.feedback("thumbs")
    
    if feedback is not None:
        # feedback is 1 (up) or 0 (down)
        rating_str = "thumbs_up" if feedback == 1 else "thumbs_down"
        try:
            fb_payload = {"report_id": report_id, "rating": rating_str}
            fb_resp = requests.post(f"{api_url}/submit-feedback", json=fb_payload, timeout=5)
            if fb_resp.status_code == 200:
                st.toast(f"Thank you for your feedback! ({rating_str})")
            else:
                st.error("Failed to save feedback.")
        except Exception as e:
            st.error(f"Feedback error: {e}")

    # ----------------------------------------------------
    #  NEW: Chat with your Health Data Agent
    # ----------------------------------------------------
    st.markdown("---")
    st.subheader("💬 Chat with your Health Data")
    st.caption("Ask questions about these results, trends, or what they mean for your health.")

    # Initialize chat history
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Display chat history
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if user_input := st.chat_input("Ex: Is my hemoglobin improving?"):
        # 1. Display user message
        st.session_state["chat_history"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # 2. Call API
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    payload = {
                        "history": st.session_state["chat_history"],
                        # We pass the full analysis data as context
                        "context": result
                    }
                    chat_resp = requests.post(f"{api_url}/chat", json=payload, timeout=60)
                    if chat_resp.status_code == 200:
                        answer = chat_resp.json().get("response", "No response text.")
                        st.markdown(answer)
                        st.session_state["chat_history"].append({"role": "assistant", "content": answer})
                    else:
                        st.error(f"Error {chat_resp.status_code}: {chat_resp.text}")
                except Exception as e:
                    st.error(f"Failed to connect to chat agent: {e}")
