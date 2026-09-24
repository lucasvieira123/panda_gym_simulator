"""
Verificação do mecanismo de similaridade do DejaVu (Retriever) usando
diretamente a implementação real em 3-dejavu/src/similarity/dejavu_similarity.py.

Este script NAO altera nenhuma logica de producao: apenas importa e chama
as funcoes internas (inclusive "privadas", prefixadas com "_") para expor
os valores intermediarios do calculo de similaridade.

Usa as configuracoes isoladas desta pasta (configs/scenario_catalogue.json,
configs/weights_config.yaml) como fonte de verdade para monitored_parameters
e pesos, exatamente como main.py faz.

Uso:
    python mechanism_analysis.py
"""
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

import yaml

THIS_DIR = Path(__file__).resolve().parent
DEJAVU_SRC = THIS_DIR.parents[1] / "3-dejavu" / "src"
sys.path.insert(0, str(DEJAVU_SRC))

from similarity.dejavu_similarity import (
    _extract_relational_expressions,
    _transform_conditional_expression_to_symbolic,
    conditional_expression_to_dnf,
    _decompose_relational_expression,
    _get_relational_expression_region,
    _calculate_jaccard_similarity,
    calculate_parameters_similarity,
    _extract_parameters,
    _tversky_similarity,
    _penalty,
    calculate_conditional_similarity,
    calculate_scenario_similarity,
)
from scenario.diagnosed_scenario import DiagnosedScenario
from scenario.candidate_scenario import CandidateScenario

CONFIGS_DIR = THIS_DIR / "configs"


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def hr(title: str) -> None:
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


