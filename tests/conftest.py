import os
import subprocess


os.environ.setdefault("DEBUG", "false")
subprocess.check_output = lambda *args, **kwargs: b"Xray 1.0.0\n"
