import pandas as pd
import streamlit as st


def render() -> None:
    if not (st.session_state.dj_parameters or st.session_state.dj_scenarios):
        st.info("Load a scenario catalogue from the sidebar to see its contents here.")
        return

    if st.session_state.dj_parameters:
        st.subheader("Monitored Parameters")
        rows = [
            {
                "Name": pname,
                "Type": pdef.get("type", ""),
                "Min":  pdef.get("min", ""),
                "Max":  pdef.get("max", ""),
            }
            for pname, pdef in st.session_state.dj_parameters.items()
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    if st.session_state.dj_scenarios:
        st.subheader("Candidate Scenarios")
        rows = [
            {
                "Name":  s.get("name", ""),
                "Given": s.get("given", "*"),
                "When":  s.get("when", "*"),
                "Do":    s.get("do", ""),
                "Then":  s.get("then", "*"),
            }
            for s in st.session_state.dj_scenarios.values()
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
