import json, glob, sys, re, datetime as dt
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
base="5-experiments/results/"; arch="5-experiments/RQ1.1/etapa0/results/"
def ticks(d):
    T=[json.loads(l) for f in glob.glob(d+"/outputs/managing_traces/ticks_*.jsonl") for l in open(f,encoding="utf-8")]
    return [t for t in T if t["event"]=="tick"]
def events(d): return [json.loads(l) for f in glob.glob(d+"/outputs/dejavu_traces/events_*.jsonl") for l in open(f,encoding="utf-8")]
def stamps(d):
    txt="\n".join(open(f,encoding="utf-8",errors="replace").read() for f in glob.glob(d+"/outputs/manager_traces/*.log"))
    return re.findall(r"\[step=\s*(\d+) (\d\d:\d\d:\d\d\.\d+)\]\[Manager\]\[DejaVu\] Adaptação", txt)
print("== Temporizacao da adaptacao (violacao -> selecionado, ultimo tick antes da task)")
for lbl,d in (("0.13 e1 (76)",base+"e1_0_13"),("0.13 e0 (75)",arch+"e0_0_130"),("0.13 q5 (75)",arch+"q5_0_130"),("0.16 e1",base+"e1_0_16"),("0.04 e1",base+"e1_0_04")):
    E=events(d); v=next(e for e in E if e["event"]=="violation"); a=next(e for e in E if e["event"]=="adaptation_selected")
    f=lambda s:dt.datetime.fromisoformat(s)
    T=ticks(d); first=next(t["step"] for t in T if t["current_task"]=="VACUUM_ASSIST")
    print(f"  {lbl:14} viol@{v['step']} pipeline={(f(a['time'])-f(v['time'])).total_seconds():.2f}s  1o_tick_vacuum={first}  manager_adapt={stamps(d)}")
    t_prev=[t for t in T if v['step']-1<=t['step']<=first]
    print("     steps:",[(t['step'],t['current_subtask'][:9],round(t['action'][2],2)) for t in t_prev])
print("== Tick anterior ao fechamento (quando o limiar foi cruzado)")
for n in ("e1_0_155","e1_0_145","e1_0_14","e1_0_135","e1_0_10","e1_0_06","e1_0_04","e1_0_02","e1_0_13","e1_0_16"):
    T=ticks(base+n); i=next(k for k,t in enumerate(T) if t["current_task"]=="VACUUM_ASSIST" and t["action"][3]<0)
    p,c=T[i-1],T[i]
    e=lambda t:np.linalg.norm([t["ee_position"][a]-t["cube_position"][a]-(0.025 if a==2 else 0) for a in range(3)])*1000
    print(f"  {n[3:]:6} t-1: fase={p['task_phase']:8} erro={e(p):4.0f}mm ee_z={p['ee_position'][2]:.3f} | fechar: ee_z={c['ee_position'][2]:.3f} topo_cubo~{c['cube_position'][2]+0.02:.3f} w={c['fingers_width']*100:.1f} c={c['finger_contacts']}")
print("== Queda em 0.135 e transporte nos controles")
for n in ("e1_0_135","e1_0_16"):
    T=ticks(base+n); i=next(k for k,t in enumerate(T) if t["current_task"]=="VACUUM_ASSIST" and t["action"][3]<0)
    prev=None
    for t in T[i:]:
        s=(t["finger_contacts"],t["current_subtask"][:9])
        if s!=prev:
            print(f"  {n[3:]} step {t['step']:3} {t['current_subtask'][:12]:12}/{t['task_phase']:7} c={t['finger_contacts']} w={t['fingers_width']*100:4.1f} z={t['cube_position'][2]:.3f} dist={t['dist_cube_to_target']*100:5.1f} eeZ-cuboZ={(t['ee_position'][2]-t['cube_position'][2])*1000:+.0f}mm")
            prev=s
    H=[t for t in T[i:] if t["finger_contacts"]==2 and t["current_subtask"].startswith("TRANSPORT")]
    print("    deslize no transporte eeZ-cuboZ inicio/fim mm:",round((H[0]['ee_position'][2]-H[0]['cube_position'][2])*1000),round((H[-1]['ee_position'][2]-H[-1]['cube_position'][2])*1000),"ticks",len(H))
print("== Deteccao: step da 1a evidencia (fim da task) x step do resultado")
for n in ("e1_0_155","e1_0_145","e1_0_14","e1_0_10","e1_0_06","e1_0_04","e1_0_02"):
    T=ticks(base+n); E=events(base+n)
    d=next(t for t in T if t["current_task"]=="VACUUM_ASSIST" and t["task_phase"]=="DONE")
    r=[e for e in E if e["event"]=="evaluation" and e.get("reason")][-1]
    v=next(t for t in T if t["step"]==r["step"])
    print(f"  {n[3:]:6} fim_task={d['step']} c={d['finger_contacts']} h={(d['cube_position'][2]-.02)*100:.1f} resultado={r['step']} ee_ate_alvo_no_resultado={((v['ee_position'][0]-v['target_position'][0])**2+(v['ee_position'][1]-v['target_position'][1])**2)**.5*100:.0f}cm fase={v['current_subtask'][:9]}/{v['task_phase']} cubo_mesa={abs(v['cube_position'][2]-0.02)<0.01}")
