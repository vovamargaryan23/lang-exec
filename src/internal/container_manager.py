import docker
from docker.models.containers import Container
import docker.errors

from src.internal.settings import DOCKER_SOCK_PATH, VOLUME_PATH


class ContainerManager:
    def __init__(self) -> None:
        self.__docker_client = docker.DockerClient(base_url=DOCKER_SOCK_PATH)
        
    def run_container(self, image: str, command: str) -> Container:
        stdout = ""
        stderr = ""
        return_code = 0
        try:
            running_container = self.__docker_client.containers.run(
                image=image,
                command=command,
                stdout=True,
                stderr=True,
                remove=True,
                volumes=[f"{VOLUME_PATH}:{VOLUME_PATH}:ro"]
            )

            stdout = running_container.decode()
        except docker.errors.ContainerError as e:
            print(e)
            stderr = e.stderr
            return_code = e.exit_status
        except docker.errors.ImageNotFound as e:
            print(e)
        except docker.errors.APIError as e:
            print(e)
        finally:
            return stdout, stderr, return_code
            
            
            
# docker.errors.ContainerError
# If the container exits with a non-zero exit code and detach is False.
# docker.errors.ImageNotFound
# If the specified image does not exist.
# docker.errors.APIError
# If the server returns an error.