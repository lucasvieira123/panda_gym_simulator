import streamlit as st

import state
from sidebar import render as render_sidebar
from views import catalogue, checked, similarities, state_machine

st.set_page_config(layout="wide", page_title="DejaVu Console")

state.init()

with st.sidebar:
    render_sidebar()

st.title(f"DejaVu Console — {st.session_state.dj_catalogue_name}")

state_machine.render()

st.divider()
catalogue.render()

st.divider()
st.subheader("Similarities")
similarities.render()

st.divider()
st.subheader("Checked Scenarios")
checked.render()
