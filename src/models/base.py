import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from config import Config

from .todo import Todo


def get_path(parent: Optional["Node"], name: str, config: Config) -> Path:
    if parent:
        return Path(os.path.join(parent.path, name))
    else:
        return config.vault_root_dir


class Node(ABC):
    _parent: Optional["Node"] = None
    _name: str
    config: Config
    _path: Optional[Path] = None

    def __repr__(self) -> str:
        return f"{self.name} ({self.__class__.__name__})"

    @property
    def parent(self) -> Optional["Node"]:
        return self._parent

    @property
    def path(self) -> Path:
        if self._path:
            return self._path

        return get_path(
            parent=self._parent,
            name=self._name,
            config=self.config,
        )

    def set_parent(self, parent):
        self._parent = parent

    @property
    def name(self):
        return self._name

    @property
    def filename(self):
        return self._filename

    @abstractmethod
    def write_to_fs(self):
        ...

    @staticmethod
    @abstractmethod
    def read_from_fs(
        name: str,
        config,
        parent: Optional["Node"] = None,
    ) -> "Node":
        ...


class DirectoryABC(Node, ABC):
    def get_children(self) -> Node:
        return list(self._children.values())

    # def get_notes(self) -> Iterable[Note]:
    #     return get_children_notes(root=self)

    def add_child(self, child: Node):
        assert child.name not in self._children
        assert child.name
        self._children[child.name] = child
        child.set_parent(self)

    def get_child(self, name: str) -> Optional[Node]:
        return self._children.get(name)
