import json

import streamlit as st

from config import CATALOGUE_SAMPLES
from state import load_catalogue


def _on_load_sample() -> None:
    name = st.session_state._dj_sample_select
    path = CATALOGUE_SAMPLES[name]
    if path.exists():
        load_catalogue(json.loads(path.read_text(encoding="utf-8")))
        st.session_state._dj_load_msg = f"Loaded: {name}"
    else:
        st.session_state._dj_load_msg = f"❌ File not found: {path}"


def _on_file_upload() -> None:
    uploaded = st.session_state._dj_file_upload
    if uploaded is None:
        return
    try:
        load_catalogue(json.load(uploaded))
        st.session_state._dj_load_msg = "Catalogue loaded!"
    except Exception as e:
        st.session_state._dj_load_msg = f"❌ Invalid file: {e}"


def render() -> None:
    st.subheader("1 — Load Scenario Catalogue")
    st.caption("Upload a JSON file or pick a built-in sample.")

    st.file_uploader(
        "Upload .json", type="json",
        key="_dj_file_upload", on_change=_on_file_upload,
        label_visibility="collapsed",
    )
    st.caption("Or load a sample:")
    st.selectbox(
        "Sample", list(CATALOGUE_SAMPLES.keys()),
        key="_dj_sample_select", label_visibility="collapsed",
    )
    st.button("Load Sample", use_container_width=True, on_click=_on_load_sample)

    if msg := st.session_state.pop("_dj_load_msg", None):
        st.success(msg)
