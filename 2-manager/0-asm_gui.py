import json
from pathlib import Path
import streamlit as st
import yaml
from streamlit_agraph import agraph, Node, Edge, Config

_CONFIGS_DIR = Path(__file__).parent / "configs"

st.set_page_config(layout="wide", page_title="ASM Editor")

st.markdown("""
<style>
[data-testid="stDownloadButton"] button[kind="primary"] {
    background-color: #28a745 !important;
    border-color: #28a745 !important;
    color: white !important;
}
[data-testid="stDownloadButton"] button[kind="primary"]:hover {
    background-color: #218838 !important;
    border-color: #218838 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "scenarios" not in st.session_state:
    st.session_state.scenarios = {}   # { id: {id, name, given, when, do, then} }
if "transitions" not in st.session_state:
    st.session_state.transitions = [] # [ {from: id, to: id} ]
if "parameters" not in st.session_state:
    st.session_state.parameters = {}  # { name: {type, min, max} }
if "model_name" not in st.session_state:
    st.session_state.model_name = "My ASM"
if "last_loaded_file" not in st.session_state:
    st.session_state.last_loaded_file = None


# ── Helpers ───────────────────────────────────────────────────────────────────
def scenario_id(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def make_label(s: dict) -> str:
    given = s["given"] or "*"
    when  = s["when"]  or "*"
    do    = s["do"]    or "-"
    then  = s["then"]  or "*"
    return (
        f"{s['name']}\n"
        f"─────────────────\n"
        f"Given : {given}\n"
        f"When  : {when}\n"
        f"Do    : {do}\n"
        f"Then  : {then}"
    )


def build_asm() -> dict:
    return {
        "metadata": {
            "name": st.session_state.model_name,
        },
        "parameters": st.session_state.parameters,
        "scenarios": {
            sid: {
                "name":  s["name"],
                "given": s["given"] or "*",
                "when":  s["when"]  or "*",
                "do":    s["do"],
                "then":  s["then"]  or "*",
            }
            for sid, s in st.session_state.scenarios.items()
        },
        "transitions": st.session_state.transitions,
    }


def load_asm(model: dict):
    meta   = model.get("metadata", {})
    st.session_state.model_name  = meta.get("name", "My ASM")
    st.session_state.parameters  = model.get("parameters", {})
    raw_scenarios = model.get("scenarios", {})
    st.session_state.scenarios   = {
        sid: {"id": sid, **s} for sid, s in raw_scenarios.items()
    }
    st.session_state.transitions = model.get("transitions", [])


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("ASM Editor")
    new_name = st.text_input("Model name", value=st.session_state.model_name)
    st.session_state.model_name = new_name

    # ── Load ──────────────────────────────────────────────────────────────────
    uploaded = st.file_uploader("Load model (.json)", type="json", label_visibility="collapsed")
    if uploaded is not None and uploaded.name != st.session_state.last_loaded_file:
        try:
            model = json.load(uploaded)
            load_asm(model)
            st.session_state.last_loaded_file = uploaded.name
            st.success("Model loaded!")
            st.rerun()
        except Exception as e:
            st.error(f"Invalid file: {e}")

    st.divider()

    # ── Parameters ────────────────────────────────────────────────────────────
    st.subheader("Parameters")
    with st.form("form_add_param", clear_on_submit=True):
        p_name = st.text_input("Name *", placeholder="e.g. h")
        p_type = st.selectbox("Type", ["int", "float", "bool", "str"])
        col_min, col_max = st.columns(2)
        p_min  = col_min.text_input("Min", placeholder="0")
        p_max  = col_max.text_input("Max", placeholder="100")
        add_param_btn = st.form_submit_button("Add Parameter", use_container_width=True)

    if add_param_btn:
        if not p_name.strip():
            st.sidebar.error("Name is required.")
        elif p_name.strip() in st.session_state.parameters:
            st.sidebar.warning(f"Parameter '{p_name}' already exists.")
        else:
            entry = {"type": p_type}
            if p_type in ("int", "float"):
                if p_min: entry["min"] = float(p_min) if p_type == "float" else int(p_min)
                if p_max: entry["max"] = float(p_max) if p_type == "float" else int(p_max)
            st.session_state.parameters[p_name.strip()] = entry
            st.sidebar.success(f"Parameter '{p_name}' added!")

    if st.session_state.parameters:
        for pname, pdef in list(st.session_state.parameters.items()):
            col_p, col_pd = st.columns([3, 1])
            type_str = pdef.get("type", "")
            range_str = ""
            if "min" in pdef or "max" in pdef:
                range_str = f" [{pdef.get('min','?')}–{pdef.get('max','?')}]"
            col_p.caption(f"`{pname}` : {type_str}{range_str}")
            if col_pd.button("🗑", key=f"del_p_{pname}"):
                del st.session_state.parameters[pname]
                st.rerun()

    st.divider()

    # ── Add Scenario ──────────────────────────────────────────────────────────
    st.subheader("Scenarios")
    with st.form("form_add_scenario", clear_on_submit=True):
        name      = st.text_input("Name *",  placeholder="e.g. Takeoff")
        given     = st.text_input("Given",   placeholder="e.g. h == 0")
        when      = st.text_input("When",    placeholder="e.g. armed == True")
        do_action = st.text_input("Do",      placeholder="e.g. takeoff_act")
        then      = st.text_input("Then",    placeholder="e.g. h >= 100")
        add_btn   = st.form_submit_button("Add Scenario", use_container_width=True)

    if add_btn:
        if not name.strip():
            st.sidebar.error("Name is required.")
        else:
            sid = scenario_id(name)
            if sid in st.session_state.scenarios:
                st.sidebar.warning(f"Scenario '{name}' already exists.")
            else:
                st.session_state.scenarios[sid] = {
                    "id":    sid,
                    "name":  name.strip(),
                    "given": given.strip(),
                    "when":  when.strip(),
                    "do":    do_action.strip(),
                    "then":  then.strip(),
                }
                st.sidebar.success(f"'{name}' added!")

    # ── Scenario list + delete ─────────────────────────────────────────────────
    if st.session_state.scenarios:
        for sid, s in list(st.session_state.scenarios.items()):
            col_name, col_btn = st.columns([3, 1])
            col_name.markdown(f"**{s['name']}**")
            if col_btn.button("🗑", key=f"del_{sid}", help="Delete scenario"):
                del st.session_state.scenarios[sid]
                st.session_state.transitions = [
                    t for t in st.session_state.transitions
                    if t["from"] != sid and t["to"] != sid
                ]
                st.rerun()

    st.divider()

    # ── Transitions ───────────────────────────────────────────────────────────
    if len(st.session_state.scenarios) >= 1:
        st.subheader("Transitions")
        names = {s["name"]: sid for sid, s in st.session_state.scenarios.items()}
        name_list = list(names.keys())

        from_name = st.selectbox("From", name_list, key="sel_from")
        to_name   = st.selectbox("To",   name_list, key="sel_to")

        if st.button("Add Transition", use_container_width=True):
            t = {"from": names[from_name], "to": names[to_name]}
            if t in st.session_state.transitions:
                st.sidebar.warning("Transition already exists.")
            else:
                st.session_state.transitions.append(t)
                label = f"{from_name} ↺" if from_name == to_name else f"{from_name} → {to_name}"
                st.sidebar.success(label)

        id_to_name = {sid: s["name"] for sid, s in st.session_state.scenarios.items()}
        for i, t in enumerate(st.session_state.transitions):
            fn = id_to_name.get(t["from"], t["from"])
            tn = id_to_name.get(t["to"],   t["to"])
            col_t, col_td = st.columns([3, 1])
            label = f"{fn} ↺" if t["from"] == t["to"] else f"{fn} → {tn}"
            col_t.caption(label)
            if col_td.button("🗑", key=f"del_t_{i}", help="Delete transition"):
                st.session_state.transitions.pop(i)
                st.rerun()

        st.divider()

    # ── Save JSON ─────────────────────────────────────────────────────────────
    st.subheader("Save Model")
    if st.button("Save to configs/asm.json", use_container_width=True, type="primary"):
        _CONFIGS_DIR.mkdir(exist_ok=True)
        (_CONFIGS_DIR / "asm.json").write_text(
            json.dumps(build_asm(), indent=2), encoding="utf-8"
        )
        st.success("Saved → configs/asm.json")

    # ── Export YAML ───────────────────────────────────────────────────────────
    st.subheader("Export")
    payload = {
        "scenarios": [
            {
                "id":    sid,
                "name":  s["name"],
                "given": s["given"] or "*",
                "when":  s["when"]  or "*",
                "do":    s["do"],
                "then":  s["then"]  or "*",
            }
            for sid, s in st.session_state.scenarios.items()
        ],
        "transitions": st.session_state.transitions,
    }
    yaml_str = yaml.dump(payload, allow_unicode=True, default_flow_style=False)
    st.download_button(
        label="Export anticipated_scenarios.yaml",
        data=yaml_str,
        file_name="anticipated_scenarios.yaml",
        mime="text/yaml",
        use_container_width=True,
    )


# ── Main canvas ───────────────────────────────────────────────────────────────
st.title(f"ASM — {st.session_state.model_name}")

if not st.session_state.scenarios:
    st.info("Use the sidebar to add your first scenario.")
else:
    with st.container(border=True):
        st.subheader("ASM")

        COLS = 2
        SPACING_X = 380
        SPACING_Y = 260

        asm_nodes = []
        for i, (sid, s) in enumerate(st.session_state.scenarios.items()):
            col = i % COLS
            row = i // COLS
            asm_nodes.append(
                Node(
                    id=sid,
                    label=make_label(s),
                    shape="box",
                    x=col * SPACING_X,
                    y=row * SPACING_Y,
                    color={"background": "#1E3A5F", "border": "#4C9BE8",
                           "highlight": {"background": "#2A5298", "border": "#6BB3F0"}},
                    font={"size": 13, "color": "#FFFFFF", "face": "monospace", "align": "left"},
                )
            )

        asm_edges = [
            Edge(source=t["from"], target=t["to"], directed=True,
                 color={"color": "#4C9BE8"}, arrows="to")
            for t in st.session_state.transitions
        ]

        agraph(nodes=asm_nodes, edges=asm_edges, config=Config(
            width="100%", height=600, directed=True,
            physics=False, hierarchical=False, nodeHighlightBehavior=True,
        ))
