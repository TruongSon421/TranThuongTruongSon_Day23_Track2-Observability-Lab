import sys, os, time

# Configure pyroscope BEFORE any app code runs
PYROSCOPE_SERVER = os.environ.get("PYROSCOPE_SERVER", "http://pyroscope:4040")
PYROSCOPE_APP_NAME = os.environ.get("PYROSCOPE_APP_NAME", "day23-app")
PYROSCOPE_SAMPLE_RATE = int(os.environ.get("PYROSCOPE_SAMPLE_RATE", "100"))

sys.path.insert(0, '/usr/local/lib/python3.12/site-packages')

try:
    import pyroscope
    pyroscope.configure(
        server_address=PYROSCOPE_SERVER,
        application_name=PYROSCOPE_APP_NAME,
        sample_rate=PYROSCOPE_SAMPLE_RATE,
        enable_logging=True,
    )
    sys.stderr.write("[pyroscope] configured: server=%s app=%s rate=%d\n" % (
        PYROSCOPE_SERVER, PYROSCOPE_APP_NAME, PYROSCOPE_SAMPLE_RATE))
    sys.stderr.flush()
except Exception as e:
    sys.stderr.write("[pyroscope] ERROR: %s\n" % e)
    sys.stderr.flush()

# Patch the main module to inject pyroscope instrumentation
# by adding it as the very first import
import importlib.util, types

# Insert pyroscope instrumentation at module load time
_original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __builtins__['__import__']

def _instrumented_import(name, *args, **kwargs):
    module = _original_import(name, *args, **kwargs)
    return module

__builtins__.__import__ = _instrumented_import

# Replace uvicorn with the profiled app
os.execvp("uvicorn", [
    "uvicorn", "main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--log-level", "warning",
])
