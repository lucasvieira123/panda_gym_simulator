# %%
from drone_behavior_simulator import DroneBehaviorSimulator, TelemetryBus
from antecipated_scenario_monitor import AntecipatedScenarioMonitor
from unanticipated_scenario_diagnoser import UnanticipatedScenarioDiagnoser
from unanticipated_scenario_identifier import UnanticipatedScenarioIdentifier
from unanticipated_scenarios_detector import UnanticipatedScenariosDetector
from similarity_based_adapter import SimilarityBasedAdapter
from utils import load_config, save_jsonl
from constants import DEJAVU_CONF_PATH

if __name__ == "__main__":
    cfg = load_config(DEJAVU_CONF_PATH)

    if cfg["simulation_replay"]["enabled"]:
        print("Starting drone behaviour simulation...")
        bus = TelemetryBus()
        simulator = DroneBehaviorSimulator(bus)
        initial_context = simulator.get_initial_context()

        # MONITORING ...
        monitor = AntecipatedScenarioMonitor(initial_context)
        bus.subscribe(monitor.handle_runtime_data)
        simulator.run()
    
    detector = UnanticipatedScenariosDetector()
    identifier = UnanticipatedScenarioIdentifier()
    diagnoser = UnanticipatedScenarioDiagnoser()
    similarity_adapter = SimilarityBasedAdapter()

    detected_unanticipated_scenarios_df = detector.detects()

    if not detected_unanticipated_scenarios_df.empty:
        print("Unanticipated scenarios detected")

        identificated_unanticipatd_scenario_dict = identifier.identifies(detected_unanticipated_scenarios_df)
        diagnosed_unanticipatd_scenario_dict = diagnoser.diagnosis(detected_unanticipated_scenarios_df, identificated_unanticipatd_scenario_dict)

        similarities_list = similarity_adapter.calculate_similarity(diagnosed_unanticipatd_scenario_dict)
        
        save_jsonl(cfg["similarities_file"], similarities_list)