import json
from pathlib import Path

import pandas as pd
import streamlit as st

_DEJAVU_DIR     = Path(__file__).parent.parent / "3-dejavu"
_CONFIGS_DIR    = _DEJAVU_DIR / "configs"
_CATALOGUE_SAMPLES = {
    "ARM": _CONFIGS_DIR / "arm" / "scenario_catalogue.json",
}

_CATALOGUE_PATH = _CONFIGS_DIR / "arm" / "scenario_catalogue.json"

st.set_page_config(layout="wide", page_title="DejaVu Console")

# ── Session state ─────────────────────────────────────────────────────────────
if "dj_catalogue_name" not in st.session_state:
    st.session_state.dj_catalogue_name = "My Catalogue"
if "dj_parameters" not in st.session_state:
    st.session_state.dj_parameters = {}
if "dj_scenarios" not in st.session_state:
    st.session_state.dj_scenarios = {}

# ── Helpers ───────────────────────────────────────────────────────────────────
def scenario_id(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def build_catalogue() -> dict:
    return {
        "metadata": {"name": st.session_state.dj_catalogue_name},
        "monitored_parameters": st.session_state.dj_parameters,
        "scenarios": {
            sid: {
                "name":  s["name"],
                "given": s["given"] or "*",
                "when":  s["when"]  or "*",
                "do":    s["do"],
                "then":  s["then"]  or "*",
            }
            for sid, s in st.session_state.dj_scenarios.items()
        },
    }


def load_catalogue(data: dict) -> None:
    meta = data.get("metadata", {})
    st.session_state.dj_catalogue_name = meta.get("name", "My Catalogue")
    st.session_state.dj_parameters     = data.get("monitored_parameters", {})
    raw = data.get("scenarios", {})
    st.session_state.dj_scenarios = {
        sid: {"id": sid, **s}
        for sid, s in raw.items()
    }


def _on_load_sample():
    name = st.session_state._dj_sample_select
    path = _CATALOGUE_SAMPLES[name]
    if path.exists():
        load_catalogue(json.loads(path.read_text(encoding="utf-8")))
        st.session_state._dj_load_msg = f"Loaded: {name}"
    else:
        st.session_state._dj_load_msg = f"❌ File not found: {path}"


def _on_file_upload():
    uploaded = st.session_state._dj_file_upload
    if uploaded is None:
        return
    try:
        data = json.load(uploaded)
        load_catalogue(data)
        st.session_state._dj_load_msg = "Catalogue loaded!"
    except Exception as e:
        st.session_state._dj_load_msg = f"❌ Invalid file: {e}"


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("DejaVu Console")

    # ── 1 — Load Scenario Catalogue ───────────────────────────────────────────
    st.subheader("1 — Load Scenario Catalogue")
    st.caption("Upload a JSON file or pick a built-in sample.")
    st.file_uploader("Upload .json", type="json", key="_dj_file_upload",
                     on_change=_on_file_upload, label_visibility="collapsed")
    st.caption("Or load a sample:")
    st.selectbox("Sample", list(_CATALOGUE_SAMPLES.keys()), key="_dj_sample_select",
                 label_visibility="collapsed")
    st.button("Load Sample", use_container_width=True, on_click=_on_load_sample)

    if msg := st.session_state.pop("_dj_load_msg", None):
        st.success(msg)

    st.divider()

    # ── 2 — Anticipated Scenario Editor ──────────────────────────────────────
    st.subheader("2 — Anticipated Scenario Editor")
    st.caption("Edit the catalogue, then save.")

    new_name = st.text_input("Catalogue name", value=st.session_state.dj_catalogue_name)
    st.session_state.dj_catalogue_name = new_name

    st.divider()

    # ── Scenario Parameters ───────────────────────────────────────────────────
    st.subheader("Scenario Parameters")
    with st.form("dj_form_add_param", clear_on_submit=True):
        p_name = st.text_input("Name *", placeholder="e.g. h")
        p_type = st.selectbox("Type", ["int", "float", "bool", "str"])
        col_min, col_max = st.columns(2)
        p_min = col_min.text_input("Min", placeholder="0")
        p_max = col_max.text_input("Max", placeholder="100")
        add_param_btn = st.form_submit_button("Add Parameter", use_container_width=True)

    if add_param_btn:
        if not p_name.strip():
            st.sidebar.error("Name is required.")
        elif p_name.strip() in st.session_state.dj_parameters:
            st.sidebar.warning(f"Parameter '{p_name}' already exists.")
        else:
            entry = {"type": p_type}
            if p_type in ("int", "float"):
                if p_min: entry["min"] = float(p_min) if p_type == "float" else int(p_min)
                if p_max: entry["max"] = float(p_max) if p_type == "float" else int(p_max)
            st.session_state.dj_parameters[p_name.strip()] = entry
            st.sidebar.success(f"Parameter '{p_name}' added!")

    if st.session_state.dj_parameters:
        for pname, pdef in list(st.session_state.dj_parameters.items()):
            col_p, col_pd = st.columns([3, 1])
            type_str  = pdef.get("type", "")
            range_str = f" [{pdef.get('min','?')}–{pdef.get('max','?')}]" if "min" in pdef or "max" in pdef else ""
            col_p.caption(f"`{pname}` : {type_str}{range_str}")
            if col_pd.button("🗑", key=f"dj_del_p_{pname}"):
                del st.session_state.dj_parameters[pname]
                st.rerun()

    st.divider()

    # ── Candidate Scenarios ───────────────────────────────────────────────────
    st.subheader("Candidate Scenarios")
    with st.form("dj_form_add_scenario", clear_on_submit=True):
        s_name  = st.text_input("Name *",  placeholder="e.g. cand_low_speed")
        s_given = st.text_input("Given",   placeholder="e.g. h < 100")
        s_when  = st.text_input("When",    placeholder="e.g. b > 10")
        s_do    = st.text_input("Do",      placeholder="e.g. setSpeed(Low)")
        s_then  = st.text_input("Then",    placeholder="e.g. h >= 90")
        add_scenario_btn = st.form_submit_button("Add Candidate", use_container_width=True)

    if add_scenario_btn:
        if not s_name.strip():
            st.sidebar.error("Name is required.")
        else:
            sid = scenario_id(s_name)
            if sid in st.session_state.dj_scenarios:
                st.sidebar.warning(f"Scenario '{s_name}' already exists.")
            else:
                st.session_state.dj_scenarios[sid] = {
                    "id":    sid,
                    "name":  s_name.strip(),
                    "given": s_given.strip(),
                    "when":  s_when.strip(),
                    "do":    s_do.strip(),
                    "then":  s_then.strip(),
                }
                st.sidebar.success(f"'{s_name}' added!")

    if st.session_state.dj_scenarios:
        for sid, s in list(st.session_state.dj_scenarios.items()):
            col_n, col_b = st.columns([3, 1])
            col_n.markdown(f"**{s['name']}**")
            if col_b.button("🗑", key=f"dj_del_s_{sid}"):
                del st.session_state.dj_scenarios[sid]
                st.rerun()

    st.divider()

    # ── Save Catalogue ────────────────────────────────────────────────────────
    st.subheader("Save Catalogue")
    if st.button("Save Catalogue", use_container_width=True):
        _CONFIGS_DIR.mkdir(exist_ok=True)
        _CATALOGUE_PATH.write_text(
            json.dumps(build_catalogue(), indent=2), encoding="utf-8"
        )
        st.success("Saved → 3-dejavu/configs/scenario_catalogue.json")


# ── Main area ─────────────────────────────────────────────────────────────────
st.title(f"DejaVu Console — {st.session_state.dj_catalogue_name}")

tab_catalogue, tab_similarity, tab_checked, tab_state_machine = st.tabs([
    "Catalogue", "Similarities", "Checked Scenarios", "State Machine"
])

with tab_catalogue:
    has_data = st.session_state.dj_parameters or st.session_state.dj_scenarios

    if not has_data:
        st.info("Load a scenario catalogue from the sidebar to see its contents here.")
    else:
        if st.session_state.dj_parameters:
            st.subheader("Monitored Parameters")
            rows = []
            for pname, pdef in st.session_state.dj_parameters.items():
                rows.append({
                    "Name": pname,
                    "Type": pdef.get("type", ""),
                    "Min":  pdef.get("min", ""),
                    "Max":  pdef.get("max", ""),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        if st.session_state.dj_scenarios:
            st.subheader("Candidate Scenarios")
            rows = []
            for s in st.session_state.dj_scenarios.values():
                rows.append({
                    "Name":  s.get("name", ""),
                    "Given": s.get("given", "*"),
                    "When":  s.get("when", "*"),
                    "Do":    s.get("do", ""),
                    "Then":  s.get("then", "*"),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with tab_similarity:
    st.subheader("Similarity Results")
    st.info("Run DejaVu to see similarity results here.")

with tab_checked:
    st.subheader("Checked Scenarios")
    st.info("Run DejaVu to see checked scenario results here.")

with tab_state_machine:
    st.subheader("State Machine")
    st.info("State machine visualisation will appear here.")
