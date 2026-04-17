import os
from pathlib import Path

DOCKER_SOCK_PATH: str = "unix://var/run/docker.sock"

# Executor container resource limits
EXEC_CPU_LIMIT: int = 1      # CPUs
EXEC_MEM_LIMIT: int = 128    # MB
EXEC_TIMEOUT: int = 10       # seconds before container is killed
EXEC_PIDS_LIMIT: int = 64    # max processes/threads inside container

# Path inside the application container where code files are written
VOLUME_PATH: Path = Path("/media/code")

# Host-side absolute path of the code volume — used when mounting into executor
# containers spawned via the Docker socket. Set via env in docker-compose.
HOST_VOLUME_PATH: str = os.environ.get("CODE_VOLUME_HOST_PATH", str(VOLUME_PATH))

NETWORK_NAME: str = ""
