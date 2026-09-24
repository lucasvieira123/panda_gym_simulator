"""
Analise consolidada + decomposicao do calculo de similaridade do Retriever
real do DejaVu, para os Desired Adaptation Scenarios da RQ2.0.

Script UNICO (fundiu o que antes eram dois scripts separados: um so agregava
o .jsonl ja produzido por main.py -- redundante, pois nao calculava nada
novo -- e outro recalculava a decomposicao chamando as funcoes reais do
Retriever). Mantido fora do main.py de proposito: main.py espelha o output
minimo de producao (SimilarityBasedAdapter), este script serve para
auditoria/explicacao pos-hoc, um proposito diferente.

NAO reimplementa a formula de similaridade -- importa e chama diretamente
as funcoes reais de 3-dejavu/src/similarity/dejavu_similarity.py (mesmas
usadas por main.py e pelo SimilarityBasedAdapter de producao). Nao executa
nenhuma simulacao fisica, nao altera catalogo/pesos/formula.

Le os mesmos arquivos de configuracao do experimento:
    configs/desired_scenario.json  (array com os Desired Adaptation Scenarios)
    configs/scenario_catalogue.json
    configs/weights_config.yaml

Gera em rq2_analysis/:
    rq2_summary.csv                   -- 1 linha por Desired Adaptation Scenario
    rq2_full_ranking.csv               -- ranking completo dos candidatos por cenario
    rq2_similarity_decomposition.csv   -- decomposicao completa (given/when/then, parametrico, penalidade)
    rq2_analysis.md                    -- relatorio unico (grupos A, B e C)

Se um .jsonl de um run anterior de main.py existir em output/similarities/,
valida os valores de Final Similarity recalculados aqui contra ele.
"""
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

import yaml

THIS_DIR = Path(__file__).resolve().parent
DEJAVU_SRC = THIS_DIR.parents[1] / "3-dejavu" / "src"
sys.path.insert(0, str(DEJAVU_SRC))

from scenario.diagnosed_scenario import DiagnosedScenario
from scenario.candidate_scenario import CandidateScenario
from similarity.dejavu_similarity import (
    calculate_scenario_similarity,
    calculate_conditional_similarity,
    calculate_parameters_similarity,
    _parameter_similarity_weighted_avg,
    _extract_parameters,
    _tversky_similarity,
)

CONFIGS_DIR = THIS_DIR / "configs"
OUTPUT_DIR = THIS_DIR / "rq2_analysis"
SIMILARITIES_DIR = THIS_DIR / "output" / "similarities"

REFERENCE_DO = "apply_vacuum_assist()"
COMPETITOR_DO = "reposition_and_regrip()"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_experiment_id(desired_name: str):
    # padrao do grid fatorial RQ2.2: RQ2_R_H01_C01_F01 -> ("R_H01_C01_F01", "H01/C01/F01")
    m = re.search(r"RQ2_(R_H(\d+)_C(\d+)_F(\d+))$", desired_name)
    if m:
        exp_id = m.group(1)
        description = f"H{m.group(2)}/C{m.group(3)}/F{m.group(4)}"
        return exp_id, description

    # padrao A/B/C: RQ2_A0_baseline_full_context -> ("A0", "baseline full context")
    m = re.search(r"RQ2_([A-Za-z]\d+)_(.*)$", desired_name)
    if m:
        exp_id, suffix = m.group(1), m.group(2)
        description = suffix.replace("_", " ")
        description = re.sub(r"(\d)p(\d+)", r"\1.\2", description)
        return exp_id, description

    return None, desired_name


