import json
import requests
import streamlit as st
import pandas as pd
import io
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
import textwrap




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
    "escalation, and references."
)

# -------------------------------
# Helpers
# -------------------------------
def render_tests_table(label: str, report: dict | None):
    if not report:
        return
    tests = report.get("tests", [])
    if not tests:
        return

    st.subheader(f"🧪 Extracted Tests – {label}")

    df_rows = []
    for t in tests:
        df_rows.append(
            {
                "Code": t.get("code"),
                "Test Name": t.get("name"),
                "Value": t.get("value"),
                "Unit": t.get("unit"),
                "Normal Low": t.get("normal_range_low"),
                "Normal High": t.get("normal_range_high"),
                "Flag": t.get("flag"),
            }
        )

    df = pd.DataFrame(df_rows)

    def color_flags(val):
        if val == "Low" or val == "High":
            return "color: red; font-weight: 600;"
        if val == "Normal":
            return "color: green; font-weight: 600;"
        return ""

    styled = df.style.applymap(color_flags, subset=["Flag"])

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
    We keep it plain text, nicely wrapped, for demo.
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
        # strip markdown headings (###) just for PDF aesthetics
        clean_para = para.replace("### ", "").replace("## ", "").replace("# ", "")
        lines = textwrap.wrap(clean_para, width=100)

        for line in lines:
            if y < margin:  # new page
                c.showPage()
                y = height - margin
                c.setFont("Helvetica", 10)
            c.drawString(margin, y, line)
            y -= 12

        y -= 6  # extra gap between paragraphs

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

def render_analysis_table(analysis: list[dict] | None):
    if not analysis:
        return
    st.subheader("📊 Analysis of Abnormal Tests")

    rows = []
    for row in analysis:
        rows.append(
            {
                "Code": row.get("code"),
                "Test Name": row.get("name"),
                "Current Value": row.get("current_value"),
                "Prev Value": row.get("previous_value"),
                "Unit": row.get("unit"),
                "Flag": row.get("current_flag"),
                "Trend": row.get("trend"),
                "Escalation": row.get("escalation_level"),
                "Specialists": ", ".join(row.get("specialists", [])),
            }
        )

    df = pd.DataFrame(rows)

    def color_flag(val):
        if val == "Low" or val == "High":
            return "color: red; font-weight: 600;"
        if val == "Normal":
            return "color: green; font-weight: 600;"
        return ""

    def color_escalation(val):
        if val == "Urgent":
            return "color: red; font-weight: 700;"
        if val == "Follow-up":
            return "color: orange; font-weight: 600;"
        if val == "Routine":
            return "color: green; font-weight: 600;"
        return ""

    styled = (
        df.style
        .applymap(color_flag, subset=["Flag"])
        .applymap(color_escalation, subset=["Escalation"])
    )

    st.dataframe(styled, use_container_width=True)



# -------------------------------
# Upload Section
# -------------------------------
st.header("📑 Analyze PDF Reports")

st.markdown(
    "For demo, use the synthetic PDFs you generated (e.g., "
    "`sample_report_current.pdf` and `sample_report_prev.pdf`)."
)

col1, col2 = st.columns(2)

with col1:
    current_pdf = st.file_uploader(
        "Current report PDF (required)",
        type=["pdf"],
        key="current_pdf",
    )
    previous_pdf = st.file_uploader(
        "Previous report PDF (optional, for trends)",
        type=["pdf"],
        key="previous_pdf",
    )

with col2:
    st.subheader("Patient metadata")
    patient_id = st.text_input("Patient ID", "P001")
    patient_name = st.text_input("Patient Name", "Test Patient")
    sex = st.selectbox("Sex", ["F", "M"], index=0)
    dob = st.text_input("DOB (YYYY-MM-DD)", "1985-01-01")
    current_date = st.text_input("Current report date (YYYY-MM-DD)", "2025-12-10")
    previous_date = st.text_input(
        "Previous report date (YYYY-MM-DD, optional)",
        "2025-11-01",
    )

analyze_button = st.button("🔍 Analyze PDF")


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
                    "current_pdf": (
                        current_pdf.name,
                        current_pdf.getvalue(),
                        "application/pdf",
                    )
                }
                if previous_pdf:
                    files["previous_pdf"] = (
                        previous_pdf.name,
                        previous_pdf.getvalue(),
                        "application/pdf",
                    )

                data = {
                    "patient_id": patient_id,
                    "patient_name": patient_name,
                    "sex": sex,
                    "dob": dob,
                    "current_date": current_date,
                }
                if previous_pdf:
                    data["previous_date"] = previous_date

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
                    result = resp.json()
                    st.success("Analysis complete ✅")

                    # Final report
                    st.subheader("🧾 Final Report")
                    final_report = result.get("final_report", "")
                    st.markdown(final_report)

                    # Download as PDF button (if we have a report)
                    if final_report:
                        pdf_bytes = create_report_pdf(final_report, patient_name, patient_id)
                        st.download_button(
                            label="⬇️ Download report as PDF",
                            data=pdf_bytes,
                            file_name=f"patient_report_{patient_id}.pdf",
                            mime="application/pdf",
                        )

                    
                    # New: structured analysis table
                    analysis = result.get("analysis", [])
                    render_analysis_table(analysis)

                    # Extracted tests tables
                    current_parsed = result.get("current_report_parsed")
                    previous_parsed = result.get("previous_report_parsed")
                    render_tests_table("Current", current_parsed)
                    render_tests_table("Previous", previous_parsed)

                    # Optional: show raw parsed JSON + logs
                    render_parsed_json("current", current_parsed)
                    render_parsed_json("previous", previous_parsed)
                    render_logs(result.get("logs", []))


            except Exception as e:
                st.error("Request to API failed.")
                st.write(str(e))
