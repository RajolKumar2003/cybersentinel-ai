"""
CyberSentinel AI — Streamlit Security Operations Dashboard.

Talks only to the FastAPI backend's REST API (never touches the database
directly), so this file works unmodified against a locally-run backend or
a deployed one — just change API_BASE_URL.

Run locally (after `pip install -r frontend/requirements.txt` and with the
backend running separately):
    streamlit run frontend/app.py

This file could not be executed in the development sandbox (streamlit is
not installed there, no network to install it) — run it locally first and
fix anything that surfaces before treating it as done.
"""
from __future__ import annotations

import os

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="CyberSentinel AI", page_icon="🛡️", layout="wide")

# --- Embedded-backend mode (for Streamlit Community Cloud) -----------------
# Streamlit Cloud only runs one process and exposes one port, so it can't
# host a separate FastAPI server the way local dev or a real deployment
# does. Setting CYBERSENTINEL_EMBEDDED_BACKEND=1 (as a Streamlit Cloud
# secret/env var) starts the real, unmodified FastAPI backend in a
# background thread inside this same process — see backend_runner.py for
# why this doesn't compromise the architecture. Local development is
# unaffected: without this env var set, behavior is exactly as before
# (point CYBERSENTINEL_API_URL at a separately-running backend, or default
# to localhost:8000).
if os.environ.get("CYBERSENTINEL_EMBEDDED_BACKEND") == "1":
    from backend_runner import start_backend

    with st.spinner("Starting backend (first load trains the ML models — can take ~30-60s)..."):
        API_BASE_URL = start_backend()
else:
    API_BASE_URL = os.environ.get("CYBERSENTINEL_API_URL", "http://localhost:8000/api/v1")
