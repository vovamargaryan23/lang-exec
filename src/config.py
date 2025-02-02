from pathlib import Path


PROJECT_ROOT_PATH = Path(__file__).parent.parent

APP_NAME = "LangExec"
APP_DESCRIPTION = "LangExec is a tool that can be used to run and test code in different programming languages, without the need to install them locally."

DOCKERFILES_PATH = Path.joinpath(PROJECT_ROOT_PATH, "dockerfiles")
