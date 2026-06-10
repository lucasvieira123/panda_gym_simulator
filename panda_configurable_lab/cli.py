from __future__ import annotations

import argparse

from .config_loader import load_yaml_config
from .runner import ExperimentRunner


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa uma simulação configurável baseada em panda-gym."
    )

    parser.add_argument(
        "--config",
        "-c",
        required=True,
        help="Caminho para o arquivo YAML de configuração.",
    )

    args = parser.parse_args()

    config = load_yaml_config(args.config)
    runner = ExperimentRunner(config)
    runner.run()


if __name__ == "__main__":
    main()
