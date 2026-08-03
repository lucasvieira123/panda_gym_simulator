import json
import time
import yaml

from scenario.candidate_scenario import CandidateScenario
from similarity.dejavu_similarity import calculate_scenario_similarity
from scenario.diagnosed_scenario import DiagnosedScenario


class SimilarityBasedAdapter:
    def __init__(self):
        self.shared_scenarios_list = self.get_shared_scenarios()
        # self.scenarios_pipeline_dict = self.get_scenarios_pipeline()
        self.weight_configs_dict = self.get_weight_config()
        self.monitored_parameters_dict = self.get_monitored_parameters()        

    def get_weight_config(self):
        with open("unexpected_scenario_handling_system/res/weights_config.yaml", "r") as file:
            settings = yaml.safe_load(file)
        return settings

    # def get_scenarios_pipeline(self):
    #     with open("unexpected_scenario_handling_system/res/scenarios_pipeline.json", "r") as file:
    #         scenarios_pipeline = json.load(file)
    #         return scenarios_pipeline

    def get_monitored_parameters(self):
        with open("unexpected_scenario_handling_system/res/monitored_parameters.json", "r") as file:
            monitored_parameters_dict = json.load(file)
            return monitored_parameters_dict

    def get_shared_scenarios(self):
        with open("unexpected_scenario_handling_system/res/shared_scenarios.json", "r") as file:
            shared_scenerios = json.load(file)
            return shared_scenerios

    def calculate_similarity(self, diagnosed_unanticipatd_scenario_dict):
        # diagnosed_data = self.scenarios_pipeline_dict["diagnosed"]
        diagnosed_data = diagnosed_unanticipatd_scenario_dict
        diagnosed_scenario = DiagnosedScenario(data=diagnosed_data)
        current_config = self.weight_configs_dict
        kargs = current_config.copy()
        kargs["monitored_parameters"] = self.monitored_parameters_dict

        similarity_result_list = []
        for candidate_data in self.shared_scenarios_list:
            candidate_scenario = CandidateScenario(data=candidate_data)

            start_time = time.perf_counter()
            similarity_result = calculate_scenario_similarity(
                diagnosed_scenario,
                candidate_scenario,
                **kargs
            )
            end_time = time.perf_counter()
            elapsed_time = end_time - start_time

            similarity_result_list.append({
                "similarity_result": similarity_result,
                "elapsed_time": elapsed_time,
                "diagnosed": diagnosed_scenario.to_dict(),    # Supondo que existe
                "candidate": candidate_scenario.to_dict(),    # Supondo que existe
                "config": current_config,
        })

        return similarity_result_list