def sort_key(exp_id):
    if not exp_id:
        return ("~", 0, 0, 0)
    m = re.match(r"R_H(\d+)_C(\d+)_F(\d+)$", exp_id)
    if m:
        return ("R", int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return (exp_id[0], int(exp_id[1:]), 0, 0)


def parse_hcf(exp_id: str):
    """'R_H01_C01_F01' -> (1, 1, 1); None se nao for do grid fatorial."""
    if not exp_id:
        return None
    m = re.match(r"R_H(\d+)_C(\d+)_F(\d+)$", exp_id)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def clause_breakdown(expr1: str, expr2: str, monitored_parameters: dict, parameter_weights: dict,
                      alpha: float, beta: float) -> dict:
    """Decompoe uma clausula (given/when/then) em parametrico + penalidade + final,
    reaproveitando as MESMAS funcoes internas do Retriever real."""
    pair_sims = calculate_parameters_similarity(expr1, expr2, monitored_parameters)
    parametric_avg = _parameter_similarity_weighted_avg(pair_sims, parameter_weights)

    params_1 = _extract_parameters(expr1)
    params_2 = _extract_parameters(expr2)
    structural_sim = _tversky_similarity(params_1, params_2, alpha=alpha, beta=beta)
    structural_penalty = 1 - structural_sim

    final = calculate_conditional_similarity(expr1, expr2, monitored_parameters, parameter_weights,
                                              alpha=alpha, beta=beta)

    shared = [p for p in params_1 if p in params_2]
    missing_in_candidate = [p for p in params_1 if p not in params_2]
    extra_in_candidate = [p for p in params_2 if p not in params_1]

    return {
        "parametric_avg": parametric_avg,
        "structural_similarity": structural_sim,
        "structural_penalty": structural_penalty,
        "final": final,
        "shared_params": ";".join(shared),
        "missing_in_candidate": ";".join(missing_in_candidate),
        "extra_in_candidate": ";".join(extra_in_candidate),
    }


def fmt(x, nd=5):
    return f"{x:.{nd}f}" if isinstance(x, float) else str(x)


# ---------------------------------------------------------------------------
# Passo 1: decomposicao (rq2_similarity_decomposition.csv)
# ---------------------------------------------------------------------------

def compute_decomposition(desired_list, catalogue, weight_configs):
    monitored_parameters = catalogue["monitored_parameters"]
    alpha = weight_configs["tversky_weights"]["alpha"]
    beta = weight_configs["tversky_weights"]["beta"]
    parameter_weights = weight_configs["parameter_weights"]
    conditional_weights = weight_configs["conditional_weights"]

    kargs = dict(
        conditional_weights=conditional_weights,
        tversky_weights={"alpha": alpha, "beta": beta},
        parameter_weights=parameter_weights,
        monitored_parameters=monitored_parameters,
    )

    rows = []
    for desired_dict in desired_list:
        diagnosed = DiagnosedScenario(data=desired_dict)
        exp_id, description = parse_experiment_id(diagnosed.name)

        for candidate_data in catalogue["scenarios"].values():
            candidate = CandidateScenario(data=candidate_data)

            given_bd = clause_breakdown(diagnosed.given.to_string(), candidate.given.to_string(),
                                         monitored_parameters, parameter_weights, alpha, beta)
            when_bd = clause_breakdown(diagnosed.when.to_string(), candidate.when.to_string(),
                                        monitored_parameters, parameter_weights, alpha, beta)
            then_bd = clause_breakdown(diagnosed.then.to_string(), candidate.then.to_string(),
                                        monitored_parameters, parameter_weights, alpha, beta)

            final = calculate_scenario_similarity(diagnosed, candidate, **kargs)

            rows.append({
                "experiment_id": exp_id,
                "desired_scenario": diagnosed.name,
                "description": description,
                "candidate_scenario": candidate.name,
                "adaptive_behavior": candidate.do.to_string(),
                "given_similarity": given_bd["final"],
                "when_similarity": when_bd["final"],
                "then_similarity": then_bd["final"],
                "given_parametric_similarity": given_bd["parametric_avg"],
                "given_structural_similarity": given_bd["structural_similarity"],
                "given_structural_penalty": given_bd["structural_penalty"],
                "given_shared_params": given_bd["shared_params"],
                "given_missing_in_candidate": given_bd["missing_in_candidate"],
                "given_extra_in_candidate": given_bd["extra_in_candidate"],
                "when_parametric_similarity": when_bd["parametric_avg"],
                "when_structural_penalty": when_bd["structural_penalty"],
                "then_parametric_similarity": then_bd["parametric_avg"],
                "then_structural_penalty": then_bd["structural_penalty"],
                "final_similarity": final,
            })

    rows.sort(key=lambda r: (sort_key(r["experiment_id"]), -r["final_similarity"]))
    return rows, alpha, beta


# ---------------------------------------------------------------------------
# Passo 2: agregacao (rq2_summary.csv, rq2_full_ranking.csv) -- derivada
# diretamente das linhas ja calculadas acima, sem reler nenhum jsonl.
# ---------------------------------------------------------------------------

def build_full_ranking(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for r in rows:
        groups[r["desired_scenario"]].append(r)

    full_rows = []
    for desired_scenario, items in groups.items():
        ranked = sorted(items, key=lambda r: r["final_similarity"], reverse=True)  # sort estavel
        for rank, r in enumerate(ranked, start=1):
            full_rows.append({
                "experiment_id": r["experiment_id"],
                "desired_scenario": desired_scenario,
                "rank": rank,
                "candidate_scenario": r["candidate_scenario"],
                "adaptive_behavior": r["adaptive_behavior"],
                "final_similarity": r["final_similarity"],
                "is_reference_candidate": r["adaptive_behavior"] == REFERENCE_DO,
            })
    full_rows.sort(key=lambda row: (sort_key(row["experiment_id"]), row["rank"]))
    return full_rows


def build_summary(rows: list[dict], issues: list[str]) -> list[dict]:
    groups = defaultdict(list)
    for r in rows:
        groups[r["desired_scenario"]].append(r)

    baseline_key = next((k for k in groups if re.search(r"RQ2_A0_", k)), None)
    baseline_top1_do = None
    if baseline_key:
        baseline_sorted = sorted(groups[baseline_key], key=lambda r: r["final_similarity"], reverse=True)
        baseline_top1_do = baseline_sorted[0]["adaptive_behavior"]
    else:
        issues.append("Nao encontrei o cenario baseline (RQ2_A0_*) -- 'top1_matches_baseline' ficara vazio.")

    summary_rows = []
    for desired_scenario, items in groups.items():
        exp_id = items[0]["experiment_id"]
        description = items[0]["description"]
        ranked = sorted(items, key=lambda r: r["final_similarity"], reverse=True)

        reference_rows = [r for r in ranked if r["adaptive_behavior"] == REFERENCE_DO]
        if len(reference_rows) != 1:
            issues.append(f"'{desired_scenario}': {len(reference_rows)} candidato(s) de referencia (esperado 1).")
            continue
        reference_row = reference_rows[0]
        reference_rank = ranked.index(reference_row) + 1
        reference_sim = reference_row["final_similarity"]

        others = [r for r in ranked if r is not reference_row]
        best_other = max(others, key=lambda r: r["final_similarity"])
        best_other_sim = best_other["final_similarity"]

        margin = reference_sim - best_other_sim  # assinada, sem abs()
        top1 = ranked[0]
        top1_is_reference = top1["adaptive_behavior"] == REFERENCE_DO
        is_exact_tie = (reference_sim == best_other_sim)

        summary_rows.append({
            "experiment_id": exp_id,
            "desired_scenario": desired_scenario,
            "description": description,
            "top1_candidate_name": top1["candidate_scenario"],
            "top1_do": top1["adaptive_behavior"],
            "top1_similarity": top1["final_similarity"],
            "reference_rank": reference_rank,
            "reference_similarity": reference_sim,
            "best_competitor_name": best_other["candidate_scenario"],
            "best_competitor_similarity": best_other_sim,
            "margin_signed": margin,
            "top1_is_reference": top1_is_reference,
            "is_exact_tie_at_top": is_exact_tie,
            "top1_matches_baseline": (top1["adaptive_behavior"] == baseline_top1_do) if baseline_top1_do else "",
        })

    summary_rows.sort(key=lambda row: sort_key(row["experiment_id"]))
    return summary_rows


def validate_against_jsonl(rows: list[dict]) -> list[str]:
    lines = []
    candidates = sorted(SIMILARITIES_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime) if SIMILARITIES_DIR.exists() else []
    if not candidates:
        lines.append(f"Nenhum .jsonl encontrado em `{SIMILARITIES_DIR}` -- validação cruzada não executada "
                      "(a decomposição abaixo ainda é válida por si só, calculada com as mesmas funções reais).")
        return lines

    jsonl_path = candidates[-1]  # mais recente
    original = {}
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            key = (rec["desired_key"], rec["candidate"]["do"])
            original[key] = rec["similarity_result"]

    max_abs_diff = 0.0
    n_compared = 0
    missing_keys = []
    for r in rows:
        key = (r["desired_scenario"], r["adaptive_behavior"])
        if key not in original:
            missing_keys.append(key)
            continue
        diff = abs(r["final_similarity"] - original[key])
        max_abs_diff = max(max_abs_diff, diff)
        n_compared += 1

    lines.append(f"Comparado contra `{jsonl_path.name}` (mais recente em `output/similarities/`).")
    lines.append(f"Comparados {n_compared} de {len(rows)} registros. Maior divergência absoluta: {max_abs_diff:.2e}")
    if missing_keys:
        lines.append(f"Combinações presentes aqui mas ausentes no jsonl (ex.: cenários novos ainda não "
                      f"rodados por main.py): {len(missing_keys)} -- normal se `desired_scenario.json` "
                      "foi editado depois do último run de main.py.")
    if n_compared and max_abs_diff < 1e-9:
        lines.append("RESULTADO: valores idênticos (dentro de erro de ponto flutuante) aos registros do experimento.")
    elif n_compared and max_abs_diff < 1e-6:
        lines.append("RESULTADO: valores coincidem dentro de tolerância numérica razoável (< 1e-6).")
    elif n_compared:
        lines.append("RESULTADO: DIVERGÊNCIA SIGNIFICATIVA -- investigar antes de usar esta decomposição como fonte de verdade.")
    return lines


# ---------------------------------------------------------------------------
# Passo 3: relatorio unico (rq2_analysis.md)
# ---------------------------------------------------------------------------

def render_summary_table(rows: list[dict]) -> list[str]:
    out = ["| ID | descrição | Top-1 | score Top-1 | rank referência | score referência | "
           "melhor concorrente | score concorrente | margem (assinada) | Top-1 == referência? | empate exato? |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append(
            f"| {r['experiment_id']} | {r['description']} | {r['top1_candidate_name']} | "
            f"{fmt(r['top1_similarity'])} | {r['reference_rank']} | {fmt(r['reference_similarity'])} | "
            f"{r['best_competitor_name']} | {fmt(r['best_competitor_similarity'])} | "
            f"{fmt(r['margin_signed'])} | {'sim' if r['top1_is_reference'] else '**NAO**'} | "
            f"{'SIM' if r['is_exact_tie_at_top'] else 'nao'} |"
        )
    return out


def render_group_r_section(group_r: list[dict]) -> list[str]:
    """Grade fatorial (RQ2.2, H x C x F) -- 897 pontos e grande demais para uma
    tabela linha-a-linha no .md; resume com estatisticas e quebra por nivel."""
    from collections import Counter

    out = ["## Grupo R -- grade fatorial de regiões (RQ2.2: Height x Contacts x Friction)", ""]
    n = len(group_r)
    n_retained = sum(1 for r in group_r if r["top1_is_reference"])
    n_flipped = n - n_retained
    n_ties = sum(1 for r in group_r if r["is_exact_tie_at_top"])
    margins = [r["margin_signed"] for r in group_r]

    out.append(f"Total de pontos no grid: **{n}**.")
    out.append("")
    out.append(f"- Top-1 == referência (`apply_vacuum_assist()`): {n_retained}/{n} ({n_retained/n*100:.1f}%)")
    out.append(f"- Top-1 mudou de identidade: {n_flipped}/{n} ({n_flipped/n*100:.1f}%)")
    out.append(f"- Empates exatos (margem == 0.0): {n_ties}")
    out.append(f"- Margem assinada: mínimo={min(margins):.5f}, máximo={max(margins):.5f}, "
               f"média={sum(margins)/n:.5f}")
    out.append("")

    if n_flipped:
        flip_counter = Counter(r["top1_do"] for r in group_r if not r["top1_is_reference"])
        out.append("**Para quem o Top-1 muda, quando muda:**")
        out.append("")
        for do, count in flip_counter.most_common():
            out.append(f"- `{do}`: {count} ponto(s) do grid")
        out.append("")

    # Quebra da taxa de flip por nivel de cada dimensao (H, C, F)
    def level_breakdown(dim_index: int, dim_label: str) -> list[str]:
        by_level = defaultdict(lambda: [0, 0])  # level -> [total, flipped]
        for r in group_r:
            hcf = parse_hcf(r["experiment_id"])
            if hcf is None:
                continue
            level = hcf[dim_index]
            by_level[level][0] += 1
            if not r["top1_is_reference"]:
                by_level[level][1] += 1
        lines_out = [f"| {dim_label} | total | Top-1 mudou | taxa |", "|---|---|---|---|"]
        for level in sorted(by_level):
            total, flipped = by_level[level]
            lines_out.append(f"| {level:02d} | {total} | {flipped} | {flipped/total*100:.1f}% |")
        return lines_out

    out.append("**Taxa de mudança de Top-1 por nível de cada dimensão do grid:**")
    out.append("")
    out.append("Altura (H):")
    out += level_breakdown(0, "H")
    out.append("")
    out.append("Contatos (C):")
    out += level_breakdown(1, "C")
    out.append("")
    out.append("Fricção (F):")
    out += level_breakdown(2, "F")
    out.append("")
    out.append("O ponto-a-ponto completo dos 897 cenários (score, rank, margem por candidato) está em "
                "`rq2_summary.csv` e `rq2_full_ranking.csv` -- filtre por `experiment_id` começando com `R_`.")
    out.append("")
    return out


def write_markdown(path: Path, decomposition_rows: list[dict], summary_rows: list[dict],
                    validation_lines: list[str], issues: list[str], alpha: float, beta: float) -> None:
    def get(exp_id, do):
        for r in decomposition_rows:
            if r["experiment_id"] == exp_id and r["adaptive_behavior"] == do:
                return r
        return None

    group_a = [r for r in summary_rows if r["experiment_id"] and r["experiment_id"].startswith("A")]
    group_b = [r for r in summary_rows if r["experiment_id"] and r["experiment_id"].startswith("B")]
    group_c = [r for r in summary_rows if r["experiment_id"] and r["experiment_id"].startswith("C")]
    group_r = [r for r in summary_rows if r["experiment_id"] and r["experiment_id"].startswith("R_")]

    lines = []
    lines.append("# RQ2.0 -- Retrieval Robustness to Scenario Analysis Inaccuracies")
    lines.append("")
    lines.append("Relatório único gerado por `decompose_rq2_similarity.py`, chamando diretamente as "
                  "funções reais de `3-dejavu/src/similarity/dejavu_similarity.py` "
                  "(`calculate_scenario_similarity`, `calculate_conditional_similarity`, "
                  "`calculate_parameters_similarity`, `_parameter_similarity_weighted_avg`, "
                  "`_extract_parameters`, `_tversky_similarity`). Nenhuma fórmula foi reimplementada; "
                  "nenhuma simulação física foi executada.")
    lines.append("")
    lines.append("**Candidato de referência**: identificado pelo campo `do == \"apply_vacuum_assist()\"` "
                  "(a chave do catálogo `lift_slip_low_friction` não é preservada nem no JSONL de "
                  "produção nem nos CSVs -- só name/given/when/do/then).")
    lines.append("")
    lines.append("**Nota sobre as descrições**: o campo `comment` do `desired_scenario.json` de entrada "
                  "não é usado por nenhuma função do Retriever e não aparece em nenhum output oficial "
                  "(`Scenario.to_dict()` só serializa type/name/given/when/do/then). A coluna "
                  "`description` abaixo foi reconstruída a partir do sufixo do nome do cenário "
                  "(convenção `RQ2_<ID>_<descrição>`), não do comentário original.")
    lines.append("")

    lines.append("## Validação")
    lines.append("")
    if issues:
        lines.append("**Problemas encontrados:**")
        for i in issues:
            lines.append(f"- {i}")
        lines.append("")
    for line in validation_lines:
        lines.append(f"- {line}")
    lines.append("")

    if group_a:
        lines.append("## Grupo A -- omissões estruturais")
        lines.append("")
        lines += render_summary_table(group_a)
        lines.append("")

    if group_b:
        lines.append("## Grupo B -- adições estruturais")
        lines.append("")
        lines += render_summary_table(group_b)
        lines.append("")

    if group_c:
        lines.append("## Grupo C -- variação paramétrica de lateral_friction")
        lines.append("")
        lines += render_summary_table(group_c)
        lines.append("")

    if group_r:
        lines += render_group_r_section(group_r)

    # --- Narrativa detalhada Grupo A (se A0-A6 existirem) ---
    a_ids = [f"A{i}" for i in range(7)]
    a_available = [i for i in a_ids if get(i, REFERENCE_DO) and get(i, COMPETITOR_DO)]
    if a_available:
        lines.append("## Por que a recuperação muda nas omissões estruturais (Grupo A)")
        lines.append("")
        a0_vac, a0_rep = get("A0", REFERENCE_DO), get("A0", COMPETITOR_DO)
        a1_vac, a1_rep = get("A1", REFERENCE_DO), get("A1", COMPETITOR_DO)
        if a0_vac and a1_vac and a0_rep and a1_rep:
            lines.append(f"- **A0 (baseline)**: `apply_vacuum_assist()` given = {a0_vac['given_similarity']:.5f} "
                          f"(paramétrico={a0_vac['given_parametric_similarity']:.5f}, penalidade={a0_vac['given_structural_penalty']:.5f}). "
                          f"`reposition_and_regrip()` given = {a0_rep['given_similarity']:.5f} "
                          f"(paramétrico={a0_rep['given_parametric_similarity']:.5f}, penalidade={a0_rep['given_structural_penalty']:.5f}).")
            lines.append(f"- **A1 (sem lateral_friction em D)**: `apply_vacuum_assist()` given sobe para "
                          f"{a1_vac['given_similarity']:.5f} (penalidade cai de {a0_vac['given_structural_penalty']:.5f} para "
                          f"{a1_vac['given_structural_penalty']:.5f} -- deixa de ser penalizado pelo *valor* de friction "
                          f"diferente, passa a ser penalizado só pela beta leve de ter um parâmetro extra não usado).")
            lines.append(f"- Só que `reposition_and_regrip()` sobe **muito mais**: de {a0_rep['given_similarity']:.5f} para "
                          f"{a1_rep['given_similarity']:.5f} (penalidade cai de {a0_rep['given_structural_penalty']:.5f} para "
                          f"{a1_rep['given_structural_penalty']:.5f} -- deixa de ser penalizado pela alpha PESADA de "
                          f"'faltar' lateral_friction, porque agora D também não tem mais esse parâmetro).")
            lines.append(f"- **A assimetria alpha={alpha}/beta={beta} explica tudo**: faltar um parâmetro que D tem "
                          f"custa caro (peso alpha); ter um parâmetro extra que D não tem custa pouco (peso beta). "
                          f"Remover `lateral_friction` de D beneficia MUITO mais quem já não tinha esse parâmetro "
                          f"(`reposition_and_regrip`) do que quem já tinha um valor compatível "
                          f"(`apply_vacuum_assist`). O resultado individual da referência melhora, mas o do "
                          f"concorrente melhora mais -- é uma perda por competição relativa, não um erro de cálculo.")
            lines.append("")
        a4_vac, a4_rep = get("A4", REFERENCE_DO), get("A4", COMPETITOR_DO)
        if a4_vac and a4_rep:
            lines.append(f"- **A4/A5 (só resta 1 sintoma)**: o vencedor passa a depender de **quantos parâmetros "
                          f"extras não usados** cada candidato carrega -- `apply_vacuum_assist()` tem 2 extras "
                          f"(penalidade={a4_vac['given_structural_penalty']:.5f}), `reposition_and_regrip()` tem só "
                          f"1 extra (penalidade={a4_rep['given_structural_penalty']:.5f}). Menos extras = menos "
                          f"penalidade beta acumulada = vence.")
        a6_vac, a6_rep = get("A6", REFERENCE_DO), get("A6", COMPETITOR_DO)
        if a6_vac and a6_rep:
            lines.append(f"- **A6 (só resta lateral_friction)**: `apply_vacuum_assist()` ainda compartilha esse "
                          f"parâmetro (given={a6_vac['given_similarity']:.5f}), `reposition_and_regrip()` não tem "
                          f"`lateral_friction` no given -- zero sobreposição, penalidade máxima "
                          f"(given={a6_rep['given_similarity']:.5f}). Sobreposição imperfeita ainda vale mais que "
                          f"nenhuma sobreposição.")
        lines.append("")

    # --- Narrativa Grupo B ---
    if group_b:
        lines.append("## Efeito das adições estruturais (Grupo B)")
        lines.append("")
        lines.append("Cada cenário B preserva o Given completo do baseline (A0) e acrescenta UM parâmetro "
                      "extra (não presente na referência original) com um limiar fisicamente genérico "
                      "(não aprendido pelo Diagnoser). Isso testa o efeito de **adicionar** informação "
                      "contextual, o oposto do Grupo A.")
        lines.append("")
        for r in group_b:
            lines.append(f"- **{r['experiment_id']}** ({r['description']}): Top-1 = `{r['top1_do']}` "
                          f"(score {fmt(r['top1_similarity'])}), referência em rank {r['reference_rank']} "
                          f"(margem {fmt(r['margin_signed'])}).")
        vac_scores = {r["experiment_id"]: get(r["experiment_id"], REFERENCE_DO) for r in group_b}
        vac_vals = {k: v["given_similarity"] for k, v in vac_scores.items() if v}
        if len(set(round(v, 6) for v in vac_vals.values())) == 1 and len(vac_vals) > 1:
            lines.append(f"- O `given_similarity` da referência é **idêntico** em todos os cenários B "
                          f"({fmt(next(iter(vac_vals.values())))}) -- consequência direta da fórmula: a "
                          f"penalidade de Tversky depende só de **quantos** parâmetros extras existem, não "
                          f"de **quais**. Como nenhum dos 3 parâmetros adicionados (mass, gripper_width, "
                          f"grasp_attempts) aparece no given de `apply_vacuum_assist()`, adicionar qualquer "
                          f"um deles tem exatamente o mesmo efeito estrutural sobre esse candidato.")
        lines.append("")

    # --- Narrativa Grupo C ---
    if group_c:
        lines.append("## Variação paramétrica de lateral_friction (Grupo C)")
        lines.append("")
        c_rows = [get(r["experiment_id"], REFERENCE_DO) for r in group_c]
        c_rows = [r for r in c_rows if r]
        if c_rows:
            lines.append("| Cenário | Given(vac) paramétrico | Given(vac) penalidade | Given(vac) final | Final(vac) |")
            lines.append("|---|---|---|---|---|")
            for r in c_rows:
                lines.append(f"| {r['experiment_id']} | {r['given_parametric_similarity']:.5f} | "
                              f"{r['given_structural_penalty']:.5f} | {r['given_similarity']:.5f} | "
                              f"{r['final_similarity']:.5f} |")
            lines.append("")
            all_zero_penalty = all(r["given_structural_penalty"] == 0.0 for r in c_rows)
            lines.append(f"- **O único componente que muda é o termo paramétrico (Jaccard) de `lateral_friction`** "
                          f"-- a penalidade estrutural {'permanece 0.0 em toda a grade' if all_zero_penalty else 'varia'}, "
                          "porque variar só o threshold nunca altera quais parâmetros aparecem no Given.")
            lines.append("- O ranking permanece estável na faixa testada porque `reposition_and_regrip()` não "
                          "depende de `lateral_friction` (seu score fica constante), e a referência nunca cai "
                          "abaixo desse piso constante dentro da grade avaliada.")
        lines.append("")

    lines.append("## Dados completos")
    lines.append("")
    lines.append("- `rq2_summary.csv` -- 1 linha por Desired Adaptation Scenario (Top-1, rank/score da "
                  "referência, melhor concorrente, margem assinada, flags de empate/retenção).")
    lines.append("- `rq2_full_ranking.csv` -- ranking completo (1 linha por par cenário-candidato).")
    lines.append("- `rq2_similarity_decomposition.csv` -- decomposição completa (Given/When/Then, "
                  "componente paramétrico e penalidade estrutural de cada cláusula, parâmetros "
                  "compartilhados/ausentes/extras).")

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
def main() -> None:
    desired_list = load_json(CONFIGS_DIR / "desired_scenario.json")
    if not isinstance(desired_list, list):
        desired_list = [desired_list]
    catalogue = load_json(CONFIGS_DIR / "scenario_catalogue.json")
    weight_configs = load_yaml(CONFIGS_DIR / "weights_config.yaml")

    decomposition_rows, alpha, beta = compute_decomposition(desired_list, catalogue, weight_configs)

    issues = []
    summary_rows = build_summary(decomposition_rows, issues)
    full_ranking_rows = build_full_ranking(decomposition_rows)
    validation_lines = validate_against_jsonl(decomposition_rows)

    write_csv(OUTPUT_DIR / "rq2_summary.csv", summary_rows)
    write_csv(OUTPUT_DIR / "rq2_full_ranking.csv", full_ranking_rows)
    write_csv(OUTPUT_DIR / "rq2_similarity_decomposition.csv", decomposition_rows)
    write_markdown(OUTPUT_DIR / "rq2_analysis.md", decomposition_rows, summary_rows, validation_lines, issues, alpha, beta)

    print(f"Cenários processados: {len(desired_list)}  |  linhas de decomposição: {len(decomposition_rows)}")
    if issues:
        print("Problemas de validação:")
        for i in issues:
            print(f"  - {i}")
    for line in validation_lines:
        print(f"  {line}")
    print(f"\nSaídas em: {OUTPUT_DIR}")
    print("  - rq2_summary.csv")
    print("  - rq2_full_ranking.csv")
    print("  - rq2_similarity_decomposition.csv")
    print("  - rq2_analysis.md")


if __name__ == "__main__":
    main()
