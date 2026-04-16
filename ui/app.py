"""BridgeAI - Streamlit Demo UI"""

import httpx
import streamlit as st

API_BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="BridgeAI", page_icon="🌉", layout="centered")
st.title("BridgeAI — Demo")
st.caption("AI-powered code analysis and User Story generation")

st.divider()

# --- Health check section ---
st.subheader("System Status")
user_input = st.text_input(
    "API Base URL",
    value=API_BASE_URL,
    help="Base URL of the running BridgeAI API",
)

if st.button("Check Health", type="primary"):
    with st.spinner("Connecting to API..."):
        try:
            response = httpx.get(f"{user_input.rstrip('/')}/health", timeout=5)
            response.raise_for_status()
            data = response.json()
            st.success("API is reachable!")
            st.json(data)
        except httpx.ConnectError:
            st.error("Could not connect to the API. Is the server running?")
        except httpx.HTTPStatusError as exc:
            st.error(f"API returned an error: {exc.response.status_code}")
            st.json(exc.response.json())
        except Exception as exc:  # noqa: BLE001
            st.error(f"Unexpected error: {exc}")

st.divider()

# --- Code Indexing section ---
st.subheader("Code Indexing")
force = st.checkbox("Force reindex", value=False, help="Reindex all files even if unchanged")

if st.button("Index Repository", type="primary"):
    with st.spinner("Indexing repository..."):
        try:
            response = httpx.post(
                f"{user_input.rstrip('/')}/api/v1/index",
                json={"force": force},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            st.success("Indexing complete!")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Scanned", data["files_scanned"])
            col2.metric("Indexed", data["files_indexed"])
            col3.metric("Updated", data["files_updated"])
            col4.metric("Skipped", data["files_skipped"])
            st.caption(f"Duration: {data['duration_seconds']:.2f}s | Request ID: {data['request_id']}")
        except httpx.ConnectError:
            st.error("Could not connect to the API. Is the server running?")
        except httpx.HTTPStatusError as exc:
            st.error(f"Indexing failed: {exc.response.json().get('detail', exc.response.status_code)}")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Unexpected error: {exc}")

st.divider()

# --- Impact Analysis section ---
st.subheader("Impact Analysis")
requirement_input = st.text_area(
    "Requirement",
    placeholder="Describe the functional change (e.g. 'Add email validation to user registration')",
    height=100,
)
project_id_input = st.text_input("Project ID", value="default")

if st.button("Analyze Impact", type="primary"):
    with st.spinner("Analyzing impact..."):
        try:
            response = httpx.post(
                f"{user_input.rstrip('/')}/api/v1/impact-analysis",
                json={"requirement": requirement_input, "project_id": project_id_input},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            risk = data["risk_level"]
            color = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red"}.get(risk, "gray")
            st.markdown(f"**Risk Level:** :{color}[{risk}]")
            col1, col2 = st.columns(2)
            col1.metric("Files Impacted", data["files_impacted"])
            col2.metric("Modules Impacted", data["modules_impacted"])
            st.caption(f"Duration: {data['duration_seconds']:.2f}s | Analysis ID: {data['analysis_id']}")
        except httpx.ConnectError:
            st.error("Could not connect to the API. Is the server running?")
        except httpx.HTTPStatusError as exc:
            st.error(f"Analysis failed: {exc.response.json().get('detail', exc.response.status_code)}")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Unexpected error: {exc}")

st.divider()
st.caption("BridgeAI MVP v0.1.0 · Powered by FastAPI + Streamlit")