def main() -> None:
    catalogue = load_json(CONFIGS_DIR / "scenario_catalogue.json")
    weight_configs = load_yaml(CONFIGS_DIR / "weights_config.yaml")
    monitored_parameters = catalogue["monitored_parameters"]
    alpha = weight_configs["tversky_weights"]["alpha"]
    beta = weight_configs["tversky_weights"]["beta"]
    parameter_weights = weight_configs["parameter_weights"]
    conditional_weights = weight_configs["conditional_weights"]

    # ------------------------------------------------------------------
    hr("SECAO 3 — Predicados unilaterais -> intervalos")
    # ------------------------------------------------------------------
    lf = monitored_parameters["lateral_friction"]
    print(f"Dominio configurado para lateral_friction: min_value={lf['min_value']}, "
          f"max_value={lf['max_value']}, type={lf['type']}")

    for value in (0.315, 0.4):
        var, op, val = _decompose_relational_expression(f"lateral_friction <= {value}")
        region = _get_relational_expression_region(var, op, val, lf["min_value"], lf["max_value"], lf["type"])
        print(f"  lateral_friction <= {value}  ->  regiao interna = {region}")

    jacc = _calculate_jaccard_similarity("lateral_friction <= 0.315", "lateral_friction <= 0.4", monitored_parameters)
    region_315 = _get_relational_expression_region("lateral_friction", "<=", 0.315, lf["min_value"], lf["max_value"], lf["type"])
    region_4 = _get_relational_expression_region("lateral_friction", "<=", 0.4, lf["min_value"], lf["max_value"], lf["type"])
    inter_low, inter_high = max(region_315[0], region_4[0]), min(region_315[1], region_4[1])
    union_low, union_high = min(region_315[0], region_4[0]), max(region_315[1], region_4[1])
    print(f"\nIntersecao: ({inter_low}, {inter_high}) -> comprimento = {inter_high - inter_low}")
    print(f"Uniao:      ({union_low}, {union_high}) -> comprimento = {union_high - union_low}")
    print(f"Jaccard(lateral_friction <= 0.315, lateral_friction <= 0.4) = {jacc}")

    # também testar outros operadores para reportar tratamento geral
    print("\nOutros operadores (mesmo dominio [0.0, 2.0], value=0.5):")
    for op in [">=", "<=", ">", "<", "==", "!="]:
        var, op2, val = _decompose_relational_expression(f"lateral_friction {op} 0.5")
        region = _get_relational_expression_region(var, op2, val, lf["min_value"], lf["max_value"], lf["type"])
        print(f"  lateral_friction {op} 0.5 -> {region}")

    # ------------------------------------------------------------------
    hr("SECAO 2 — Tratamento de parametro ausente (lateral_friction)")
    # ------------------------------------------------------------------
    desired_given = "(object_lift_height_cm < 10) AND (finger_contacts < 2) AND lateral_friction <= 0.315"
    candidate_given_no_friction = "object_lift_height_cm < 10 AND finger_contacts < 2"

    print(f"Desired given:   {desired_given}")
    print(f"Candidate given: {candidate_given_no_friction}  (sem lateral_friction)")

    pair_sims = calculate_parameters_similarity(desired_given, candidate_given_no_friction, monitored_parameters)
    print(f"\ncalculate_parameters_similarity (pares casados por nome de variavel):")
    for d in pair_sims:
        print(f"  {d}")
    print("  -> lateral_friction NAO aparece: nao ha par para ele (so entra na comparacao "
          "quem existe nos DOIS lados). Ele NAO recebe similaridade 0 nem 1 explicitamente: "
          "e simplesmente omitido da media parametrica.")

    params_1 = _extract_parameters(desired_given)
    params_2 = _extract_parameters(candidate_given_no_friction)
    print(f"\n_extract_parameters(desired)   = {params_1}")
    print(f"_extract_parameters(candidate) = {params_2}")

    tversky = _tversky_similarity(params_1, params_2, alpha=alpha, beta=beta)
    penalty = _penalty(params_1, params_2, alpha=alpha, beta=beta)
    print(f"\nTversky(params_desired, params_candidate, alpha={alpha}, beta={beta}) = {tversky}")
    print(f"penalty = 1 - Tversky = {penalty}")
    print("  -> penalty e calculada SOBRE O CONJUNTO de parametros (estrutural), "
          "nao sobre os valores. lateral_friction estar so no 'desired' entra como "
          "'only_in_set1', ponderado por ALPHA (peso alto = 0.9) -> penalidade forte.")

    final_given_sim = calculate_conditional_similarity(
        desired_given, candidate_given_no_friction, monitored_parameters, parameter_weights, alpha=alpha, beta=beta
    )
    print(f"\ncalculate_conditional_similarity(given_desired, given_candidate) = {final_given_sim}")
    print("  formula: final = max(parametric_avg - structural_penalty, 0)")

    print("\nRespostas diretas as perguntas da secao 2:")
    print("  1) lateral_friction ausente e tratado como wildcard?           NAO — nao existe conceito de wildcard no codigo.")
    print("  2) A ausencia recebe similaridade 0 explicitamente?            NAO no termo parametrico (e omitido, nao zerado).")
    print("  3) O parametro e simplesmente ignorado?                       SIM, na media parametrica (Jaccard por par).")
    print("  4) Existe penalidade estrutural especifica?                    SIM — Tversky penalty sobre o CONJUNTO de nomes de parametros (alpha/beta).")
    print("  5) A ausencia afeta so estrutural ou tambem parametrica?       So a estrutural (penalty). A parametrica so soma sobre os pares casados.")
    print("  6) Comportamento difere entre Given/When/Then?                 NAO — calculate_conditional_similarity e chamada de forma identica e independente para given/when/then.")

    # ------------------------------------------------------------------
    hr("SECAO 4 — Parsing e normalizacao")
    # ------------------------------------------------------------------

    def compare_equivalent(label: str, expr_a: str, expr_b: str) -> None:
        print(f"\n[{label}]")
        print(f"  A: {expr_a!r}")
        print(f"  B: {expr_b!r}")
        try:
            leaves_a = _extract_relational_expressions(expr_a)
            leaves_b = _extract_relational_expressions(expr_b)
            dnf_a = conditional_expression_to_dnf(expr_a)
            dnf_b = conditional_expression_to_dnf(expr_b)
            params_a = _extract_parameters(expr_a)
            params_b = _extract_parameters(expr_b)
            print(f"  leaves A = {leaves_a}")
            print(f"  leaves B = {leaves_b}")
            print(f"  DNF A    = {dnf_a!r}")
            print(f"  DNF B    = {dnf_b!r}")
            print(f"  params A = {params_a} | params B = {params_b}")
        except Exception as e:
            print(f"  <<< EXCECAO ao processar parsing/DNF: {type(e).__name__}: {e}")
            return
        try:
            sim = calculate_conditional_similarity(expr_a, expr_b, monitored_parameters, parameter_weights, alpha=alpha, beta=beta)
            print(f"  similarity(A, B) = {sim}  {'== 1.0 OK' if sim == 1.0 else '<<< DIFERENTE DE 1.0'}")
        except Exception as e:
            print(f"  <<< EXCECAO ao calcular similarity(A, B): {type(e).__name__}: {e}")

    compare_equivalent("Parenteses", "(object_lift_height_cm < 10)", "object_lift_height_cm < 10")
    compare_equivalent("Espacos", "finger_contacts < 2", "finger_contacts    <    2")
    compare_equivalent(
        "Ordem das condicoes",
        "object_lift_height_cm < 10 AND finger_contacts < 2",
        "finger_contacts < 2 AND object_lift_height_cm < 10",
    )
    compare_equivalent("Representacao numerica (10 vs 10.0)", "object_lift_height_cm < 10", "object_lift_height_cm < 10.0")
    compare_equivalent(
        "Parenteses em expressao composta",
        "(object_lift_height_cm < 10) AND (finger_contacts < 2)",
        "object_lift_height_cm < 10 AND finger_contacts < 2",
    )

    # ------------------------------------------------------------------
    hr("SECAO 5 — Ordem do AND (3 termos)")
    # ------------------------------------------------------------------
    expr_order_1 = "object_lift_height_cm < 10 AND finger_contacts < 2 AND lateral_friction <= 0.315"
    expr_order_2 = "lateral_friction <= 0.315 AND object_lift_height_cm < 10 AND finger_contacts < 2"
    sim_order = calculate_conditional_similarity(expr_order_1, expr_order_2, monitored_parameters, parameter_weights, alpha=alpha, beta=beta)
    print(f"A: {expr_order_1!r}")
    print(f"B: {expr_order_2!r}")
    print(f"similarity(A, B) = {sim_order}  {'== 1.0 OK' if sim_order == 1.0 else '<<< DIFERENTE DE 1.0'}")

    # ------------------------------------------------------------------
    hr("SECAO 6 — Caso real LIFT_OBJECT contra catalogo real")
    # ------------------------------------------------------------------
    diagnosed_dict = {
        "name": "diagnosed_LIFT_OBJECT_unanticipated",
        "given": "object_lift_height_cm < 10 AND finger_contacts < 2 AND lateral_friction <= 0.315",
        "when": "grasp_completed == 1",
        "do": "TBD",
        "then": "object_lift_height_cm >= 10 AND finger_contacts >= 2",
    }
    diagnosed_scenario = DiagnosedScenario(data=diagnosed_dict)

    results = []
    for candidate_data in catalogue["scenarios"].values():
        candidate_scenario = CandidateScenario(data=candidate_data)

        given_sim = calculate_conditional_similarity(
            diagnosed_scenario.given.to_string(), candidate_scenario.given.to_string(),
            monitored_parameters, parameter_weights, alpha=alpha, beta=beta,
        )
        when_sim = calculate_conditional_similarity(
            diagnosed_scenario.when.to_string(), candidate_scenario.when.to_string(),
            monitored_parameters, parameter_weights, alpha=alpha, beta=beta,
        )
        then_sim = calculate_conditional_similarity(
            diagnosed_scenario.then.to_string(), candidate_scenario.then.to_string(),
            monitored_parameters, parameter_weights, alpha=alpha, beta=beta,
        )

        # decompor given/when/then em parametrica (weighted jaccard avg) + penalty estrutural
        def breakdown(expr1, expr2):
            pair_sims = calculate_parameters_similarity(expr1, expr2, monitored_parameters)
            from similarity.dejavu_similarity import _parameter_similarity_weighted_avg
            parametric = _parameter_similarity_weighted_avg(pair_sims, parameter_weights)
            p1 = _extract_parameters(expr1)
            p2 = _extract_parameters(expr2)
            structural_sim = _tversky_similarity(p1, p2, alpha=alpha, beta=beta)
            struct_penalty = 1 - structural_sim
            return parametric, structural_sim, struct_penalty

        given_parametric, given_structural, given_penalty = breakdown(
            diagnosed_scenario.given.to_string(), candidate_scenario.given.to_string()
        )
        when_parametric, when_structural, when_penalty = breakdown(
            diagnosed_scenario.when.to_string(), candidate_scenario.when.to_string()
        )
        then_parametric, then_structural, then_penalty = breakdown(
            diagnosed_scenario.then.to_string(), candidate_scenario.then.to_string()
        )

        overall = calculate_scenario_similarity(
            diagnosed_scenario, candidate_scenario,
            conditional_weights=conditional_weights,
            tversky_weights={"alpha": alpha, "beta": beta},
            parameter_weights=parameter_weights,
            monitored_parameters=monitored_parameters,
        )

        results.append({
            "candidate_name": candidate_scenario.name,
            "given_structural_similarity": round(given_structural, 5),
            "given_parametric_similarity": round(given_parametric, 5),
            "given_structural_penalty": round(given_penalty, 5),
            "given_final_similarity": round(given_sim, 5),
            "when_structural_similarity": round(when_structural, 5),
            "when_parametric_similarity": round(when_parametric, 5),
            "when_final_similarity": round(when_sim, 5),
            "then_structural_similarity": round(then_structural, 5),
            "then_parametric_similarity": round(then_parametric, 5),
            "then_final_similarity": round(then_sim, 5),
            "final_similarity": round(overall, 5),
        })

    results.sort(key=lambda r: r["final_similarity"], reverse=True)
    for rank, r in enumerate(results, 1):
        r["rank"] = rank
        print(f"\n[{rank}] {r['candidate_name']}")
        print(f"    given: structural={r['given_structural_similarity']}  parametric={r['given_parametric_similarity']}  "
              f"penalty={r['given_structural_penalty']}  final={r['given_final_similarity']}")
        print(f"    when:  structural={r['when_structural_similarity']}  parametric={r['when_parametric_similarity']}  "
              f"final={r['when_final_similarity']}")
        print(f"    then:  structural={r['then_structural_similarity']}  parametric={r['then_parametric_similarity']}  "
              f"final={r['then_final_similarity']}")
        print(f"    FINAL SIMILARITY = {r['final_similarity']}")

    # ------------------------------------------------------------------
    hr("SECAO 7 — Top-1, Top-2, Delta")
    # ------------------------------------------------------------------
    top1, top2 = results[0], results[1]
    delta = top1["final_similarity"] - top2["final_similarity"]
    print(f"Top-1 candidate: {top1['candidate_name']}")
    print(f"Top-1 similarity: {top1['final_similarity']}")
    print(f"\nTop-2 candidate: {top2['candidate_name']}")
    print(f"Top-2 similarity: {top2['final_similarity']}")
    print(f"\nDeltaTop1 = {delta}")


if __name__ == "__main__":
    main()