st.markdown(
    """
    <style>
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stMetricValue"] { font-size: 1.7rem; font-weight: 700; }
    .severity-critical { color: #ef4444; font-weight: 700; }
    .severity-high { color: #f97316; font-weight: 700; }
    .severity-medium { color: #eab308; font-weight: 600; }
    .severity-low { color: #22c55e; font-weight: 600; }
    .evidence-box { background: #111827; border-radius: 8px; padding: 0.9rem 1.1rem; margin-bottom: 0.6rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def api_get(path: str, **params):
    try:
        resp = requests.get(f"{API_BASE_URL}{path}", params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"Could not reach the backend API at {API_BASE_URL}{path}: {e}")
        return None


def api_post(path: str, json_body: dict | None = None):
    try:
        resp = requests.post(f"{API_BASE_URL}{path}", json=json_body or {}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"Request to {API_BASE_URL}{path} failed: {e}")
        return None


def severity_badge(severity: str) -> str:
    return f'<span class="severity-{severity}">{severity.upper()}</span>'


# --- Sidebar navigation ------------------------------------------------------
st.sidebar.title("🛡️ CyberSentinel AI")
st.sidebar.caption("Agentic Network Security Investigation & Response Platform")
page = st.sidebar.radio(
    "Navigate",
    [
        "Dashboard", "Incidents", "Incident Details", "AI Investigation",
        "RAG Knowledge Base", "ML Model Performance", "Recommendations",
        "Audit Logs", "System Health",
    ],
)
st.sidebar.divider()
st.sidebar.caption(
    "⚠️ AI output here is a recommendation, not guaranteed truth. Every "
    "response action requires explicit human approval before it is applied "
    "to the (simulated) environment."
)

# --- Pages --------------------------------------------------------------------
if page == "Dashboard":
    st.title("Security Operations Dashboard")
    metrics = api_get("/metrics")
    if metrics:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Incidents", metrics["total_incidents"])
        c2.metric("Critical Incidents", metrics["critical_incidents"])
        c3.metric("Anomalies Detected", metrics["anomaly_count"])
        c4.metric("Resolved Incidents", metrics["resolved_incidents"])

        avg_time = metrics.get("average_investigation_time_seconds")
        st.metric(
            "Avg. Investigation Time",
            f"{avg_time:.1f}s" if avg_time is not None else "No completed investigations yet",
        )

        st.subheader("Anomaly Detector Performance (demo data)")
        det = metrics.get("detector_metrics") or {}
        if det:
            rows = []
            for name, m in det.items():
                rows.append({"Model": name, "Precision": m["precision"], "Recall": m["recall"],
                             "F1": m["f1"], "False Positive Rate": m["false_positive_rate"]})
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
            st.caption(next(iter(det.values())).get("note", ""))
        else:
            st.info("No evaluation report found. Run `python ml/train_anomaly_models.py`.")

elif page == "Incidents":
    st.title("Incidents")
    status_filter = st.selectbox("Filter by status", ["(all)", "open", "investigating", "resolved", "closed"])
    incidents = api_get("/incidents", **({"status": status_filter} if status_filter != "(all)" else {}))
    if incidents:
        df = pd.DataFrame(incidents)
        st.dataframe(
            df[["incident_id", "severity", "source", "affected_service", "status", "investigation_status", "anomaly_score"]],
            use_container_width=True,
        )
        st.session_state["incident_ids"] = df["incident_id"].tolist()
    else:
        st.info("No incidents yet. Ingest events via POST /api/v1/events to generate some.")

elif page == "Incident Details":
    st.title("Incident Details")
    incident_id = st.text_input("Incident ID", value=st.session_state.get("selected_incident", ""))
    if incident_id:
        incident = api_get(f"/incidents/{incident_id}")
        if incident:
            st.markdown(f"### {incident['incident_id']} — {severity_badge(incident['severity'])}", unsafe_allow_html=True)
            st.write(f"**Source:** {incident['source']}  |  **Service:** {incident['affected_service']}")
            st.write(f"**Anomaly score:** {incident['anomaly_score']:.3f}")
            st.write(f"**Status:** {incident['status']}  |  **Investigation:** {incident['investigation_status']}")
            st.write("**Event summary:**", incident["event_summary"])

            if st.button("Run AI Investigation", type="primary", disabled=incident["investigation_status"] == "completed"):
                with st.spinner("Running 5-agent investigation pipeline..."):
                    result = api_post(f"/incidents/{incident_id}/investigate")
                if result:
                    st.success("Investigation completed.")
                    st.rerun()

elif page == "AI Investigation":
    st.title("AI Investigation")
    incident_id = st.text_input("Incident ID to view investigation for")
    if incident_id:
        investigation = api_get(f"/incidents/{incident_id}/investigation")
        if investigation:
            st.subheader("Root Cause")
            st.write(f"**{investigation['root_cause']}** — confidence "
                     f"{investigation['root_cause_confidence']:.0%}" if investigation["root_cause_confidence"] else "Not yet determined")
            st.write(investigation.get("evidence_summary", ""))

            if investigation.get("alternative_hypotheses"):
                st.caption("Alternative hypotheses considered: " + str(investigation["alternative_hypotheses"]))

            st.subheader("Agent Trail")
            for run in investigation.get("agent_runs", []):
                with st.expander(f"{run['agent_name']} — {run['status']}"):
                    st.json(run["output"])

            st.subheader("Retrieved Knowledge (RAG)")
            for doc in investigation.get("retrieved_documents", []):
                st.markdown(
                    f"<div class='evidence-box'><b>{doc['document_id']}</b> "
                    f"(relevance {doc['relevance_score']:.2f}, rank {doc['rank']})<br>{doc['chunk_text']}</div>",
                    unsafe_allow_html=True,
                )

elif page == "RAG Knowledge Base":
    st.title("RAG Knowledge Base")
    st.write("Ingest a new document into the live knowledge base:")
    with st.form("ingest_form"):
        title = st.text_input("Title")
        source = st.text_input("Source", value="manual_upload")
        doc_type = st.selectbox("Document type", ["playbook", "mitre", "incident_report", "guide"])
        content = st.text_area("Content", height=200)
        submitted = st.form_submit_button("Ingest")
        if submitted and title and content:
            result = api_post("/documents/ingest", {"title": title, "source": source, "document_type": doc_type, "content": content})
            if result:
                st.success(f"Ingested as {result['document_id']}")

elif page == "ML Model Performance":
    st.title("ML Model Performance")
    metrics = api_get("/metrics")
    det = (metrics or {}).get("detector_metrics") or {}
    if det:
        for name, m in det.items():
            st.subheader(name)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Precision", f"{m['precision']:.3f}")
            c2.metric("Recall", f"{m['recall']:.3f}")
            c3.metric("F1", f"{m['f1']:.3f}")
            c4.metric("False Positive Rate", f"{m['false_positive_rate']:.4f}")
            st.write("Confusion matrix `[[TN, FP], [FN, TP]]`:", m["confusion_matrix"])
            st.caption(m["note"])
    else:
        st.info("Run `python ml/train_anomaly_models.py` to generate an evaluation report.")

elif page == "Recommendations":
    st.title("Recommendations & Approval")
    incident_id = st.text_input("Incident ID")
    if incident_id:
        rec = api_get(f"/incidents/{incident_id}/recommendation")
        if rec:
            st.write(f"**Action:** {rec['recommended_action']}  |  **Priority:** {rec['priority']}  |  **Risk:** {rec['risk']}")
            st.write(f"**Expected impact:** {rec['expected_impact']}")
            st.write(f"**Rollback:** {rec['rollback_recommendation']}")
            if rec["requires_human_approval"]:
                st.warning("This action requires human approval before any (simulated) execution.")
                approver = st.text_input("Your name/email (approver)")
                c1, c2 = st.columns(2)
                if c1.button("✅ Approve", disabled=not approver):
                    action = api_post(f"/incidents/{incident_id}/approve", {"approved_by": approver})
                    if action:
                        st.success(f"Approved. Simulated action '{action['action_type']}' recorded (not a real-world action).")
                if c2.button("❌ Reject", disabled=not approver):
                    action = api_post(f"/incidents/{incident_id}/reject", {"approved_by": approver})
                    if action:
                        st.info("Rejected. Incident closed without action.")

elif page == "Audit Logs":
    st.title("Audit Logs")
    st.info(
        "Audit log listing endpoint is not yet exposed via a dedicated "
        "GET /api/v1/audit-logs route in this build — logs are written on "
        "every approve/reject action (see backend/app/models/orm.py: "
        "AuditLog). Add the route when this page is prioritized."
    )

elif page == "System Health":
    st.title("System Health")
    health = api_get("/health")
    if health:
        status_color = "🟢" if health["status"] == "ok" else "🟡"
        st.write(f"{status_color} **Overall status:** {health['status']}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Database", "OK" if health["database"] else "DOWN")
        c2.metric("Anomaly Models", "Loaded" if health["anomaly_models_loaded"] else "Missing")
        c3.metric("Vector Store", "Loaded" if health["vector_store_loaded"] else "Empty")
        st.caption(f"LLM provider: {health['llm_provider']}")
