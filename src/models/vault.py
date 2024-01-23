import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Optional

from config import Config

from .directory import Directory
from .note import Note, ProjectNote
from .todo import Todo
from .utils import get_children_notes


class Vault:
    config: Config
    root: Directory

    # todo: maybe remove "create" and leave only __init__
    def __init__(self, config):
        self.config = config
        self.root = Directory.create(
            name=self.config.vault_root_dir.parts[-1],
            config=config,
        )

    @staticmethod
    def create(config: Config) -> "Vault":
        vault = Vault(config=config)
        projects_dir = Directory.create(name=config.projects_dir_name, config=config)

        vault.root.add_child(projects_dir)
        return vault

    @staticmethod
    def read_from_fs(config) -> "Vault":
        vault = Vault.create(config=config)
        vault.root = Directory.read_from_fs(
            name=config.vault_root_dir.parts[-1],
            config=config,
        )

        # todo: maybe remove this
        for project in vault.get_projects():
            for todo in project.get_all_todos():
                assert todo.project == project

        return vault

    def write_to_fs(self) -> None:
        self.root.write_to_fs()

    def __getitem__(self, path: str):
        node = self.root

        for rel_path in path.split("/"):
            if node and rel_path and rel_path != ".":
                node = node.get_child(str(rel_path))

        return node

    @property
    def projects_path(self) -> Path:
        return Path(
            os.path.join(self.root.path, Path(self.config.projects_dir_name)),
        )

    @property
    def projects_dir(self) -> Directory:
        return self.root.get_child(self.config.projects_dir_name)

    @property
    def name(self):
        return self.root.path.parts[-1]

    def get_todos(self) -> list[Todo]:
        return [todo for project in self.get_projects() for todo in project.get_todos()]

    def get_all_todos(self) -> list[Todo]:
        result = []
        for root_todo in self.get_todos():
            for todo in root_todo.traverse():
                result.append(todo)
        return result

    def get_todo(self, todo_text: str) -> Optional[Todo]:
        # todo: optimize?
        todos = {todo.text: todo for todo in self.root.get_todos()}
        return todos.get(todo_text)

    def get_projects(self) -> list[ProjectNote]:
        result: list[ProjectNote] = []

        cur_node = self.projects_dir
        stack = [cur_node]

        while stack:
            node = stack.pop()
            if isinstance(node, ProjectNote):
                result.append(node)
            if isinstance(node, Directory):
                stack.extend(node.get_children())

        return result

    def get_project(self, name: str) -> Optional[ProjectNote]:
        return {proj.name: proj for proj in self.get_projects()}.get(name)

    def get_notes(self) -> Iterable[Note]:
        return get_children_notes(self.root)

    @property
    def updated_at(self):
        return max(note.updated_at for note in self.get_notes())

    @property
    def updated_recently(self):
        logging.debug(f"Vault updated at {self.updated_at}")
        return self.updated_at > (
            datetime.now() - timedelta(seconds=self.config.read_debounce_sec)
        )
