import streamlit as st

from .sm_setup import render as render_sm_setup
from .catalogue_loader import render as render_catalogue_loader
from .catalogue_editor import render as render_catalogue_editor


def render() -> None:
    st.title("DejaVu Console")
    render_sm_setup()
    st.divider()
    render_catalogue_loader()
    st.divider()
    render_catalogue_editor()
