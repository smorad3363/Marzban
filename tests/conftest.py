import os
import subprocess


os.environ.setdefault("DEBUG", "false")
_check_output = subprocess.check_output


def check_output(*args, **kwargs):
    command = args[0] if args else kwargs.get("args", [])
    command_parts = command if isinstance(command, (list, tuple)) else [command]
    if any("xray" in str(part).lower() for part in command_parts):
        return b"Xray 1.0.0\n"
    return _check_output(*args, **kwargs)


subprocess.check_output = check_output
