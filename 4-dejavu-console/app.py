import json
import queue
import threading

import streamlit as st
from websockets.sync.client import connect as ws_connect

import state
from sidebar import render as render_sidebar
from views import catalogue, checked, similarities, state_machine

_DEJAVU_WS_URL = "ws://localhost:8002/ws/state"


# ── WebSocket receiver (background thread) ────────────────────────────────────

def _ws_receiver(q: queue.Queue, browser_ready: threading.Event) -> None:
    import time
    browser_ready.wait(timeout=60.0)
    while True:
        try:
            with ws_connect(_DEJAVU_WS_URL) as ws:
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
    q = queue.Queue(maxsize=1)
    browser_ready = threading.Event()
    call_count = [0]
    threading.Thread(target=_ws_receiver, args=(q, browser_ready), daemon=True).start()
    return q, browser_ready, call_count


# ── App ───────────────────────────────────────────────────────────────────────

st.set_page_config(layout="wide", page_title="DejaVu Console")

state.init()

with st.sidebar:
    render_sidebar()

st.title(f"DejaVu Console — {st.session_state.dj_catalogue_name}")

state_machine.render()

st.divider()
catalogue.render()

st.divider()


@st.fragment(run_every=0.5)
def live_panel():
    q, browser_ready, call_count = _get_shared_state()
    call_count[0] += 1
    if call_count[0] == 2:
        browser_ready.set()

    if not q.empty():
        st.session_state.dj_live = q.get_nowait()
        st.session_state.pop("_dj_live_frozen", None)
    elif "dj_live" in st.session_state and st.session_state.dj_live is not None:
        pass  # mantém o último estado recebido

    live = st.session_state.get("dj_live")

    # ── Live state container ──────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Live — DejaVu State")

        if live is None:
            st.info("DejaVu não conectado. Aguardando ws://localhost:8002...")
        else:
            p = live.get("new_perception", {})

            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Episode",     live.get("episode", "—"))
            col_b.metric("Step",        live.get("step",    "—"))
            col_c.metric("Subtask",     p.get("current_subtask", live.get("current_subtask", "—")))

            col_d, col_e, col_f = st.columns(3)
            col_d.metric("SM State",    live.get("active_sm_state",  "—"))
            col_e.metric("SM Status",   live.get("sm_status",        "—"))
            col_f.metric("Unanticipated", str(live.get("unanticipated", "—")))

            if p:
                with st.expander("New Perception", expanded=True):
                    # ── Task / Result ─────────────────────────────────────
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Task",    p.get("current_task", "—"))
                    c2.metric("Reward",  f"{p.get('reward', 0):+.4f}")
                    c3.metric("Success", str(p.get("is_success", "—")))
                    c4.metric("Fingers", f"{p.get('fingers_width', 0):.3f} m")

                    st.divider()

                    # ── ASM processed params ──────────────────────────────
                    st.markdown("**ASM Params**")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("gripper_width_cm",      p.get("gripper_width_cm", "—"))
                    c2.metric("grasp_completed",       p.get("grasp_completed",  "—"))
                    c3.metric("finger_contacts",       p.get("finger_contacts",  "—"))
                    c4.metric("object_available",      p.get("object_available", "—"))

                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("dist_ee_object_cm",     p.get("distance_ee_object_cm",   "—"))
                    c2.metric("dist_obj_goal_cm",      p.get("distance_object_goal_cm", "—"))
                    c3.metric("lift_height_cm",        p.get("object_lift_height_cm",   "—"))
                    c4.metric("grasp_attempts",        p.get("grasp_attempts",          "—"))

                    st.divider()

                    # ── Positions ─────────────────────────────────────────
                    def _f3(x, y, z): return f"[{x:+.3f}, {y:+.3f}, {z:+.3f}]"

                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"**EE** `{_f3(p.get('ee_x',0), p.get('ee_y',0), p.get('ee_z',0))}`")
                    c2.markdown(f"**Cube** `{_f3(p.get('cube_x',0), p.get('cube_y',0), p.get('cube_z',0))}`")
                    c3.markdown(f"**Target** `{_f3(p.get('target_x',0), p.get('target_y',0), p.get('target_z',0))}`")

                    # ── Action ────────────────────────────────────────────
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("action_x",       f"{p.get('action_x', 0):+.3f}")
                    c2.metric("action_y",       f"{p.get('action_y', 0):+.3f}")
                    c3.metric("action_z",       f"{p.get('action_z', 0):+.3f}")
                    c4.metric("action_gripper", f"{p.get('action_gripper', 0):+.3f}")

                    # ── Joints ────────────────────────────────────────────
                    angles = "  ".join(f"{p.get(f'j{i}', 0):+.3f}" for i in range(7))
                    vels   = "  ".join(f"{p.get(f'jv{i}', 0):+.3f}" for i in range(7))
                    st.markdown(f"**Joint Angles** `{angles}`")
                    st.markdown(f"**Joint Vels**   `{vels}`")

                    st.divider()

                    # ── Dicts ─────────────────────────────────────────────
                    if p.get("objects"):
                        with st.expander("Objects"):
                            st.json(p["objects"])
                    if p.get("obstacles"):
                        with st.expander("Obstacles"):
                            st.json(p["obstacles"])
                    if p.get("target_goal"):
                        with st.expander("Target Goal"):
                            st.json(p["target_goal"])
                    if p.get("scene"):
                        with st.expander("Scene"):
                            st.json(p["scene"])

    st.divider()

    # ── Similarities & Checked (live-aware) ───────────────────────────────────
    st.subheader("Similarities")
    similarities.render()

    st.divider()

    st.subheader("Checked Scenarios")
    checked.render()


live_panel()
