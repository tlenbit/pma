import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional, Self

from config import Config

from .base import Node
from .todo import (
    EngageLongTodo,
    EngageMediumTodo,
    EngageShortTodo,
    ExternalTodo,
    MetaTodo,
    SchedulingResetTodo,
    Todo,
)


class BlobNote(Node):
    content: bytes
    _parent: Optional[Node]
    _name: str
    _filename: str
    config: Config

    def __init__(
        self,
        name,
        content: bytes,
        config: Config,
        extension: str = "",
        parent: Optional[Node] = None,
    ) -> None:
        self._name = name
        self.content = content
        self._parent = parent
        self.config = config
        self._name = name
        assert "." not in name
        self._filename = ".".join([name, extension]) if extension else name

    def __repr__(self):
        return f"BlobNote<{id(self)}>"

    def write_to_fs(self) -> None:
        pass  # too dangerous :) and there is no point to do it yet

    @staticmethod
    def read_from_fs(
        path: Path, config: Config, parent: Optional[Node] = None
    ) -> "BlobNote":
        with open(path, "rb") as f:
            content = f.read()
        name = path.parts[-1].split(".")[0]
        extension = path.parts[-1].split(".")[0] if "." in path.parts[-1] else ""
        return BlobNote(
            name=name,
            extension=extension,
            content=content,
            parent=parent,
            config=config,
        )


def parse_note_metadata(text: str, note_name: str) -> str:
    if not text.strip().startswith("---"):
        return ""
    start = text.find("---")
    if start == -1:
        return ""
    pos = start + 3
    finish = text[pos:].find("---")
    if finish == -1:
        logging.warning(f"Found not closed metadata in note... {note_name}")
        return ""
    pos = start + finish + 6
    return text[start:pos]


class Note(Node):
    _content: str
    _todos: list[Todo]
    _parent: Optional[Node]
    _metadata: str
    _name: str
    _filename: str
    _path: Optional[Path]
    updated_at: datetime

    def __init__(
        self,
        name: str,
        text: str,
        config: Config,
        extension: str = "",
        parent: Optional[Node] = None,
        updated_at: datetime = datetime.now(),
        path: Optional[Path] = None,
    ) -> None:
        metadata = parse_note_metadata(text, note_name=name)
        self._content = text.replace(metadata, "").strip()
        self.config = config
        self._name = name
        self.updated_at = updated_at
        # assert "." not in name
        self._filename = ".".join([name, extension]) if extension else name
        self._parent = parent
        self._metadata = metadata
        self._filter_duplicate_aliases()
        self._path = path

    def _filter_duplicate_aliases(self):
        aliases = self.get_aliases()
        if aliases:
            self.set_aliases(set(aliases))

    @property
    def path(self) -> Path:
        return Path(Path(*super().path.parts[:-1]), self._filename)

    def get_aliases(self) -> tuple[str, ...]:
        aliases_prefix = "aliases:"
        for line in self.metadata.split("\n"):
            if line.strip().startswith(aliases_prefix):
                aliases_str = line.replace(aliases_prefix, "").strip()
                if not (aliases_str.startswith("[") and aliases_str.endswith("]")):
                    logging.error(f"Incorrect aliases string in note {self.name}")

                return tuple(
                    el.strip().lower() for el in aliases_str[1:-1].split(",") if el
                )
        return ()

    def set_aliases(self, val: Iterable[str]) -> None:
        if not self._metadata:
            self._metadata = "---\n---"
        metadata_lines = self._metadata.split("\n")
        aliases_line = f"aliases: [{','.join(set(val))},]"
        for i in range(len(metadata_lines)):
            if metadata_lines[i].startswith("aliases:"):
                metadata_lines[i] = aliases_line
                break
        else:
            metadata_lines[-1] = aliases_line
            metadata_lines.append("---")
        self._metadata = "\n".join(metadata_lines)

    def add_alias(self, val: str) -> None:
        aliases = self.get_aliases()
        if val.lower() not in aliases:
            self.set_aliases(list(aliases) + [val.lower()])

    @classmethod
    def read_from_fs(
        cls, path: Path, config: Config, parent: Optional[Node] = None
    ) -> Optional[Self]:
        with open(path, "r") as f:
            text = f.read()
        updated_at = datetime.fromtimestamp(os.path.getmtime(path))
        filename = path.parts[-1]
        return cls(
            name=".".join(filename.split(".")[:-1]) if "." in filename else filename,
            extension=filename.split(".")[-1] if "." in filename else "",
            text=text,
            parent=parent,
            config=config,
            updated_at=updated_at,
            path=path,
        )

    def write_to_fs(self) -> None:
        with open(self.path, "w") as f:
            f.write(self.text)

    @property
    def lines(self) -> list[str]:
        return self._content.split("\n")

    @property
    def metadata(self) -> str:
        return self._metadata

    @property
    def text(self) -> str:
        return (self.metadata + "\n\n" + self._content).strip()

    @text.setter
    def text(self, val):
        self._content = val.strip()

    @property
    def content(self) -> str:
        return self._content

    @property
    def internal_links(self) -> Iterable[str]:
        pattern = r"\[\[(.*?)\]\]"
        return [el.strip() for el in re.findall(pattern, self.text)]


