import os
import signal
import time
from subprocess import Popen

import pytest

dir_path = os.path.dirname(os.path.realpath(__file__))
root_path = os.path.abspath(os.path.join(dir_path, "../.."))


@pytest.fixture(autouse=True, scope="session")
def run_server():
    # See:
    #   https://stackoverflow.com/questions/4789837/how-to-terminate-a-python-subprocess-launched-with-shell-true
    process = Popen(["bash", "entrypoint.sh"], cwd=root_path, preexec_fn=os.setsid)
    time.sleep(5)
    yield
    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
