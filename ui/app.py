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

# --- Requirement Understanding section ---
st.subheader("Requirement Understanding")
req_understanding_input = st.text_area(
    "Requirement",
    placeholder="Describe the functional requirement in natural language (e.g. 'The user must be able to register with email and password')",
    height=100,
    key="req_understanding",
)
req_understanding_project_id = st.text_input("Project ID", value="my-project", key="req_understanding_project_id")

if st.button("Understand Requirement", type="primary"):
    with st.spinner("Analyzing requirement..."):
        try:
            response = httpx.post(
                f"{user_input.rstrip('/')}/api/v1/understand-requirement",
                json={"requirement": req_understanding_input, "project_id": req_understanding_project_id},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            st.success("Requirement understood!")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Intent:** `{data['intent']}`")
                st.markdown(f"**Feature Type:** `{data['feature_type']}`")
                complexity = data["estimated_complexity"]
                color = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red"}.get(complexity, "gray")
                st.markdown(f"**Complexity:** :{color}[{complexity}]")
            with col2:
                keywords = data.get("keywords", [])
                if keywords:
                    st.markdown("**Keywords:**")
                    st.code(", ".join(keywords))
            st.caption(
                f"Processing time: {data['processing_time_seconds']:.3f}s "
                f"| Requirement ID: {data['requirement_id']}"
            )
        except httpx.ConnectError:
            st.error("Could not connect to the API. Is the server running?")
        except httpx.HTTPStatusError as exc:
            st.error(f"Understanding failed: {exc.response.json().get('detail', exc.response.status_code)}")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Unexpected error: {exc}")

st.divider()

# --- Story Generation section ---
st.subheader("Story Generation")
req_id_input = st.text_input(
    "Requirement ID",
    placeholder="UUID del requirement generado en la sección anterior",
    key="story_req_id",
)
analysis_id_input = st.text_input(
    "Impact Analysis ID",
    placeholder="UUID del análisis generado anteriormente",
    key="story_analysis_id",
)
story_project_id = st.text_input("Project ID", value="my-project", key="story_project_id")

if st.button("Generate Story", type="primary"):
    if not req_id_input or not analysis_id_input:
        st.warning("Please provide both Requirement ID and Impact Analysis ID.")
    else:
        with st.spinner("Generating user story..."):
            try:
                response = httpx.post(
                    f"{user_input.rstrip('/')}/api/v1/generate-story",
                    json={
                        "requirement_id": req_id_input,
                        "impact_analysis_id": analysis_id_input,
                        "project_id": story_project_id,
                    },
                    timeout=60,
                )
                if response.status_code == 404:
                    st.error(response.json().get("detail", "Not found"))
                else:
                    response.raise_for_status()
                    data = response.json()
                    st.success("Story generated!")
                    st.markdown(f"## {data['title']}")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Story Points", data["story_points"])
                        risk = data["risk_level"]
                        color = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red"}.get(risk, "gray")
                        st.markdown(f"**Risk Level:** :{color}[{risk}]")
                    with col2:
                        st.caption(f"Generation time: {data['generation_time_seconds']:.3f}s")
                        st.caption(f"Story ID: {data['story_id']}")

                    st.session_state["last_story_id"] = data["story_id"]

            except httpx.ConnectError:
                st.error("Could not connect to the API. Is the server running?")
            except httpx.HTTPStatusError as exc:
                st.error(f"Story generation failed: {exc.response.json().get('detail', exc.response.status_code)}")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Unexpected error: {exc}")

st.divider()

# --- Ticket Creation section ---
st.subheader("Create Ticket")

_PROVIDER_LABELS = {"Jira": "jira", "Azure DevOps": "azure_devops"}
_PROVIDER_HELP = {
    "jira": "Requires JIRA_BASE_URL, JIRA_USER_EMAIL and JIRA_API_TOKEN in the API .env",
    "azure_devops": "Requires AZURE_ORG_URL, AZURE_PROJECT and AZURE_DEVOPS_TOKEN in the API .env",
}

default_story_id = st.session_state.get("last_story_id", "")
ticket_story_id = st.text_input(
    "Story ID",
    value=default_story_id,
    placeholder="UUID of the generated story",
    key="ticket_story_id",
)

col_prov, col_type = st.columns(2)
with col_prov:
    selected_provider_label = st.selectbox(
        "Provider",
        options=list(_PROVIDER_LABELS.keys()),
        key="ticket_provider",
    )
with col_type:
    ticket_issue_type = st.selectbox(
        "Issue Type",
        options=["Story", "Task", "Bug", "Epic"],
        key="ticket_issue_type",
    )

selected_provider = _PROVIDER_LABELS[selected_provider_label]
st.caption(_PROVIDER_HELP[selected_provider])

if selected_provider == "jira":
    ticket_project_key = st.text_input(
        "Jira Project Key", value="PROJ", key="ticket_project_key"
    )
else:
    ticket_project_key = st.text_input(
        "Azure DevOps Project (used as key)", value="", key="ticket_project_key",
        placeholder="Leave empty — project is set via AZURE_PROJECT in .env",
    )

if st.button("Create Ticket", type="primary"):
    if not ticket_story_id:
        st.warning("Please provide a Story ID.")
    else:
        spinner_label = f"Creating {selected_provider_label} ticket..."
        with st.spinner(spinner_label):
            try:
                response = httpx.post(
                    f"{user_input.rstrip('/')}/api/v1/tickets",
                    json={
                        "story_id": ticket_story_id,
                        "integration_type": selected_provider,
                        "project_key": ticket_project_key or "default",
                        "issue_type": ticket_issue_type,
                    },
                    timeout=30,
                )
                if response.status_code in (200, 201):
                    data = response.json()
                    is_duplicate = response.status_code == 200 and data.get("message")
                    if is_duplicate:
                        st.info(f"Ticket already exists: **{data['ticket_id']}**")
                    else:
                        st.success(f"Ticket created: **{data['ticket_id']}**")
                    col1, col2, col3 = st.columns(3)
                    col1.markdown(f"**Provider:** `{data['provider']}`")
                    col2.markdown(f"**Status:** `{data['status']}`")
                    if data.get("url"):
                        link_label = "Open in Jira" if selected_provider == "jira" else "Open in Azure DevOps"
                        col3.markdown(f"[{link_label}]({data['url']})")
                elif response.status_code == 404:
                    st.error(f"Story not found: {response.json().get('detail')}")
                elif response.status_code == 502:
                    detail = response.json().get("detail", {})
                    st.error(f"Integration error: {detail.get('error', 'Unknown error')}")
                    if not detail.get("retryable", True):
                        st.warning(
                            f"This error is not retryable. Check your {selected_provider_label} credentials."
                        )
                else:
                    response.raise_for_status()
            except httpx.ConnectError:
                st.error("Could not connect to the API. Is the server running?")
            except httpx.HTTPStatusError as exc:
                st.error(f"Ticket creation failed: {exc.response.json().get('detail', exc.response.status_code)}")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Unexpected error: {exc}")

st.divider()

# --- Integration Health section ---
if st.button("Check Integration Health"):
    with st.spinner("Checking integrations..."):
        try:
            response = httpx.get(
                f"{user_input.rstrip('/')}/api/v1/integration/health",
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            _provider_labels = {"jira": "Jira", "azure_devops": "Azure DevOps"}
            for provider, health_status in data.items():
                color = {
                    "healthy": "green",
                    "unhealthy": "red",
                    "not_configured": "orange",
                }.get(health_status, "gray")
                label = _provider_labels.get(provider, provider)
                st.markdown(f"**{label}:** :{color}[{health_status}]")
        except httpx.ConnectError:
            st.error("Could not connect to the API.")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Unexpected error: {exc}")

st.divider()
st.caption("BridgeAI MVP v0.1.0 · Powered by FastAPI + Streamlit")