class DefaultTodosMixin:
    meta_todo_classes = [
        EngageShortTodo,
        EngageMediumTodo,
        EngageLongTodo,
    ]


class ShedulingNoteMetaTodosMixin:
    meta_todo_classes = [SchedulingResetTodo]


class ProjectNote(Note, DefaultTodosMixin):
    external_todo: Optional[ExternalTodo] = None
    meta_todo_classes: list[MetaTodo]

    def __init__(
        self,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        lines_without_todos = []
        lines_with_todos = []
        for line in self.content.split("\n"):
            if line.strip().startswith("- [ ] ") or line.strip().startswith("- [x] "):
                lines_with_todos.append(line)
            else:
                lines_without_todos.append(line)
        todos = Todo.parse_from_lines(lines_with_todos)
        for todo in todos:
            todo.updated_at = kwargs.get("updated_at", datetime.now())

        self._content = "\n".join(lines_without_todos).strip()
        self._todos = todos

        for todo in todos:
            todo.project = self

    def add_default_todos(self):
        for meta_todo_class in self.meta_todo_classes:
            todo_text = meta_todo_class.template.format(self.name)
            if todo_text not in [todo.text for todo in self.get_todos()]:
                logging.debug(f'Adding "{todo_text}"  todo to project "{self.name}"')
                self.add_todo(Todo(text=todo_text, done=False))

    def get_sorted_todos(self) -> list["Todo"]:
        return sorted(self._todos, key=lambda todo: (todo.done, -todo.priority))

    def get_todos(self) -> list["Todo"]:
        return self.get_sorted_todos()

    def get_all_todos(self) -> list["Todo"]:
        result = []
        for root_todo in self.get_todos():
            for todo in root_todo.traverse():
                result.append(todo)
        return result

    @property
    def todos(self) -> list["Todo"]:
        return self.get_todos()

    # todo: add test for this
    def get_todo(self, text) -> Optional["Todo"]:
        return {todo.text: todo for todo in self.get_todos()}.get(text)

    @property
    def todos_text(self) -> str:
        result_lines = []
        separator_line = "\n"

        cur_priority = None
        for todo in self.get_sorted_todos():
            if cur_priority != todo.priority:
                result_lines.append(separator_line)
                cur_priority = todo.priority
            result_lines.append("\n".join(todo.to_lines()))

        return "\n".join(result_lines)

    def add_todo(self, todo: Todo) -> None:
        self._todos.append(todo)
        todo.project = self

    def remove_todo(self, todo: Todo) -> None:
        self._todos.remove(todo)

    @property
    def text(self) -> str:
        return (
            self.metadata + "\n\n" + self.todos_text + "\n\n" + self._content
        ).strip()

    @text.setter
    def text(self, val):
        self._content = val.strip()


class SchedulingNote(ShedulingNoteMetaTodosMixin, ProjectNote):
    ...
