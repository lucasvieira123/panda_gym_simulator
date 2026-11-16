import json, glob, math, sys
import numpy as np
sys.stdout.reconfigure(encoding="utf-8")
def R(r,p,y):
    cr,sr,cp,sp,cy,sy=math.cos(r),math.sin(r),math.cos(p),math.sin(p),math.cos(y),math.sin(y)
    return np.array([[cy*cp,cy*sp*sr-sy*cr,cy*sp*cr+sy*sr],[sy*cp,sy*sp*sr+cy*cr,sy*sp*cr-cy*sr],[-sp,cp*sr,cp*cr]])
def mis(rot):
    M=R(*rot); return math.degrees(math.acos(min(1,max(abs(M[1,i]) for i in range(3)))))
order=["e1_0_155","e1_0_145","e1_0_14","e1_0_135","e1_0_10","e1_0_06","e1_0_04","e1_0_02","e1_0_01","e1_0_13","e1_0_16"]
for n in order:
    d="5-experiments/results/"+n
    o=json.load(open(d+"/outcome.json",encoding="utf-8"))
    T=[json.loads(l) for f in glob.glob(d+"/outputs/managing_traces/ticks_*.jsonl") for l in open(f,encoding="utf-8")]
    T=[t for t in T if t["event"]=="tick"]
    ar=o["adaptation_result"]; ph=o["physical"]; v=o["violation"] or {}
    print(f"\n## mu={o['lateral_friction']} viol={v.get('active_scenario')}@{v.get('step')} result={ar['status']}/{ar['reason']} (eval_ticks={ar.get('ticks')},task_ticks={ar.get('run_ticks')}) goal={ph.get('global_goal_achieved')} evolved={o['asm_evolved']} dist={ph['dist_cube_to_target_m']*100:.1f}cm end_step={o['sequence']['last_step']} dur={o['run']['duration_s']}s rc={o['run']['managing_exit_code']}")
    print("   diag:",(o["diagnosis"] or {}).get("diagnostic_conditions"),"| top:",[(x["candidate"][:12],round(x["score"],3)) for x in (o["ranking"] or {}).get("ranking",[])][:2])
    # 1a pegada: perda de contato
    first=next((t for t in T if t["finger_contacts"]==2),None)
    lost=next((t for t in T if first and t["step"]>first["step"] and t["finger_contacts"]<2),None)
    if lost:
        h=[t for t in T if first["step"]<=t["step"]<lost["step"]]
        print(f"   1a pegada: contato {first['step']}→{lost['step']} sub={lost['current_subtask']}/{lost['task_phase']} h_max={max((t['cube_position'][2]-.02)*100 for t in h):.1f}cm F={[round(x) for x in h[-1]['finger_normal_forces']]} slip_ee_cubo={(h[-1]['ee_position'][2]-h[-1]['cube_position'][2]-(h[0]['ee_position'][2]-h[0]['cube_position'][2]))*1000:+.0f}mm")
    vac=[t for t in T if t["current_task"]=="VACUUM_ASSIST"]
    if not vac: print("   sem vacuum"); continue
    v0=vac[0]; print(f"   vacuum inicio: step {v0['step']} cubo={[round(x,3) for x in v0['cube_position']]} desal={mis(v0['cube_rotation']):.0f}° vel={math.hypot(*v0['cube_linear_velocity']):.2f}m/s ee-cubo={v0['dist_ee_to_cube']*100:.0f}cm")
    i=next((k for k,t in enumerate(T) if t["current_task"]=="VACUUM_ASSIST" and t["action"][3]<0),None)
    if i is None:
        print(f"   nunca fechou: fases={sorted(set(t['task_phase'] for t in vac))} ticks={len(vac)} cubo_final={[round(x,2) for x in T[-1]['cube_position']]}"); continue
    c=T[i]; err=[(c["ee_position"][a]-c["cube_position"][a]-(0.025 if a==2 else 0))*1000 for a in range(3)]
    print(f"   fechar: step {c['step']} erro_alvo xyz={[round(e) for e in err]}mm norma={np.linalg.norm(err):.0f}mm desal={mis(c['cube_rotation']):.1f}° vel={math.hypot(*c['cube_linear_velocity']):.2f}m/s cubo_z={c['cube_position'][2]:.3f}")
    print("   t+k (fase c largura F zcubo zee vel desal):")
    for k in range(0,10):
        if i+k>=len(T): break
        t=T[i+k]; print(f"      +{k} {t['task_phase'][:7]:7} c={t['finger_contacts']} w={t['fingers_width']*100:4.1f} F={[round(x) for x in t['finger_normal_forces']]} z={t['cube_position'][2]:.3f} ee={t['ee_position'][2]:.3f} v={math.hypot(*t['cube_linear_velocity']):.2f} d={mis(t['cube_rotation']):.0f}°")
    post=T[i:]
    held=[t for t in post if t["finger_contacts"]==2]
    print(f"   apos fechar: ticks_c2={len(held)} h_max={max((t['cube_position'][2]-.02)*100 for t in post):.1f}cm final_c={T[-1]['finger_contacts']}")
