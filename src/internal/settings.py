from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    docker_sock_path: str = "unix:///var/run/docker.sock"

    exec_cpu_limit: int = 1
    exec_mem_limit: int = 128
    exec_timeout: int = 10
    exec_pids_limit: int = 64
    exec_pool_size: int = 3
    exec_pool_overflow: int = 5
    exec_rate_limit: str = "30/minute"
    redis_url: str | None = None

    volume_path: Path = Path("/media/code")
    code_volume_host_path: str = ""

    @computed_field
    @property
    def host_volume_path(self) -> str:
        return self.code_volume_host_path or str(self.volume_path)

    @computed_field
    @property
    def exec_mem_limit_bytes(self) -> int:
        return self.exec_mem_limit * 1024 * 1024

    @computed_field
    @property
    def exec_cpu_limit_nanos(self) -> int:
        return self.exec_cpu_limit * 10 ** 9


settings = Settings()
