from pathlib import Path

DOCKER_SOCK_PATH: str = "unix://var/run/docker.sock"

# EXECUTOR CONTAINER RESOURCE LIMITS
EXEC_CPU_LIMIT: int = 4
EXEC_MEM_LIMIT: int = 4096

# VOLUME SETTINGS
VOLUME_PATH: Path = Path("/media/code")

NETWORK_NAME: str = ""