from __future__ import annotations

from logging import config
from pathlib import Path
from typing import Any, Dict

import yaml


def load_yaml_config(path: str | Path) -> Dict[str, Any]:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Arquivo YAML não encontrado: {path}")

    # with path.open("r", encoding="utf-8") as file:
    #     config = yaml.safe_load(file) or {}

    # validate_minimal_config(config)

    # return config
    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    config["_config_path"] = str(path)
    config["_config_dir"] = str(path.parent)

    validate_minimal_config(config)

    return config


def validate_minimal_config(config: Dict[str, Any]) -> None:
    # "task" e "policy" são opcionais no arquivo de ambiente — podem vir do
    # commands file (runtime_commands.yaml) para separar responsabilidades.
    # "goals" é opcional — pode vir do goals file (goals.yaml)
    required_sections = ["experiment", "robot", "simulation", "objects"]

    for section in required_sections:
        if section not in config:
            raise ValueError(f"Seção obrigatória ausente no YAML: '{section}'")

    # Se task estiver no arquivo de ambiente, valida o tipo
    if "task" in config and config["task"].get("type", "configurable") != "configurable":
        raise ValueError("Esta versão inicial suporta apenas task.type: 'configurable'.")

    if not isinstance(config.get("objects"), list) or len(config["objects"]) == 0:
        raise ValueError("A seção 'objects' precisa conter pelo menos um objeto.")

    # Valida goals apenas se presentes no arquivo de ambiente
    if "goals" in config:
        targets = config["goals"].get("targets", [])

        if not isinstance(targets, list) or len(targets) == 0:
            raise ValueError("A seção 'goals.targets' precisa conter pelo menos um objetivo.")

        object_names = {obj["name"] for obj in config["objects"]}

        for target in targets:
            obj_name = target.get("object")

            if obj_name not in object_names:
                raise ValueError(
                    f"O objetivo referencia o objeto '{obj_name}', mas ele não existe em objects."
                )

            if "position" not in target:
                raise ValueError(f"O objetivo do objeto '{obj_name}' precisa ter 'position'.")
