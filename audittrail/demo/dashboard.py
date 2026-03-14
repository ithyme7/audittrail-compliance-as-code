import json
import os

import pandas as pd
import streamlit as st


st.set_page_config(page_title="AuditTrail Dashboard", layout="wide", page_icon="🛡️")


def load_data(file_path: str):
    traces = []
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    traces.append(json.loads(line))
    return traces


def verify_integrity(traces) -> bool:
    if not traces:
        return False
    prev = "0"
    for t in traces:
        if t.get("previous_hash") != prev:
            return False
        prev = t.get("hash")
    return True


st.title("🛡️ AuditTrail Compliance Dashboard")
st.markdown("*Live inzicht in de EU AI Act compliance status van je modellen.*")

st.sidebar.header("📁 Databron")
log_file = st.sidebar.text_input(
    "Pad naar audit.log", value="./demo_output/fraud-detection-demo_audit.log"
)

data = load_data(log_file)

if not data:
    st.warning(f"Geen data gevonden in {log_file}. Run eerst een demo!")
else:
    total_events = len(data)
    unique_traces = len(set(d.get("trace_id") for d in data if "trace_id" in d))
    is_valid = verify_integrity(data)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Totale Logs", total_events)
    col2.metric("Unieke AI Traces", unique_traces)
    col3.metric("Integriteit (Hash Chain)", "Gevalideerd ✅" if is_valid else "Corrupt ❌")
    col4.metric("Risk Level", "HIGH")

    st.divider()

    st.subheader("⚖️ Laatste Fairness Checks (Demographic Parity)")
    compliance_events = [
        d
        for d in data
        if d.get("event_type") == "training_end"
        and d.get("data", {}).get("compliance_checks")
    ]

    if compliance_events:
        latest_check = compliance_events[-1]["data"]["compliance_checks"].get(
            "demographic_parity", {}
        )
        c1, c2 = st.columns([1, 2])
        with c1:
            st.info(f"**Verschil:** {latest_check.get('value', 0):.3f}")
            st.info(f"**Drempelwaarde:** {latest_check.get('threshold', 0.05)}")
            if latest_check.get("violates"):
                st.error("🚨 Waarschuwing: Model vertoont bias (Overtreedt drempelwaarde)")
            else:
                st.success("✅ Model is eerlijk (Binnen drempelwaarde)")
    else:
        st.write("Nog geen fairness data beschikbaar.")

    st.divider()

    st.subheader("🔍 Recente Audit Log")
    df = pd.DataFrame(data[-10:])
    if not df.empty:
        df_display = df[["timestamp", "event_type", "trace_id", "hash"]]
        st.dataframe(df_display, use_container_width=True)

    with st.expander("Toon ruwe JSON van laatste event"):
        st.json(data[-1] if data else {})
