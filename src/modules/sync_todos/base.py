from abc import ABC, abstractmethod

from models import ExternalTodo, Todo


class ExternalTodoApp(ABC):
    @abstractmethod
    def get_todos(self) -> list[ExternalTodo]:
        ...

    @abstractmethod
    def create_todo(self, todo: Todo) -> None:
        ...

    @abstractmethod
    def remove_todo(self, todo: Todo) -> None:
        ...

    @abstractmethod
    def update_todo(self, todo: Todo) -> None:
        ...
