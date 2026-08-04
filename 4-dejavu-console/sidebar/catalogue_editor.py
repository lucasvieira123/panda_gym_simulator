import json

import streamlit as st

from config import CATALOGUE_PATH
from state import build_catalogue, scenario_id


def render() -> None:
    st.subheader("2 — Scenario Catalogue Editor")
    st.caption("Edit the catalogue, then save.")

    new_name = st.text_input("Catalogue name", value=st.session_state.dj_catalogue_name)
    st.session_state.dj_catalogue_name = new_name

    st.divider()
    _render_parameters()
    st.divider()
    _render_candidate_scenarios()
    st.divider()
    _render_save()


def _render_parameters() -> None:
    st.subheader("Monitored Parameters")

    with st.form("dj_form_add_param", clear_on_submit=True):
        p_name = st.text_input("Name *", placeholder="e.g. grip_force")
        p_type = st.selectbox("Type", ["int", "float", "bool", "str"])
        col_min, col_max = st.columns(2)
        p_min = col_min.text_input("Min", placeholder="0")
        p_max = col_max.text_input("Max", placeholder="100")
        submitted = st.form_submit_button("Add Parameter", use_container_width=True)

    if submitted:
        name = p_name.strip()
        if not name:
            st.sidebar.error("Name is required.")
        elif name in st.session_state.dj_parameters:
            st.sidebar.warning(f"'{name}' already exists.")
        else:
            entry: dict = {"type": p_type}
            if p_type in ("int", "float"):
                if p_min:
                    entry["min"] = float(p_min) if p_type == "float" else int(p_min)
                if p_max:
                    entry["max"] = float(p_max) if p_type == "float" else int(p_max)
            st.session_state.dj_parameters[name] = entry
            st.sidebar.success(f"'{name}' added!")

    for pname, pdef in list(st.session_state.dj_parameters.items()):
        col_label, col_btn = st.columns([3, 1])
        type_str  = pdef.get("type", "")
        range_str = (
            f" [{pdef.get('min', '?')}–{pdef.get('max', '?')}]"
            if "min" in pdef or "max" in pdef else ""
        )
        col_label.caption(f"`{pname}` : {type_str}{range_str}")
        if col_btn.button("🗑", key=f"dj_del_p_{pname}"):
            del st.session_state.dj_parameters[pname]
            st.rerun()


def _render_candidate_scenarios() -> None:
    st.subheader("Candidate Scenarios")

    with st.form("dj_form_add_scenario", clear_on_submit=True):
        s_name  = st.text_input("Name *",  placeholder="e.g. slip_recovery")
        s_given = st.text_input("Given",   placeholder="e.g. slip_detected == 1")
        s_when  = st.text_input("When",    placeholder="e.g. contact_detected == 1")
        s_do    = st.text_input("Do",      placeholder="e.g. increaseGripForce()")
        s_then  = st.text_input("Then",    placeholder="e.g. slip_detected == 0")
        submitted = st.form_submit_button("Add Candidate", use_container_width=True)

    if submitted:
        name = s_name.strip()
        if not name:
            st.sidebar.error("Name is required.")
        else:
            sid = scenario_id(name)
            if sid in st.session_state.dj_scenarios:
                st.sidebar.warning(f"'{name}' already exists.")
            else:
                st.session_state.dj_scenarios[sid] = {
                    "id":    sid,
                    "name":  name,
                    "given": s_given.strip(),
                    "when":  s_when.strip(),
                    "do":    s_do.strip(),
                    "then":  s_then.strip(),
                }
                st.sidebar.success(f"'{name}' added!")

    for sid, s in list(st.session_state.dj_scenarios.items()):
        col_name, col_btn = st.columns([3, 1])
        col_name.markdown(f"**{s['name']}**")
        if col_btn.button("🗑", key=f"dj_del_s_{sid}"):
            del st.session_state.dj_scenarios[sid]
            st.rerun()


def _render_save() -> None:
    st.subheader("Save Catalogue")
    if st.button("Save Catalogue", use_container_width=True):
        CATALOGUE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CATALOGUE_PATH.write_text(json.dumps(build_catalogue(), indent=2), encoding="utf-8")
        st.success("Saved → configs/arm/scenario_catalogue.json")
