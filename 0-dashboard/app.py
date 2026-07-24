import json
import queue
import threading
from pathlib import Path
import streamlit as st
import yaml
from websockets.sync.client import connect as ws_connect
from streamlit_agraph import agraph, Node, Edge, Config

_CONFIGS_DIR    = Path(__file__).parent.parent / "1-manager" / "configs"
_MANAGER_WS_URL = "ws://localhost:8001/ws/state"


# ── WebSocket receiver (background thread) ────────────────────────────────────

def _ws_receiver(q: queue.Queue, browser_ready: threading.Event, conn_count: list) -> None:
    import time
    browser_ready.wait(timeout=60.0)
    while True:
        try:
            with ws_connect(_MANAGER_WS_URL) as ws:
                conn_count[0] += 1  # nova ligação ao manager = nova execução
                for raw in ws:
                    msg = json.loads(raw)
                    try:
                        q.put_nowait(msg)
                    except queue.Full:
                        try:
                            q.get_nowait()
                        except queue.Empty:
                            pass
                        q.put_nowait(msg)
        except Exception:
            time.sleep(0.1)


@st.cache_resource
def _get_shared_state():
    """Singleton por processo: fila, evento browser_ready, contador de runs e de conexões."""
    q = queue.Queue(maxsize=1)
    browser_ready = threading.Event()
    call_count = [0]
    conn_count  = [0]  # incrementa cada vez que _ws_receiver conecta ao manager
    threading.Thread(target=_ws_receiver, args=(q, browser_ready, conn_count), daemon=True).start()
    return q, browser_ready, call_count, conn_count

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
if "monitored_parameters" not in st.session_state:
    st.session_state.monitored_parameters = {}  # { name: {type, min, max} }
if "model_name" not in st.session_state:
    st.session_state.model_name = "My ASM"
if "last_loaded_file" not in st.session_state:
    st.session_state.last_loaded_file = None
if "perception_history" not in st.session_state:
    st.session_state.perception_history = []

