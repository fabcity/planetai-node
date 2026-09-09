"""Run a command on a pseudo-terminal and type the given answers into it.

`planetai` reads every answer from /dev/tty on purpose — the documented install is `curl … | bash`, where
stdin is the pipe — so a test that pipes into stdin drives nothing. This gives the command a real
terminal, which is the only way to test a question.

  python3 tests/pty_run.py "answer1" "answer2" -- cmd arg arg
"""
import os
import pty
import select
import sys

answers = []
argv = sys.argv[1:]
if "--" in argv:
    i = argv.index("--")
    answers, argv = argv[:i], argv[i + 1:]
if not argv:
    sys.exit("usage: pty_run.py [answers...] -- cmd [args...]")

pid, fd = pty.fork()
if pid == 0:
    os.execvp(argv[0], argv)

out = b""
pending = [a.encode() + b"\n" for a in answers]
while True:
    r, w, _ = select.select([fd], [fd] if pending else [], [], 20)
    if w and pending:
        os.write(fd, pending.pop(0))
    if r:
        try:
            chunk = os.read(fd, 4096)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
    if not r and not w:
        break
_, status = os.waitpid(pid, 0)
sys.stdout.write(out.decode(errors="replace"))
sys.exit(os.waitstatus_to_exitcode(status) if hasattr(os, "waitstatus_to_exitcode") else (status >> 8))
