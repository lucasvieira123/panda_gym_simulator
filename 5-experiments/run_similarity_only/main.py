"""
Executa isoladamente a etapa de similaridade do DejaVu, fora do pipeline
principal (sem monitor, identifier ou diagnoser).

Toda a configuracao deste experimento vive dentro desta mesma pasta
(run_similarity_only/), isolada do resto do projeto:

    configs/scenario_catalogue.json   -> copia de 3-dejavu/configs/arm/scenario_catalogue.json
    configs/weights_config.yaml       -> copia de 3-dejavu/configs/weights_config.yaml
    configs/desired_scenario.json     -> cenario "desired"/diagnosticado a comparar
    output/similarities/              -> onde o .jsonl de resultado e gravado

O codigo-fonte (classes de Scenario/Expression, metrica de similaridade,
formatacao de trace) NAO e duplicado aqui: e importado direto de
3-dejavu/src via sys.path.

O arquivo de --input aceita tanto um unico cenario desejado (objeto JSON)
quanto uma lista de varios cenarios (array JSON) -- nesse caso o ranking e
calculado uma vez para cada item da lista, e todos os resultados vao para
o mesmo .jsonl de saida, com o campo "desired_key" identificando de qual
cenario da lista veio cada linha.

Uso:
    python main.py
    python main.py --input configs/outro_cenario.json
    python main.py --input configs/varios_cenarios.json --top 3
"""
import argparse
import json
import sys
import yaml
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

THIS_DIR = Path(__file__).resolve().parent
DEJAVU_SRC = THIS_DIR.parents[1] / "3-dejavu" / "src"
sys.path.insert(0, str(DEJAVU_SRC))

from scenario.diagnosed_scenario import DiagnosedScenario
from scenario.candidate_scenario import CandidateScenario
from similarity.dejavu_similarity import calculate_scenario_similarity
from trace_printer import format_pipeline_similarities

CONFIGS_DIR = THIS_DIR / "configs"
OUTPUT_DIR = THIS_DIR / "output" / "similarities"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--input",
        default=str(CONFIGS_DIR / "desired_scenario.json"),
        help="JSON com {name, given, when, do, then} do cenario desejado/diagnosticado",
    )
    parser.add_argument("--top", type=int, default=None, help="mostra so os N melhores no terminal (grava todos no arquivo)")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_yaml(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def calculate_similarity(desired_dict: dict, catalogue: dict, weight_configs: dict) -> list:
    diagnosed_scenario = DiagnosedScenario(data=desired_dict)

    kargs = weight_configs.copy()
    kargs["monitored_parameters"] = catalogue.get("monitored_parameters", {})

    results = []
    for candidate_data in catalogue.get("scenarios", {}).values():
        candidate_scenario = CandidateScenario(data=candidate_data)
        similarity_result = calculate_scenario_similarity(diagnosed_scenario, candidate_scenario, **kargs)
        results.append({
            "similarity_result": similarity_result,
            "diagnosed": diagnosed_scenario.to_dict(),
            "candidate": candidate_scenario.to_dict(),
            "config": weight_configs,
        })
    return results


def write_similarities(all_results: list) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = OUTPUT_DIR / f"similarities_{ts}.jsonl"
    with open(out_path, "a", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps({"run_id": ts, **r}, default=str) + "\n")
    return out_path


def main() -> None:
    args = parse_args()

    desired_data = load_json(Path(args.input))
    catalogue = load_json(CONFIGS_DIR / "scenario_catalogue.json")
    weight_configs = load_yaml(CONFIGS_DIR / "weights_config.yaml")

    desired_list = desired_data if isinstance(desired_data, list) else [desired_data]

    all_results = []
    for desired_dict in desired_list:
        results = calculate_similarity(desired_dict, catalogue, weight_configs)
        results.sort(key=lambda s: s["similarity_result"], reverse=True)

        desired_key = desired_dict.get("name", "desired")
        if len(desired_list) > 1:
            print(f"\n{'#' * 90}\n# Desired: {desired_key}\n{'#' * 90}")

        print(format_pipeline_similarities(results[: args.top] if args.top else results))

        top = results[0]
        print(
            f"\n>> Melhor candidato: {top['candidate']['name']} "
            f"(score={top['similarity_result']:.5f}) -> do: {top['candidate']['do']}"
        )

        for r in results:
            r["desired_key"] = desired_key
        all_results.extend(results)

    out_path = write_similarities(all_results)
    print(f"\nResultados completos gravados em: {out_path}")


if __name__ == "__main__":
    main()
