import logging
import os
from pathlib import Path
from typing import Iterable, Optional

from config import Config

from .base import DirectoryABC, Node, get_path
from .note import BlobNote, Note, ProjectNote, SchedulingNote
from .utils import get_children_notes


def is_hidden_file(path: Path):
    return path.parts[-1].startswith(".")


def path_should_be_ignored(path: Path, config: Config):
    if is_hidden_file(path):
        return True

    return path in [
        Path(os.path.join(config.vault_root_dir, relative_dir))
        for relative_dir in config.ignore_paths
    ]


def read_note_from_fs(path: Path, config: Config, parent=None) -> Note:
    with open(path, "rb") as f:
        content = f.read()
        try:
            content.decode("utf-8")
            if config.scheduling_note_name in path.parts[-1]:
                return SchedulingNote.read_from_fs(
                    path=path,
                    parent=parent,
                    config=config,
                )
            elif config.projects_dir_name in path.parts:
                return ProjectNote.read_from_fs(
                    path=path,
                    parent=parent,
                    config=config,
                )
            else:
                return Note.read_from_fs(
                    path=path,
                    parent=parent,
                    config=config,
                )

        except UnicodeDecodeError:
            return BlobNote.read_from_fs(
                path=path,
                config=config,
                parent=parent,
            )


class Directory(DirectoryABC):
    _children: dict[str, "Node"]

    def __init__(
        self,
        name: str,
        config: Config,
        parent: Optional[Node] = None,
    ):
        self._name = name
        self._children = {}
        self._parent = parent
        self.config = config

    @staticmethod
    def create(
        name: str,
        config: Config,
        parent: Optional[Node] = None,
    ) -> "Directory":
        return Directory(name, config, parent)

    def get_children(self) -> Node:
        return list(self._children.values())

    def get_notes(self) -> Iterable[Note]:
        return get_children_notes(root=self)

    def add_child(self, child: Node):
        assert child.name not in self._children
        assert child.name
        self._children[child.name] = child
        child.set_parent(self)

    def get_child(self, name: str) -> Optional[Node]:
        return self._children.get(name)

    @staticmethod
    def read_from_fs(
        name: str,
        config,
        parent: Optional[Node] = None,
    ) -> DirectoryABC:
        path = get_path(parent=parent, name=name, config=config)
        assert os.path.isdir(path), f"{path} is not a dir"
        result = Directory.create(name=name, parent=parent, config=config)
        for child_path in path.iterdir():
            if path_should_be_ignored(child_path, config):
                logging.debug(f"Ignoring path {path}...")
                continue

            child: Optional[Node]
            if os.path.isdir(child_path):
                child = Directory.read_from_fs(
                    name=child_path.parts[-1],
                    config=config,
                    parent=result,
                )
            else:
                child = read_note_from_fs(path=child_path, parent=result, config=config)
                if not child:
                    logging.error(f"Couldnt read note with path {path}")
                    continue
            result.add_child(child)

        return result

    def write_to_fs(self) -> None:
        if not os.path.exists(self.path):
            os.mkdir(self.path)
        for child in self.get_children():
            child.write_to_fs()
