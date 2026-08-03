# %%
import re
from sismic.io import import_from_yaml, export_to_plantuml

# Casa blocos do tipo:
#   <indent> state "LABEL" as ALIAS {
#   <indent>   ...conteúdo...
#   <indent> }
#
# Observação: exigimos indentação (>= 1 espaço/tab) -> NÃO pega o root (indent 0).
STATE_BLOCK_RE = re.compile(
    r'(?ms)^(?P<indent>[ \t]+)state\s+"(?P<label>[^"]+)"\s+as\s+(?P<alias>[A-Za-z0-9_]+)\s*\{\s*\n'
    r'(?P<body>.*?)'
    r'^(?P=indent)\}\s*$'
)

def unbox_all_states_except_root(puml_text: str) -> str:
    def repl(m: re.Match) -> str:
        indent = m.group("indent")
        label = m.group("label")
        alias = m.group("alias")
        body = m.group("body")

        # Remove 1 nível de indentação do corpo (padrão do export: indent + 2 espaços)
        # Mantém linhas vazias como estão.
        remove_prefix = indent + "  "
        new_body_lines = []
        for ln in body.splitlines():
            if ln.startswith(remove_prefix):
                new_body_lines.append(ln[len(remove_prefix):])
            else:
                new_body_lines.append(ln)

        new_body = "\n".join(new_body_lines).rstrip()

        if new_body:
            return f'{indent}state "{label}" as {alias}\n{new_body}'
        else:
            return f'{indent}state "{label}" as {alias}'

    out = STATE_BLOCK_RE.sub(repl, puml_text)
    # Mantém newline final, se existia
    if puml_text.endswith("\n") and not out.endswith("\n"):
        out += "\n"
    return out


# ---- seu fluxo ----
sc = import_from_yaml(filepath="scenario_state_machine.yaml")
puml_text = export_to_plantuml(sc, state_contracts=True)

# achata todos os estados folha (todos, exceto o root)
puml_text = unbox_all_states_except_root(puml_text)

open("scenario_state_machine.puml", "w", encoding="utf-8").write(puml_text)
# %%
