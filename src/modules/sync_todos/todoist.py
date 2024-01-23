import datetime
import json
import logging
from typing import Any

import httpx
from models import Todo
from sync_todos import ExternalTodo, ExternalTodoApp
from todoist_api_python.api import TodoistAPI
from utils import retry

TOKEN = "5893fc33bdf673e42db6fc5a2eb86beae3a59d6b"


class TodoistApp(ExternalTodoApp):
    todoist_api: TodoistAPI = TodoistAPI(TOKEN)
    project_id: str = ""
    project_name: str = "Inbox"

    def __init__(self):
        if not self.project_id:
            project = {p.name: p for p in self.todoist_api.get_projects()}.get(
                self.project_name
            )
            if not project:
                logging.info(
                    f"Could not find project with name '{self.project_name}, creating new one...'"
                )
                project = self.todoist_api.add_project(name=self.project_name)
            self.project_id = project.id
        assert self.project_id

    @retry(times=10)
    def get_not_completed_todos(self) -> list[ExternalTodo]:
        tasks = self.todoist_api.get_tasks(project_id=self.project_id)

        return [
            ExternalTodo(
                id=task.id,
                done=task.is_completed,
                text=task.content,
                priority=task.priority - 1,
                updated_at=datetime.datetime.fromisoformat(task.created_at),
                external_parent_id=task.parent_id,
            )
            for task in tasks
        ]

    @retry(times=10)
    def get_completed_todos(self) -> list[ExternalTodo]:
        # todoist python native lib kindly does not include completed tasks
        # so we kindly have to use separate "sync api" for completed tasks
        sync_api_response = httpx.get(
            "https://api.todoist.com/sync/v9/completed/get_all",
            params={"project_id": self.project_id},
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
        # todo: use pydantic for this shit
        tasks_from_sync_api = json.loads(sync_api_response.text)["items"]

        return [
            ExternalTodo(
                id=task["id"],
                done=True,
                text=task["content"],
                updated_at=datetime.datetime.fromisoformat(task["completed_at"]),
            )
            for task in tasks_from_sync_api
        ]

    def get_todos(self) -> list[ExternalTodo]:
        # todo make requests async
        # todoist kindly made two separate apis for done and not done tasks

        todos = self.get_completed_todos() + self.get_not_completed_todos()
        todos.sort(key=lambda x: (not x.done, x.updated_at))

        # for the same tasks only the most recent and not done should remain
        unique_todos_dict = {}
        for todo in todos:
            unique_todos_dict[todo.text] = todo

        result = list(unique_todos_dict.values())

        return result

    @retry(times=10)
    def create_todo(self, todo: ExternalTodo) -> None:
        logging.info(f"Creating external todo... {todo.text}")
        task = self.todoist_api.add_task(
            content=todo.text,
            parent_id=todo.external_parent_id,
            priority=todo.priority + 1,
            project_id=self.project_id,
        )
        todo.id = task.id

    @retry(times=10)
    def remove_todo(self, todo: ExternalTodo) -> None:
        logging.info(f"Removing todo... {todo.text} with id: {todo.id}")
        assert todo.id
        try:
            # is_success = self.todoist_api.update_task(
            #     task_id=todo.id,
            #     content="DELETED",
            #     is_completed=True,
            #     project_id=self.project_id,
            # )
            is_success = self.todoist_api.close_task(
                task_id=todo.id,
                project_id=self.project_id,
            )
            if not is_success:
                logging.error(f"Failed removing task {todo.text}")
        except Exception:
            logging.error(f"Could not remove task {todo.text}")

    @retry(times=10)
    def update_todo(self, todo: ExternalTodo) -> None:
        if todo.done:
            logging.warning(f"Closing todo... {todo.text}")
            try:
                assert todo.id
                self.todoist_api.update_task(
                    task_id=todo.id,
                    content="DELETED",
                    project_id=self.project_id,
                )
                self.todoist_api.close_task(
                    task_id=todo.id,
                    project_id=self.project_id,
                )
            except Exception as error:
                logging.warning(str(error))
                logging.warning(
                    f"Looks like {todo.text} is already already done in todoist too"
                )
        else:
            logging.warning(f"Updating priority of todo... {todo.text}")
            try:
                is_success = self.todoist_api.update_task(
                    task_id=todo.id,
                    priority=todo.priority + 1,
                    project_id=self.project_id,
                )
                if not is_success:
                    logging.error(f"Failed updating task {todo.text}")
            except Exception as error:
                print(error)
