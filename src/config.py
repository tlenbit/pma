from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    vault_root_dir: Path = Path("/app/vault")
    ignore_paths: list[Path] = [
        "./storage",
        "./translations",
        "./projects/learn/languages/thai/aux/Письменность.md",  # todo: add "ignore_dirs"
    ]
    logging_level: str = "INFO"
    projects_dir_name: str = "projects"
    scheduling_note_name: str = "⚙️ Scheduling"

    model_config = ConfigDict(env_file=".env")

    read_debounce_sec: int = 30


def get_config():
    return Config()
