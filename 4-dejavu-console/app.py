import json
from pathlib import Path

import streamlit as st
import yaml

_DEJAVU_DIR = Path(__file__).parent.parent / "3-dejavu"
_RES_DIR    = _DEJAVU_DIR / "res"
_CONFIGS_DIR = _DEJAVU_DIR / "configs"

st.set_page_config(layout="wide", page_title="DejaVu Console")

# ── Session state ─────────────────────────────────────────────────────────────
if "anticipated_scenarios" not in st.session_state:
    st.session_state.anticipated_scenarios = []
if "dj_parameters" not in st.session_state:
    st.session_state.dj_parameters = {}
if "dj_scenarios" not in st.session_state:
    st.session_state.dj_scenarios = {}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("DejaVu Console")

    # ── 1 — Scenario Catalogue ────────────────────────────────────────────────
    st.subheader("1 — Load Scenario Catalogue")
    st.caption("Load the anticipated scenarios used by the state machine monitor.")
    st.file_uploader("Upload .yaml / .json", type=["yaml", "json"],
                     key="_anticipated_upload", label_visibility="collapsed")
    st.caption("Or load from res/:")
    st.selectbox("Sample", ["anticipated_scenarios.yaml"], key="_anticipated_select",
                 label_visibility="collapsed")
    st.button("Load", use_container_width=True, key="btn_load_anticipated")

    if st.session_state.anticipated_scenarios:
        st.caption(f"{len(st.session_state.anticipated_scenarios)} scenario(s) loaded")

    st.divider()

    # ── 2 — Anticipated Scenario Editor ──────────────────────────────────────
    st.subheader("2 — Anticipated Scenario Editor")

    # ── Scenario Parameters ───────────────────────────────────────────────────
    st.subheader("Scenario Parameters")
    with st.form("dj_form_add_param", clear_on_submit=True):
        p_name = st.text_input("Name *", placeholder="e.g. h")
        p_type = st.selectbox("Type", ["int", "float", "bool", "str"])
        col_min, col_max = st.columns(2)
        p_min = col_min.text_input("Min", placeholder="0")
        p_max = col_max.text_input("Max", placeholder="100")
        st.form_submit_button("Add Parameter", use_container_width=True)

    if st.session_state.dj_parameters:
        for pname, pdef in list(st.session_state.dj_parameters.items()):
            col_p, col_pd = st.columns([3, 1])
            type_str  = pdef.get("type", "")
            range_str = f" [{pdef.get('min','?')}–{pdef.get('max','?')}]" if "min" in pdef or "max" in pdef else ""
            col_p.caption(f"`{pname}` : {type_str}{range_str}")
            col_pd.button("🗑", key=f"dj_del_p_{pname}")

    st.divider()

    # ── Candidate Scenarios ───────────────────────────────────────────────────
    st.subheader("Candidate Scenarios")
    with st.form("dj_form_add_scenario", clear_on_submit=True):
        s_name      = st.text_input("Name *",  placeholder="e.g. cand_low_speed")
        s_given     = st.text_input("Given",   placeholder="e.g. h < 100")
        s_when      = st.text_input("When",    placeholder="e.g. b > 10")
        s_do        = st.text_input("Do",      placeholder="e.g. setSpeed(Low)")
        s_then      = st.text_input("Then",    placeholder="e.g. h >= 90")
        st.form_submit_button("Add Candidate", use_container_width=True)

    if st.session_state.dj_scenarios:
        for sid, s in list(st.session_state.dj_scenarios.items()):
            col_n, col_b = st.columns([3, 1])
            col_n.markdown(f"**{s['name']}**")
            col_b.button("🗑", key=f"dj_del_s_{sid}")

    st.divider()

    # ── Save Catalogue ────────────────────────────────────────────────────────
    st.button("Save Catalogue", use_container_width=True)


# ── Main area ─────────────────────────────────────────────────────────────────
st.title("DejaVu Console")

tab_similarity, tab_checked, tab_state_machine = st.tabs([
    "Similarities", "Checked Scenarios", "State Machine"
])

with tab_similarity:
    st.subheader("Similarity Results")
    st.info("Run DejaVu to see similarity results here.")

with tab_checked:
    st.subheader("Checked Scenarios")
    st.info("Run DejaVu to see checked scenario results here.")

with tab_state_machine:
    st.subheader("State Machine")
    st.info("State machine visualisation will appear here.")
