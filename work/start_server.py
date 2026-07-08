import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
log = root / "work" / "server.log"
err = root / "work" / "server.err.log"
pid_file = root / "work" / "server.pid"

cmd = [
    sys.executable,
    "-m",
    "uvicorn",
    "backend.main:app",
    "--host",
    "127.0.0.1",
    "--port",
    "8000",
]

with log.open("ab") as out, err.open("ab") as error:
    process = subprocess.Popen(
        cmd,
        cwd=root,
        stdout=out,
        stderr=error,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        close_fds=True,
    )

pid_file.write_text(str(process.pid), encoding="utf-8")
print(process.pid)
