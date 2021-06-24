import os
import sys

# run the WebSocket server and timeout after 5s
status = os.system('timeout --preserve-status 5 bash entrypoint.sh')

# See: https://bugs.python.org/issue40094
# Ideally we would use os.waitstatus_to_exitcode(status), except this is available
# only in Python 3.9
if os.WIFSIGNALED(status):
    exit_code = -os.WTERMSIG(status)
elif os.WIFEXITED(status):
    exit_code = os.WEXITSTATUS(status)
elif os.WIFSTOPPED(status):
    exit_code = -os.WSTOPSIG(status)
else:
    raise Exception("Unexpected exit status")

# this indicates the timeout happened, resulting in an exit via SIGTERM (143)
if exit_code == 143:
    sys.exit(0)

sys.exit(-1)
