import logging
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

from config import Config
from event_bus import EventBus
from models import MetaTodo, Note, Priority, ProjectNote, Todo, Vault, create_todo
from sync_todos import ExternalTodo, ExternalTodoApp


# todo: logic in this class and todoist ExternalTodoApp is mixed, maybe fix it
@dataclass
class ExternalTodosSyncer:
    external_todo_app: ExternalTodoApp
    vault: Vault
    config: Config
    event_bus: Optional[EventBus] = None

    _local_todos_dict: dict[str, Todo] = field(default_factory=dict)
    _external_root_todos: list[ExternalTodo] = field(default_factory=list)

    def set_local_todos_dict(self) -> None:
        self._local_todos_dict = {}
        for todo in self.vault.get_all_todos():
            self._local_todos_dict[todo.text] = todo

    def sync(self) -> None:
        self.set_local_todos_dict()

        external_todos: list[
            Optional[ExternalTodo]
        ] = self.external_todo_app.get_todos()

        synced_external_todos: set[ExternalTodo] = set()

        for _ in range(len(external_todos)):  # same principle as in bubble sort
            for external_todo in external_todos:
                if external_todo in synced_external_todos:
                    continue
                elif project := self.vault.get_project(external_todo.text):
                    project.external_todo = external_todo
                    synced_external_todos.add(external_todo)
                elif local_todo := self._local_todos_dict.get(external_todo.text):
                    local_todo.external_todo = external_todo
                    synced_external_todos.add(external_todo)
                else:
                    for project in self.vault.get_projects():
                        if (
                            project.external_todo
                            and project.external_todo.id
                            == external_todo.external_parent_id
                        ):
                            project.add_todo(
                                create_todo(
                                    text=external_todo.text,
                                    done=external_todo.done,
                                    external_todo=external_todo,
                                )
                            )
                            synced_external_todos.add(external_todo)
                            continue

                    # setting up local child todos
                    for local_todo in self.vault.get_todos():
                        if (
                            local_todo.external_todo
                            and local_todo.external_todo.id
                            == external_todo.external_parent_id
                        ):
                            local_todo.add_child(
                                create_todo(
                                    text=external_todo.text,
                                    done=external_todo.done,
                                    priority=external_todo.priority,
                                    external_todo=external_todo,
                                )
                            )
                            synced_external_todos.add(external_todo)
                            continue

        for project in self.vault.get_projects():
            if not project.external_todo:
                new_todo = ExternalTodo(text=project.name, done=False)
                # breakpoint()
                self.external_todo_app.create_todo(new_todo)
                project.external_todo = new_todo
            elif project.external_todo.done:
                new_project_todo = ExternalTodo(text=project.name, done=False)
                # breakpoint()
                self.external_todo_app.create_todo(new_project_todo)
                assert new_project_todo.id
                for todo in project.get_todos():
                    if todo.external_todo:
                        todo.external_todo.done = todo.done
                        todo.external_todo.external_parent_id = new_project_todo.id
                        # breakpoint()
                        self.external_todo_app.create_todo(
                            todo.external_todo
                        )  # cannot just update todo because todoist kindly removes all subtodos of done todo and we can not change it anymore
                    else:
                        ...  # it will be created later anyway

        for todo in self.vault.get_all_todos():
            if not todo.external_todo:
                if not todo.done:
                    new_todo = ExternalTodo(
                        text=todo.text,
                        done=todo.done,
                        priority=todo.priority,
                    )
                    if todo.parent and todo.parent.external_todo:
                        new_todo.external_parent_id = todo.parent.external_todo.id
                    elif todo.project and todo.project.external_todo:
                        new_todo.external_parent_id = todo.project.external_todo.id
                    # breakpoint()
                    self.external_todo_app.create_todo(new_todo)
                    todo.external_todo = new_todo
            elif (
                todo.external_todo.done
                and not todo.done
                and todo.updated_at > todo.external_todo.updated_at
            ):
                if not todo.project.external_todo:
                    breakpoint()
                todo.external_todo.external_parent_id = todo.project.external_todo.id

                new_todo = ExternalTodo(
                    text=todo.text,
                    done=todo.done,
                    priority=todo.priority,
                    external_parent_id=todo.project.external_todo.id,
                )
                # breakpoint()
                self.external_todo_app.create_todo(new_todo)
            elif (
                todo.updated_at > todo.external_todo.updated_at
                and todo.done != todo.external_todo.done
            ):
                todo.external_todo.done = todo.done
                self.external_todo_app.update_todo(todo.external_todo)
            else:
                todo.done = todo.external_todo.done
                todo.priority = todo.external_todo.priority


@dataclass
class ExternalTodosSyncJob:
    external_todo_app: ExternalTodoApp
    vault: Vault
    config: Config
    event_bus: Optional[EventBus] = None

    def run(self) -> None:
        syncer = ExternalTodosSyncer(
            external_todo_app=self.external_todo_app,
            vault=self.vault,
            config=self.config,
            event_bus=self.event_bus,
        )
        syncer.sync()
