from dataclasses import dataclass
from pathlib import Path


@dataclass
class ConfigMock:
    vault_root_dir: Path
    ignore_paths: list[Path]
    projects_dir_name: str


def get_mock_config(
    vault_number: int = 666,
    projects_dir_name="projects",
):
    return ConfigMock(
        vault_root_dir=Path(f"fixtures/vault_{vault_number}"),
        ignore_paths=[],
        projects_dir_name=projects_dir_name,
    )
