import streamlit as st


def init() -> None:
    defaults = {
        "dj_catalogue_name": "My Catalogue",
        "dj_parameters":     {},
        "dj_scenarios":      {},
        "dj_sm_loaded":      False,
        "dj_assm":           None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


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
