import io
import json
import requests
import streamlit as st


# -------------------------------
# CONFIG
# -------------------------------
st.set_page_config(
    page_title="Patient Report Intelligence",
    page_icon="🩺",
    layout="wide",
)

API_BASE_URL = "http://127.0.0.1:5001"


# -------------------------------
# SIDEBAR
# -------------------------------
st.sidebar.title("⚙️ Settings")

api_url = st.sidebar.text_input(
    "API base URL",
    API_BASE_URL,
    help="Flask backend URL (keep default if running locally)",
)

mode = st.sidebar.radio(
    "Analysis Mode",
    ["Analyze PDF (demo)", "Analyze JSON (debug)"],
    index=0,
)


st.sidebar.markdown("---")
st.sidebar.markdown("**Backend status:**")

# Quick health check
try:
    health_resp = requests.get(f"{api_url}/health", timeout=3)
    if health_resp.status_code == 200:
        st.sidebar.success("✅ API is running")
    else:
        st.sidebar.warning(f"⚠️ API responded with {health_resp.status_code}")
except Exception as e:
    st.sidebar.error("❌ Cannot reach API")
    st.sidebar.write(str(e))


st.title("🩺 Patient Report Intelligence – Demo UI")
st.markdown(
    "Upload lab reports and view AI-generated **patient-friendly** and "
    "**educational clinician** summaries with trends, escalation and references."
)


# -------------------------------
# HELPERS
# -------------------------------
def render_final_report(markdown_text: str):
    """Render the combined markdown report from the backend."""
    st.markdown(markdown_text)


def render_logs(logs):
    with st.expander("🔍 Debug Logs"):
        for line in logs:
            st.text(line)


def render_parsed_report(label: str, report_json: dict | None):
    if not report_json:
        return
    with st.expander(f"📄 Parsed {label} report (JSON)"):
        st.json(report_json)


# -------------------------------
# MODE 1: PDF MODE (DEMO)
# -------------------------------
if mode == "Analyze PDF (demo)":
    st.header("📑 Analyze PDF Reports")

    st.markdown(
        "For demo, use the **synthetic PDFs you generated via ReportLab** "
        "(e.g., `sample_report_current.pdf` and `sample_report_prev.pdf`)."
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

    if analyze_button:
        if not current_pdf:
            st.error("Please upload at least the current PDF report.")
        else:
            with st.spinner("Analyzing reports with backend..."):
                try:
                    files = {
                        "current_pdf": (current_pdf.name, current_pdf.getvalue(), "application/pdf")
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
                        timeout=60,
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

                        st.subheader("🧾 Final Report")
                        render_final_report(result.get("final_report", ""))

                        # Optional debug/technical views
                        render_parsed_report("current", result.get("current_report_parsed"))
                        render_parsed_report("previous", result.get("previous_report_parsed"))
                        render_logs(result.get("logs", []))

                except Exception as e:
                    st.error("Request to API failed.")
                    st.write(str(e))


# -------------------------------
# MODE 2: JSON MODE (DEBUG)
# -------------------------------
if mode == "Analyze JSON (debug)":
    st.header("🧪 Analyze JSON Payload")

    st.markdown(
        "Use this for debugging with the same JSON payload you send via `curl` "
        "to `/analyze-json`."
    )

    default_json = {
        "current_report": {
            "patient": {
                "external_id": "P001",
                "name": "Test Patient",
                "sex": "F",
                "dob": "1985-01-01"
            },
            "report_date": "2025-12-10",
            "tests": [
                {
                    "code": "HGB",
                    "name": "Hemoglobin",
                    "value": 8.1,
                    "unit": "g/dL",
                    "normal_range_low": 12.0,
                    "normal_range_high": 15.5,
                    "flag": "Low"
                },
                {
                    "code": "TSH",
                    "name": "TSH",
                    "value": 6.8,
                    "unit": "µIU/mL",
                    "normal_range_low": 0.4,
                    "normal_range_high": 4.0,
                    "flag": "High"
                }
            ]
        },
        "previous_report": {
            "patient": {
                "external_id": "P001",
                "name": "Test Patient",
                "sex": "F",
                "dob": "1985-01-01"
            },
            "report_date": "2025-11-01",
            "tests": [
                {
                    "code": "HGB",
                    "name": "Hemoglobin",
                    "value": 10.5,
                    "unit": "g/dL",
                    "normal_range_low": 12.0,
                    "normal_range_high": 15.5,
                    "flag": "Low"
                },
                {
                    "code": "TSH",
                    "name": "TSH",
                    "value": 3.2,
                    "unit": "µIU/mL",
                    "normal_range_low": 0.4,
                    "normal_range_high": 4.0,
                    "flag": "Normal"
                }
            ]
        }
    }

    json_text = st.text_area(
        "JSON payload for /analyze-json",
        value=json.dumps(default_json, indent=2),
        height=400,
    )

    if st.button("🔍 Analyze JSON"):
        try:
            payload = json.loads(json_text)
        except json.JSONDecodeError as e:
            st.error("Invalid JSON")
            st.write(str(e))
        else:
            with st.spinner("Calling /analyze-json..."):
                try:
                    resp = requests.post(
                        f"{api_url}/analyze-json",
                        json=payload,
                        timeout=60,
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

                        st.subheader("🧾 Final Report")
                        render_final_report(result.get("final_report", ""))

                        render_logs(result.get("logs", []))

                except Exception as e:
                    st.error("Request to API failed.")
                    st.write(str(e))
