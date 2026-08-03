import os
import re
import threading
import wrapt
import pprint
import logging

def next_log_filename(prefix="trace_", suffix=".log", directory="logs"):
    if not os.path.exists(directory):
        os.makedirs(directory)
    existing = [
        f for f in os.listdir(directory)
        if re.match(rf"{re.escape(prefix)}\d+{re.escape(suffix)}$", f)
    ]
    if not existing:
        return os.path.join(directory, f"{prefix}1{suffix}")
    numbers = [
        int(re.search(rf"{re.escape(prefix)}(\d+){re.escape(suffix)}", fname).group(1))
        for fname in existing
    ]
    next_idx = max(numbers) + 1
    return os.path.join(directory, f"{prefix}{next_idx}{suffix}")

def setup_logger():
    """Configura o logger para novo arquivo sequencial na pasta logs."""
    # Remove todos os handlers existentes para garantir reconfiguração
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    log_filename = next_log_filename()
    logging.basicConfig(
        filename=log_filename,
        filemode='w',
        level=logging.INFO,
        format='%(message)s'
    )
    print(f"[LOGGER] Novo arquivo de log: {log_filename}")
    return log_filename


@wrapt.decorator
def trace(wrapped, instance, args, kwargs):
    log_lines = []
    log_lines.append(f"\n{'='*50}")
    log_lines.append(f"{wrapped.__name__}:")
    log_lines.append("  input:")

    if args:
        log_lines.append("    args:")
        for idx, arg in enumerate(args):
            log_lines.append(f"      [{idx}]:")
            log_lines.append(pprint.pformat(arg, indent=8, width=80, compact=False))
    else:
        log_lines.append("    args: (vazio)")

    if kwargs:
        log_lines.append("    kwargs:")
        for k, v in kwargs.items():
            log_lines.append(f"      {k}:")
            log_lines.append(pprint.pformat(v, indent=10, width=80, compact=False))
    else:
        log_lines.append("    kwargs: (vazio)")

    result = wrapped(*args, **kwargs)

    log_lines.append("  output:")
    log_lines.append(pprint.pformat(result, indent=4, width=80, compact=False))
    log_lines.append(f"{'='*50}\n")

    log_entry = "\n".join(log_lines)
    logging.info(log_entry)

    return result