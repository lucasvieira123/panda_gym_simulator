import streamlit as st
from streamlit_agraph import Config, Edge, Node, agraph


def _node_color(name: str) -> dict:
    if name == "INIT":
        return {"background": "#2E7D32", "border": "#66BB6A"}
    if name == "FINAL":
        return {"background": "#1A237E", "border": "#5C6BC0"}
    if name.startswith("ERR"):
        return {"background": "#7B1010", "border": "#EF5350"}
    if name.startswith("PHI"):
        return {"background": "#4A235A", "border": "#AB47BC"}
    return {"background": "#1E3A5F", "border": "#4C9BE8"}


def _node_label(state: dict) -> str:
    name   = state["name"]
    always = next(
        (c["always"] for c in state.get("contract", []) if "always" in c),
        None,
    )
    return f"{name}\n─────────────\n{always}" if always and always != "True" else name


def _build_graph(assm: dict) -> tuple[list, list]:
    states = assm["statechart"]["root state"]["states"]
    nodes, edges = [], []
    for state in states:
        name = state["name"]
        nodes.append(Node(
            id=name, label=_node_label(state), shape="box",
            color=_node_color(name),
            font={"size": 12, "color": "#FFFFFF", "face": "monospace", "align": "left"},
        ))
        for tr in state.get("transitions", []):
            label = tr.get("event", tr.get("guard", ""))
            edges.append(Edge(
                source=name, target=tr["target"],
                directed=True, arrows="to",
                label=label,
                color={"color": "#90A4AE"},
                font={"size": 11, "color": "#CFD8DC", "align": "middle"},
            ))
    return nodes, edges


def render() -> None:
    assm = st.session_state.get("dj_assm")
    if assm is None:
        st.info("Load & Generate a State Machine from the sidebar (block 0) to see it here.")
        return

    nodes, edges = _build_graph(assm)
    agraph(nodes=nodes, edges=edges, config=Config(
        width="100%", height=700, directed=True,
        physics=False, hierarchical=True, nodeHighlightBehavior=True,
    ))