# ── Helpers ───────────────────────────────────────────────────────────────────
def scenario_id(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def make_label(s: dict) -> str:
    given = s["given"] or "*"
    when  = s["when"]  or "*"
    do    = s["do"]    or "-"
    then  = s["then"]  or "*"
    prefix = "[A] " if s.get("type", "predefined") == "adaptive" else ""
    return (
        f"{prefix}{s['name']}\n"
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
        "nodes": {
            "init": {"name": "INIT", "type": "init"},
            "end":  {"name": "END",  "type": "end"},
        },
        "monitored_parameters": st.session_state.monitored_parameters,
        "scenarios": {
            sid: {
                "name":  s["name"],
                "type":  s.get("type", "predefined"),
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
    # aceita tanto "monitored_parameters" (formato atual) quanto "parameters" (legado)
    st.session_state.monitored_parameters = (
        model.get("monitored_parameters") or model.get("parameters", {})
    )
    raw_scenarios = model.get("scenarios", {})
    st.session_state.scenarios   = {
        sid: {"id": sid, "type": s.get("type", "predefined"), **s}
        for sid, s in raw_scenarios.items()
    }
    st.session_state.transitions = model.get("transitions", [])


# Auto-carrega asm.json do manager na primeira vez que a sessão arranca
_ASM_PATH = _CONFIGS_DIR / "asm.json"
if "asm_auto_loaded" not in st.session_state:
    st.session_state.asm_auto_loaded = False
if not st.session_state.asm_auto_loaded and _ASM_PATH.exists():
    try:
        load_asm(json.loads(_ASM_PATH.read_text(encoding="utf-8")))
        st.session_state.asm_auto_loaded = True
    except Exception:
        pass


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
    st.subheader("Monitored Parameters")
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
        elif p_name.strip() in st.session_state.monitored_parameters:
            st.sidebar.warning(f"Parameter '{p_name}' already exists.")
        else:
            entry = {"type": p_type}
            if p_type in ("int", "float"):
                if p_min: entry["min"] = float(p_min) if p_type == "float" else int(p_min)
                if p_max: entry["max"] = float(p_max) if p_type == "float" else int(p_max)
            st.session_state.monitored_parameters[p_name.strip()] = entry
            st.sidebar.success(f"Parameter '{p_name}' added!")

    if st.session_state.monitored_parameters:
        for pname, pdef in list(st.session_state.monitored_parameters.items()):
            col_p, col_pd = st.columns([3, 1])
            type_str = pdef.get("type", "")
            range_str = ""
            if "min" in pdef or "max" in pdef:
                range_str = f" [{pdef.get('min','?')}–{pdef.get('max','?')}]"
            col_p.caption(f"`{pname}` : {type_str}{range_str}")
            if col_pd.button("🗑", key=f"del_p_{pname}"):
                del st.session_state.monitored_parameters[pname]
                st.rerun()

    st.divider()

    # ── Add Scenario ──────────────────────────────────────────────────────────
    st.subheader("Scenarios")
    with st.form("form_add_scenario", clear_on_submit=True):
        name          = st.text_input("Name *",  placeholder="e.g. Takeoff")
        scenario_type = st.radio("Type", ["predefined", "adaptive"], horizontal=True, index=0)
        given         = st.text_input("Given",   placeholder="e.g. h == 0")
        when          = st.text_input("When",    placeholder="e.g. armed == True")
        do_action     = st.text_input("Do",      placeholder="e.g. takeoff_act")
        then          = st.text_input("Then",    placeholder="e.g. h >= 100")
        add_btn       = st.form_submit_button("Add Scenario", use_container_width=True)

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
                    "type":  scenario_type,
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
            badge = "`adaptive`" if s.get("type", "predefined") == "adaptive" else "`predefined`"
            col_name.markdown(f"**{s['name']}** {badge}")
            if col_btn.button("🗑", key=f"del_{sid}", help="Delete scenario"):
                del st.session_state.scenarios[sid]
                st.session_state.transitions = [
                    t for t in st.session_state.transitions
                    if t["from"] != sid and t["to"] != sid
                ]
                st.rerun()

    st.divider()

    # ── Transitions ───────────────────────────────────────────────────────────
    st.subheader("Transitions")
    _FIXED_NODES = {"● Init": "__init__", "◎ End": "__end__"}
    names = {**_FIXED_NODES, **{s["name"]: sid for sid, s in st.session_state.scenarios.items()}}
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

    _fixed_display = {"__init__": "● Init", "__end__": "◎ End"}
    id_to_name = {**_fixed_display, **{sid: s["name"] for sid, s in st.session_state.scenarios.items()}}
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
        st.success("Saved → 2-manager/configs/asm.json")

    # ── Export YAML ───────────────────────────────────────────────────────────
    st.subheader("Export")
    payload = {
        "scenarios": [
            {
                "id":    sid,
                "name":  s["name"],
                "type":  s.get("type", "predefined"),
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


# ── Live state panel ─────────────────────────────────────────────────────────
st.title(f"ASM — {st.session_state.model_name}")

def _flatten_perception(p: dict) -> dict:
    def r3(v): return [round(x, 4) for x in v] if v else []
    row = {
        "episode":              p.get("episode"),
        "step":                 p.get("step"),
        "task":                 p.get("current_task", ""),
        "reward":               round(p.get("reward", 0), 4),
        "success":              p.get("is_success", False),
        "fingers":              round(p.get("fingers_width", 0), 4),
        "ee_x":                 round(p["ee_position"][0], 4) if p.get("ee_position") else None,
        "ee_y":                 round(p["ee_position"][1], 4) if p.get("ee_position") else None,
        "ee_z":                 round(p["ee_position"][2], 4) if p.get("ee_position") else None,
        "cube_x":               round(p["cube_position"][0], 4) if p.get("cube_position") else None,
        "cube_y":               round(p["cube_position"][1], 4) if p.get("cube_position") else None,
        "cube_z":               round(p["cube_position"][2], 4) if p.get("cube_position") else None,
        "cube_roll":            round(p["cube_rotation"][0], 4) if p.get("cube_rotation") else None,
        "cube_pitch":           round(p["cube_rotation"][1], 4) if p.get("cube_rotation") else None,
        "cube_yaw":             round(p["cube_rotation"][2], 4) if p.get("cube_rotation") else None,
        "target_x":             round(p["target_position"][0], 4) if p.get("target_position") else None,
        "target_y":             round(p["target_position"][1], 4) if p.get("target_position") else None,
        "target_z":             round(p["target_position"][2], 4) if p.get("target_position") else None,
        "dist_ee_cube":         round(p.get("dist_ee_to_cube", 0), 4),
        "dist_cube_target":     round(p.get("dist_cube_to_target", 0), 4),
        "obstacle_in_path":     p.get("obstacle_in_path", False),
        "obstacle_count":       p.get("obstacle_count_in_path", 0),
    }
    joints = p.get("joint_angles", [])
    for i, v in enumerate(joints):
        row[f"j{i}_angle"] = round(v, 4)
    return row


@st.fragment(run_every=0.1)
def live_panel():
    q, browser_ready, call_count, conn_count = _get_shared_state()
    call_count[0] += 1
    if call_count[0] == 2:  # 1ª chamada é server-side; 2ª é o 1º tick real do browser
        browser_ready.set()

    # Detecta nova execução do manager/managing: conn_count mudou desde a última vez
    last_conn = st.session_state.get("_last_conn", 0)
    if conn_count[0] != last_conn:
        st.session_state._last_conn = conn_count[0]
        st.session_state.perception_history = []
        st.session_state.pop("last_manager_state", None)

    live_state = None
    if not q.empty():
        live_state = q.get_nowait()
        st.session_state.last_manager_state = live_state
        p = live_state.get("perception", {})
        if p:
            st.session_state.perception_history.append(_flatten_perception(p))
    elif "last_manager_state" in st.session_state:
        live_state = st.session_state.last_manager_state

    with st.container(border=True):
        st.subheader("Live — Manager State")
        if live_state is None:
            st.info("Manager não conectado. Aguardando ws://localhost:8001...")
        else:
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Episode", live_state.get("episode", "—"))
            col_b.metric("Step",    live_state.get("step",    "—"))
            col_c.metric("Situation", live_state.get("situation", "—"))

            col_d, col_e = st.columns(2)
            col_d.metric("Strategy", live_state.get("strategy", "—"))

            perception = live_state.get("perception", {})
            if perception:
                with st.expander("Perception", expanded=True):
                    def fmt3(v): return f"[{v[0]:+.3f}, {v[1]:+.3f}, {v[2]:+.3f}]" if v else "—"
                    def fmt7(v): return "  ".join(f"{x:+.3f}" for x in v) if v else "—"

                    # ── Tarefa / Resultado ────────────────────────────────
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Task",      perception.get("current_task", "—"))
                    c2.metric("Reward",    f"{perception.get('reward', 0):+.4f}")
                    c3.metric("Success",   str(perception.get("is_success", "—")))
                    c4.metric("Fingers",   f"{perception.get('fingers_width', 0):.3f} m")

                    st.divider()

                    # ── End-Effector ──────────────────────────────────────
                    c1, c2 = st.columns(2)
                    c1.markdown(f"**EE Position** `{fmt3(perception.get('ee_position', []))}`")
                    c2.markdown(f"**EE Velocity** `{fmt3(perception.get('ee_velocity', []))}`")

                    # ── Cubo ──────────────────────────────────────────────
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**Cube Position** `{fmt3(perception.get('cube_position', []))}`")
                    c2.markdown(f"**Cube Rotation** `{fmt3(perception.get('cube_rotation', []))}`")
                    c3.markdown(f"**Cube Lin. Vel.** `{fmt3(perception.get('cube_linear_velocity', []))}`")

                    # ── Target ────────────────────────────────────────────
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**Target Position** `{fmt3(perception.get('target_position', []))}`")
                    c2.metric("Dist EE→Cube",    f"{perception.get('dist_ee_to_cube', 0):.4f} m")
                    c3.metric("Dist Cube→Target", f"{perception.get('dist_cube_to_target', 0):.4f} m")

                    st.divider()

                    # ── Ação ──────────────────────────────────────────────
                    action = perception.get("action", [])
                    if action:
                        st.markdown(f"**Action** `{[round(x, 3) for x in action]}`")

                    # ── Juntas ────────────────────────────────────────────
                    angles = perception.get("joint_angles", [])
                    vels   = perception.get("joint_velocities", [])
                    if angles:
                        st.markdown(f"**Joint Angles** `{fmt7(angles)}`")
                    if vels:
                        st.markdown(f"**Joint Velocities** `{fmt7(vels)}`")

                    st.divider()

                    # ── Obstáculos ────────────────────────────────────────
                    c1, c2 = st.columns(2)
                    c1.metric("Obstacle in Path", str(perception.get("obstacle_in_path", False)))
                    c2.metric("Obstacle Count",   perception.get("obstacle_count_in_path", 0))

                    # ── Objetos / Cena / Config ───────────────────────────
                    if perception.get("objects"):
                        with st.expander("Objects"):
                            st.json(perception["objects"])
                    if perception.get("obstacles"):
                        with st.expander("Obstacles"):
                            st.json(perception["obstacles"])
                    if perception.get("target_goal"):
                        with st.expander("Target Goal"):
                            st.json(perception["target_goal"])
                    if perception.get("scene"):
                        with st.expander("Scene"):
                            st.json(perception["scene"])
                    if perception.get("robot_config"):
                        with st.expander("Robot Config"):
                            st.json(perception["robot_config"])
                    if perception.get("scripts"):
                        st.markdown(f"**Scripts** `{list(perception['scripts'].keys())}`")

# ── Main canvas ───────────────────────────────────────────────────────────────

with st.container(border=True):
    st.subheader("ASM")

    COLS = 2
    SPACING_X = 380
    SPACING_Y = 260

    _COLORS = {
        "predefined": {
            "background": "#1E3A5F", "border": "#4C9BE8",
            "highlight":  {"background": "#2A5298", "border": "#6BB3F0"},
        },
        "adaptive": {
            "background": "#3D3000", "border": "#FFD700",
            "highlight":  {"background": "#5C4800", "border": "#FFE84D"},
        },
    }

    num_scenarios = len(st.session_state.scenarios)
    total_rows    = max(1, (num_scenarios + COLS - 1) // COLS)
    center_x      = int((COLS - 1) * SPACING_X / 2)

    # Nós estruturais sempre presentes
    asm_nodes = [
        Node(
            id="__init__",
            label="",
            shape="dot",
            size=14,
            x=center_x,
            y=-SPACING_Y,
            color={
                "background": "#000000", "border": "#000000",
                "highlight":  {"background": "#444444", "border": "#444444"},
            },
        ),
        Node(
            id="__end__",
            label="●",
            shape="circle",
            size=20,
            x=center_x,
            y=total_rows * SPACING_Y,
            color={
                "background": "#FFFFFF", "border": "#000000",
                "highlight":  {"background": "#F0F0F0", "border": "#333333"},
            },
            font={"size": 16, "color": "#000000"},
            borderWidth=4,
        ),
    ]

    for i, (sid, s) in enumerate(st.session_state.scenarios.items()):
        col = i % COLS
        row = i // COLS
        stype = s.get("type", "predefined")
        asm_nodes.append(
            Node(
                id=sid,
                label=make_label(s),
                shape="box",
                x=col * SPACING_X,
                y=row * SPACING_Y,
                color=_COLORS[stype],
                font={"size": 13, "color": "#FFFFFF", "face": "monospace", "align": "left"},
            )
        )

    if not st.session_state.scenarios:
        st.caption("Add scenarios in the sidebar. Connect them to ● Init and ◎ End via Transitions.")

    asm_edges = [
        Edge(source=t["from"], target=t["to"], directed=True,
             color={"color": "#4C9BE8"}, arrows="to")
        for t in st.session_state.transitions
    ]

    agraph(nodes=asm_nodes, edges=asm_edges, config=Config(
        width="100%", height=600, directed=True,
        physics=False, hierarchical=False, nodeHighlightBehavior=True,
    ))

    st.markdown(
        '<span style="display:inline-block;width:12px;height:12px;background:#000;border-radius:50%;vertical-align:middle;margin-right:5px"></span>'
        '<span style="vertical-align:middle;margin-right:16px">Init</span>'
        '<span style="display:inline-block;width:14px;height:14px;background:#fff;border:3px solid #000;border-radius:50%;vertical-align:middle;margin-right:5px"></span>'
        '<span style="vertical-align:middle;margin-right:16px">End</span>'
        '<span style="display:inline-block;width:14px;height:14px;background:#1E3A5F;border:2px solid #4C9BE8;border-radius:3px;vertical-align:middle;margin-right:5px"></span>'
        '<span style="vertical-align:middle;margin-right:16px">Predefined</span>'
        '<span style="display:inline-block;width:14px;height:14px;background:#3D3000;border:2px solid #FFD700;border-radius:3px;vertical-align:middle;margin-right:5px"></span>'
        '<span style="vertical-align:middle">Adaptive</span>',
        unsafe_allow_html=True,
    )

live_panel()

# ── Trace histórico ───────────────────────────────────────────────────────────
@st.fragment(run_every=0.1)
def trace_panel():
    import pandas as pd
    with st.container(border=True):
        col_title, col_btn = st.columns([5, 1])
        col_title.subheader("Trace — Histórico de Steps")
        if col_btn.button("🗑 Limpar", use_container_width=True):
            st.session_state.perception_history = []

        if not st.session_state.perception_history:
            st.info("Nenhum step recebido ainda.")
        else:
            df = pd.DataFrame(st.session_state.perception_history)
            st.dataframe(df, use_container_width=True, height=300)

trace_panel()
