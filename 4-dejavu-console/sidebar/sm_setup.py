import json
import sys

import streamlit as st

from config import ASM_LOCAL, ASM_SAMPLES, DEJAVU_SRC_DIR, STATE_MACHINE_PATH


def _ensure_src() -> None:
    src = str(DEJAVU_SRC_DIR)
    if src not in sys.path:
        sys.path.insert(0, src)


def _generate_sm(asm: dict) -> None:
    _ensure_src()
    from has_model_to_assm import has_to_assm, to_yaml
    assm = has_to_assm(asm)
    STATE_MACHINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ASM_LOCAL.write_text(json.dumps(asm, indent=2), encoding="utf-8")
    STATE_MACHINE_PATH.write_text(to_yaml(assm), encoding="utf-8")
    st.session_state.dj_assm = assm


def _on_asm_upload() -> None:
    uploaded = st.session_state._dj_asm_upload
    if uploaded is None:
        return
    try:
        _generate_sm(json.load(uploaded))
        st.session_state.dj_sm_loaded = True
        st.session_state._sm_msg = ("ok", f"Loaded & generated: {uploaded.name}")
    except Exception as e:
        st.session_state._sm_msg = ("error", str(e))


def _on_load_asm_sample() -> None:
    name = st.session_state._dj_asm_select
    path = ASM_SAMPLES[name]
    if not path.exists():
        st.session_state._sm_msg = ("error", f"File not found: {path}")
        return
    try:
        _generate_sm(json.loads(path.read_text(encoding="utf-8")))
        st.session_state.dj_sm_loaded = True
        st.session_state._sm_msg = ("ok", f"Loaded & generated: {name}")
    except Exception as e:
        st.session_state._sm_msg = ("error", str(e))


def render() -> None:
    st.subheader("0 — State Machine Setup")
    st.caption("Upload an ASM JSON or pick a built-in sample.")

    st.file_uploader(
        "Upload ASM .json", type="json",
        key="_dj_asm_upload", on_change=_on_asm_upload,
        label_visibility="collapsed",
    )
    st.caption("Or load a sample:")
    st.selectbox(
        "ASM Sample", list(ASM_SAMPLES.keys()),
        key="_dj_asm_select", label_visibility="collapsed",
    )
    st.button("Load & Generate", use_container_width=True, on_click=_on_load_asm_sample)

    if "_sm_msg" in st.session_state:
        kind, msg = st.session_state.pop("_sm_msg")
        (st.success if kind == "ok" else st.error)(msg)
