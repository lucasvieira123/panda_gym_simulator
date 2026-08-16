import json
import time
import yaml

from scenario.candidate_scenario import CandidateScenario
from similarity.dejavu_similarity import calculate_scenario_similarity
from scenario.diagnosed_scenario import DiagnosedScenario
from constants import DEJAVU_CONF_PATH, PROJECT_ROOT
from utils import load_config


class SimilarityBasedAdapter:

    def __init__(self):
        self.cfg = load_config(DEJAVU_CONF_PATH)

        catalogue_path = PROJECT_ROOT / self.cfg["scenario_catalogue_path"]
        weights_path   = PROJECT_ROOT / self.cfg["weights_config_path"]

        with open(catalogue_path, "r") as f:
            catalogue = json.load(f)

        with open(weights_path, "r") as f:
            self.weight_configs_dict = yaml.safe_load(f)

        # Extrai monitored_parameters e lista de cenários candidatos do catálogo
        self.monitored_parameters_dict = catalogue.get("monitored_parameters", {})
        scenarios_dict = catalogue.get("scenarios", {})
        self.candidates = list(scenarios_dict.values())

    def calculate_similarity(self, diagnosed_unanticipated_scenario_dict: dict) -> list:
        diagnosed_scenario = DiagnosedScenario(data=diagnosed_unanticipated_scenario_dict)
        kargs = self.weight_configs_dict.copy()
        kargs["monitored_parameters"] = self.monitored_parameters_dict

        results = []
        for candidate_data in self.candidates:
            candidate_scenario = CandidateScenario(data=candidate_data)

            start_time = time.perf_counter()
            similarity_result = calculate_scenario_similarity(
                diagnosed_scenario,
                candidate_scenario,
                **kargs
            )
            elapsed_time = time.perf_counter() - start_time

            results.append({
                "similarity_result": similarity_result,
                "elapsed_time":      elapsed_time,
                "diagnosed":         diagnosed_scenario.to_dict(),
                "candidate":         candidate_scenario.to_dict(),
                "config":            self.weight_configs_dict,
            })

        return results

    def recommend(self, sorted_results: list) -> dict | None:
        if not sorted_results:
            return None
        top = sorted_results[0]
        candidate = top.get("candidate", {})
        return {
            "candidate_name": candidate.get("name"),
            "do":             candidate.get("do"),
            "score":          top.get("similarity_result"),
        }
