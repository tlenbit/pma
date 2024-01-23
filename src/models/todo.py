import inspect
import logging
from abc import abstractmethod
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from sys import getrefcount
from typing import Any, Generator, Optional, Self


class Priority(int, Enum):
    today = 3
    later = 2
    maybe = 1


class Todo:
    external_todo: Optional["ExternalTodo"] = None

    # todo: fix type
    _project: Optional[Any] = None
    parent: Optional["Todo"] = None
    text: str  # todo: rename to content (same as in notes)
    _done: bool
    _children: list[Self]
    _priority: Priority
    _updated_at: datetime

    def __init__(
        self,
        text: str,
        done: bool = False,
        children: Optional[list[Self]] = None,
        priority: Priority = Priority.later,
        updated_at: datetime = datetime.now(),
        external_todo: Optional["ExternalTodo"] = None,
    ):
        self._done = done
        self._text = text
        self._children = children or []
        self._priority = priority
        self._updated_at = updated_at
        self.external_todo = external_todo

    def __repr__(self) -> str:
        return f"{self.text} ({self.__class__.__name__})"

    # todo: fix type
    @property
    def project(self) -> Optional[Any]:
        return self._project or self.parent and self.parent.project

    # todo: fix type
    @project.setter
    def project(self, val: Any) -> None:
        self._project = val

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, val: str) -> None:
        raise ValueError("You can not change text of a todo")

    def add_child(self, child: Self) -> None:
        self._children.append(child)
        child.parent = self

    def remove_child(self, child: Self) -> None:
        self._children.remove(child)

    def delete(self) -> None:
        if self.parent:
            self.parent.remove_child(self)
        elif self.project:
            self.project.remove_todo(self)
        logging.warning(f"Refs count on todo '{self.text}': {getrefcount(self)}")

    def get_child(self, child_text: str) -> Optional["Todo"]:
        # todo: use dict
        for child in self.children:
            if child.text == child_text:
                return child
        return None

    def merge(self, new_todo: "Todo") -> None:
        if not self.text == new_todo.text:
            logging.error(
                f"Cannot merge todos with different names: '{self.text}' and '{new_todo.text}'"
            )
        if new_todo.updated_at > self.updated_at:
            logging.info(f"Updating local todo {self}")
            self.done = new_todo.done
            self.id = new_todo.id
            self.priority = new_todo.priority

        for child in new_todo.children:
            present_child = self.get_child(child.text)
            if present_child:
                present_child.merge(child)
            else:
                logging.info(f"Adding new local todo {child}")
                self.add_child(child)

    @property
    def priority(self) -> Priority:
        if self.text.strip().startswith("!"):
            return Priority.today
        return self._priority

    @priority.setter
    def priority(self, val: Priority):
        self._priority = val

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    @updated_at.setter
    def updated_at(self, val):
        self._updated_at = val

    @property
    def done(self):
        return self._done

    @done.setter
    def done(self, val: bool):
        self._done = val

    @property
    def children(self) -> list[Self]:
        return sorted(self._children, key=lambda todo: (todo.done, -todo.priority))

    @staticmethod
    def parse_from_line(line: str) -> Optional["Todo"]:
        if line.startswith("- [ ] "):
            return create_todo(done=False, text=line[6:])
        if line.startswith("- [x] "):
            return create_todo(done=True, text=line[6:])
        return None

    @staticmethod
    def parse_from_lines(lines: list[str]) -> list["Todo"]:
        def get_indent_level(line: str) -> int:
            indent_level = 0
            i = 0
            while i < len(line):
                if line[i] == "\t":
                    indent_level += 1
                i += 1
            return indent_level

        result: list[Todo] = []
        stack: list[Todo] = []
        previous_todo: Optional[Todo] = None

        for line in lines:
            indent_level = get_indent_level(line)

            todo = Todo.parse_from_line(line.strip())
            if not todo:
                continue

            # todo: use pattern matching?
            if indent_level == 0:
                result.append(todo)
                stack = []
            elif (indent_level == len(stack) + 1) and previous_todo:
                stack.append(previous_todo)
                stack[-1].add_child(todo)
            elif indent_level == len(stack):
                stack[-1].add_child(todo)
            elif indent_level < len(stack):
                stack.pop()
                stack[-1].add_child(todo)

            previous_todo = todo

        return result

    def to_lines(self) -> list[str]:
        # use list of lists here
        # to keep track of indent level
        stacks: list[list[Todo]] = []
        stacks.append([self])
        result = []

        while stacks:
            # cleanup empty list
            if not stacks[-1]:
                stacks.pop()
                continue

            cur = stacks[-1].pop()
            result.append(cur.to_line(indent_level=len(stacks) - 1))
            stacks.append(cur.children[::-1])

        return result

    def to_line(self, indent_level: int = 0) -> str:
        # this does not return subtodos
        # maybe use only to_lines method, or rename this one
        done_marker = "x" if self._done else " "
        indent = "\t" * indent_level
        return f"{indent}- [{done_marker}] {self.text}"

    def traverse(self) -> Generator[Self, None, None]:
        d = deque([self])
        while d:
            cur = d.popleft()
            yield cur
            d.extend(cur.children)


class MetaTodo(Todo):
    @property
    @abstractmethod
    def template(self):
        raise

    def __init__(
        self,
        priority: Priority = Priority.today,
        *args,
        **kwargs,
    ):
        super().__init__(priority=priority, *args, **kwargs)


class EngageShortTodo(MetaTodo):
    template = "♲ 20 mins of {}"
    minutes = 20  # todo: refactor


class EngageMediumTodo(MetaTodo):
    template = "♲ 40 mins of {}"
    minutes = 40


class EngageLongTodo(MetaTodo):
    template = "♲ 60 mins of {}"
    minutes = 60


class SchedulingResetTodo(MetaTodo):
    template = "♲ Reset Scheduling"


def get_meta_todos_classes():
    return [
        cls
        for name, cls in globals().items()
        if inspect.isclass(cls) and issubclass(cls, MetaTodo) and cls is not MetaTodo
    ]


def create_todo(
    text: str,
    **kwargs,
) -> Todo:
    # todo: refactor switch
    for meta_todo_cls in get_meta_todos_classes():
        if meta_todo_cls.template.replace("{}", "") in text:
            return meta_todo_cls(text=text, **kwargs)
    return Todo(text=text, **kwargs)


class ExternalTodo:
    id: Optional[str]  # will be absent if todo is not yet created
    external_parent_id: Optional[str]
    done: bool
    text: str
    updated_at: datetime
    priority: Priority

    def __init__(
        self,
        text: str,
        updated_at: datetime = datetime.now(),
        priority: Priority = Priority.later,
        done: bool = False,
        external_parent_id: Optional[str] = None,
        id: Optional[str] = None,
    ):
        self.external_parent_id = external_parent_id
        self.id = id
        self.done = done
        self.text = text
        self.priority = priority

        if updated_at.tzinfo:
            local_tz = datetime.now(timezone.utc).astimezone().tzinfo
            local_aware = updated_at.astimezone(local_tz)
            updated_at = local_aware.replace(tzinfo=None)

        self.updated_at = updated_at
