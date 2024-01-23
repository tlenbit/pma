import random
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from models import Directory, ProjectNote, Todo, Vault, create_todo
from modules import ExternalTodosSyncer
from sync_todos import ExternalTodo, ExternalTodoApp
from tests.utils import get_mock_config


class ExternalTodoAppMock(ExternalTodoApp):
    def get_todos(self) -> list[ExternalTodo]:
        return []

    def create_todo(self, todo: ExternalTodo) -> None:
        todo.id = str(random.randint(0, 100))

    def remove_todo(self, todo: ExternalTodo) -> None:
        pass

    def update_todo(self, todo: ExternalTodo) -> None:
        pass


class CreateTodoMock(MagicMock):
    def __call__(self, todo: ExternalTodo):
        super().__call__(todo)
        todo.id = str(random.randint(0, 100))


class RemoveTodoMock(MagicMock):
    def __call__(self, todo: ExternalTodo):
        super().__call__(todo)


class UpdateTodoMock(MagicMock):
    def __call__(self, todo: ExternalTodo):
        super().__call__(todo)


@pytest.fixture
def external_todo_app_mock():
    return ExternalTodoAppMock()


class TestExternalTodosSyncer:
    def test_sync_external_to_local_projects_todos(
        self,
        external_todo_app_mock,
    ):
        config = get_mock_config()
        vault = Vault.create(config=config)
        directory_for_projects_about_consuming = Directory.create(
            name="consume", config=config
        )

        directory_for_projects_about_consuming.add_child(
            ProjectNote(name="🕹 Игры", text="lalala", config=config)
        )
        vault.projects_dir.add_child(directory_for_projects_about_consuming)

        project_todo = ExternalTodo(
            id=4526, text="🕹 Игры", done=False
        )  # this todo should be represented as a project in vault
        child_todo = ExternalTodo(id=4526, text="пройти зельду", done=False)
        child_todo.external_parent_id = project_todo.id
        external_todo_app_mock.get_todos = lambda: [
            ExternalTodo(
                id=4526,
                text="пройти зельду",
                done=False,
                external_parent_id=project_todo.id,
            ),
            project_todo,
        ]

        syncer = ExternalTodosSyncer(external_todo_app_mock, vault, config)

        syncer.sync()

        assert len(vault["projects/consume/🕹 Игры"].get_todos()) == 1
        assert vault["projects/consume/🕹 Игры"].get_todos()[0].text == "пройти зельду"

    def test_sync_projects_todos_mark_existing_todo_as_done(
        self,
        external_todo_app_mock,
    ):
        config = get_mock_config()
        vault = Vault.create(config=config)
        directory_for_projects_about_consuming = Directory.create(
            name="consume", config=config
        )
        note = ProjectNote(name="🕹 Игры", text="lalala", config=config)
        note.add_todo(Todo(done=False, text="пройти зельду"))
        directory_for_projects_about_consuming.add_child(note)
        vault.projects_dir.add_child(directory_for_projects_about_consuming)

        project_todo = ExternalTodo(
            id=4526, text="🕹 Игры", done=False
        )  # this todo should be represented as a project in vault
        external_todo_app_mock.get_todos = lambda: [
            project_todo,
            ExternalTodo(id=4526, text="todo", done=True),
            ExternalTodo(
                id=4526,
                text="пройти зельду",
                done=True,
                external_parent_id=project_todo.id,
            ),
        ]

        syncer = ExternalTodosSyncer(external_todo_app_mock, vault, config)

        assert vault["projects/consume/🕹 Игры"].get_todos()[0].done is False

        syncer.sync()

        assert vault["projects/consume/🕹 Игры"].get_todos()[0].done is True

    def test_sync_local_project_todos_to_external(
        self,
        external_todo_app_mock,
    ):
        config = get_mock_config()
        vault = Vault.create(config=config)

        external_todo_app_mock.create_todo = CreateTodoMock()

        external_todo_app_mock.get_todos = lambda: []
        parent_todo = create_todo(done=False, text="parent_todo")
        child_todo = create_todo(done=False, text="child_todo")
        parent_todo.add_child(child_todo)
        note = ProjectNote(name="🕹 Игры", text="lalala", config=config)
        note.add_todo(parent_todo)
        vault.projects_dir.add_child(note)

        syncer = ExternalTodosSyncer(external_todo_app_mock, vault, config)

        syncer.sync()

        assert external_todo_app_mock.create_todo.call_count == 3
        # new todo object corresponding to "note" should be used in first call
        # so idk how to check it
        new_todo1 = external_todo_app_mock.create_todo.call_args_list[0].args[0]
        new_todo2 = external_todo_app_mock.create_todo.call_args_list[1].args[0]
        new_todo3 = external_todo_app_mock.create_todo.call_args_list[2].args[0]
        assert new_todo1.text == "🕹 Игры"
        assert new_todo1.id
        assert new_todo2.id
        assert new_todo3.id
        assert new_todo2.text == parent_todo.text
        assert new_todo2.done == parent_todo.done
        assert new_todo2.priority == parent_todo.priority
        assert new_todo3.text == child_todo.text
        assert new_todo3.done == child_todo.done
        assert new_todo3.priority == child_todo.priority

    def test_sync_local_project_todos_to_external_when_project_todo_note_already_exists(
        self,
        external_todo_app_mock,
    ):
        config = get_mock_config()
        vault = Vault.create(config=config)

        external_todo_app_mock.create_todo = CreateTodoMock()

        external_todo_app_mock.get_todos = lambda: [
            ExternalTodo(id="123", text="🕹 Игры", done=False, priority=1),
        ]
        todo = create_todo(done=False, text="todo")
        note = ProjectNote(name="🕹 Игры", text="lalala", config=config)
        note.add_todo(todo)
        vault.projects_dir.add_child(note)

        syncer = ExternalTodosSyncer(external_todo_app_mock, vault, config)

        syncer.sync()

        assert external_todo_app_mock.create_todo.call_count == 1
        new_todo = external_todo_app_mock.create_todo.call_args_list[0].args[0]
        assert new_todo.text == todo.text
        assert new_todo.done == todo.done
        assert new_todo.priority == todo.priority
        assert new_todo.external_parent_id == "123"

    def test_not_remove_duplicates_with_different_parents(
        self,
        external_todo_app_mock,
    ):
        config = get_mock_config()
        vault = Vault.create(config=config)

        external_todo_app_mock.remove_todo = RemoveTodoMock()

        parent_todo = ExternalTodo(id=123, text="parent_todo", done=False, priority=1)
        parent_todo2 = ExternalTodo(id=123, text="parent_todo2", done=False, priority=1)
        child1 = ExternalTodo(
            id=124,
            text="child_todo1",
            done=False,
            priority=1,
            external_parent_id=parent_todo.id,
        )
        child2 = ExternalTodo(
            id=124,
            text="child_todo1",
            done=False,
            priority=1,
            external_parent_id=parent_todo2.id,
        )
        child3 = ExternalTodo(
            id=124,
            text="child_todo2",
            done=False,
            priority=1,
            external_parent_id=parent_todo.id,
        )
        child1.external_parent_id = parent_todo.id
        child2.external_parent_id = parent_todo2.id
        child3.external_parent_id = parent_todo.id

        external_todo_app_mock.get_todos = lambda: [parent_todo, parent_todo2]

        syncer = ExternalTodosSyncer(external_todo_app_mock, vault, config)

        syncer.sync()

        assert external_todo_app_mock.remove_todo.call_count == 0

    # fixing a bug
    def test_sync_local_project_subtasks_to_external(
        self,
        external_todo_app_mock,
    ):
        config = get_mock_config()
        vault = Vault.create(config=config)

        parent_todo = create_todo(done=False, text="parent_todo")
        child_todo = create_todo(done=False, text="child_todo")
        parent_todo.add_child(child_todo)
        note = ProjectNote(name="🕹 Игры", text="lalala", config=config)
        note.add_todo(parent_todo)
        vault.projects_dir.add_child(note)

        external_todo_app_mock.create_todo = CreateTodoMock()  # add project todo here

        external_todo_app_mock.get_todos = lambda: []

        syncer = ExternalTodosSyncer(external_todo_app_mock, vault, config)

        syncer.sync()

        assert external_todo_app_mock.create_todo.call_count == 3

        new_todo2 = external_todo_app_mock.create_todo.call_args_list[1].args[0]
        new_todo3 = external_todo_app_mock.create_todo.call_args_list[2].args[0]

        assert new_todo2.text == parent_todo.text
        assert new_todo2.done == parent_todo.done
        assert new_todo2.priority == parent_todo.priority
        assert new_todo3.text == child_todo.text
        assert new_todo3.done == child_todo.done
        assert new_todo3.priority == child_todo.priority
        assert new_todo3.external_parent_id == new_todo2.id

    def test_nothing_happens_if_external_todos_are_same_as_local(self):
        config = get_mock_config()
        vault = Vault.create(config=config)

        parent_todo = create_todo(done=False, text="parent_todo")
        child_todo = create_todo(done=False, text="child_todo")
        parent_todo.add_child(child_todo)

        note = ProjectNote(name="🕹 Игры", text="lalala", config=config)
        note.add_todo(parent_todo)

        vault.projects_dir.add_child(note)

        external_todo_app_mock.create_todo = CreateTodoMock()

        external_todo_app_mock.get_todos = lambda: [
            ExternalTodo(done=False, text="🕹 Игры", id="123"),
            ExternalTodo(
                done=False, text="parent_todo", id="124", external_parent_id="123"
            ),
            ExternalTodo(
                done=False, text="child_todo", id="125", external_parent_id="124"
            ),
        ]

        syncer = ExternalTodosSyncer(external_todo_app_mock, vault, config)

        syncer.sync()

        assert external_todo_app_mock.create_todo.call_count == 0

    def test_ignore_done_local_todo_if_there_is_not_same_external_todo(self):
        config = get_mock_config()
        vault = Vault.create(config=config)

        todo = create_todo(done=True, text="todo")

        note = ProjectNote(name="🕹 Игры", text="lalala", config=config)
        note.add_todo(todo)
        vault.projects_dir.add_child(note)

        external_todo_app_mock.create_todo = CreateTodoMock()

        external_todo_app_mock.get_todos = lambda: [
            ExternalTodo(done=False, text="🕹 Игры", id="123"),
        ]

        syncer = ExternalTodosSyncer(external_todo_app_mock, vault, config)

        syncer.sync()

        assert external_todo_app_mock.create_todo.call_count == 0

    def test_ignore_done_local_todo_if_there_IS_same_done_external_todo(self):
        config = get_mock_config()
        vault = Vault.create(config=config)

        todo = create_todo(done=True, text="todo")
        todo.updated_at = datetime.now()

        note = ProjectNote(name="🕹 Игры", text="lalala", config=config)
        note.add_todo(todo)
        vault.projects_dir.add_child(note)

        external_todo_app_mock.create_todo = CreateTodoMock()

        external_todo_app_mock.get_todos = lambda: [
            ExternalTodo(done=False, text="🕹 Игры", id="123"),
            ExternalTodo(
                done=True, text="todo", updated_at=datetime.now() - timedelta(hours=1)
            ),
        ]

        syncer = ExternalTodosSyncer(external_todo_app_mock, vault, config)

        syncer.sync()

        assert external_todo_app_mock.create_todo.call_count == 0

    def test_marking_local_todo_as_done(
        self,
        external_todo_app_mock,
    ):
        config = get_mock_config()
        vault = Vault.create(config=config)

        project_todo = ExternalTodo(id=123, text="🕹 Игры", done=False)
        todo = ExternalTodo(
            id=12233,
            text="todo",
            done=False,
            updated_at=datetime.now()
            - timedelta(hours=1),  # so that local todo is more fresh
            external_parent_id=project_todo.id,
        )

        external_todo_app_mock.get_todos = lambda: [project_todo, todo]
        external_todo_app_mock.update_todo = UpdateTodoMock()  # add project todo here

        note = ProjectNote(name="🕹 Игры", text="lalala", config=config)
        note.add_todo(
            create_todo(
                done=True,
                text="todo",
            )
        )
        vault.projects_dir.add_child(note)

        syncer = ExternalTodosSyncer(external_todo_app_mock, vault, config)

        syncer.sync()

        assert todo.done is True
        assert external_todo_app_mock.update_todo.call_count == 1
        updated_todo = external_todo_app_mock.update_todo.call_args_list[0].args[0]
        assert updated_todo.done is True
        assert updated_todo.id == todo.id

    def test_not_marking_local_todo_as_done_if_external_todo_is_done_too(
        self,
        external_todo_app_mock,
    ):
        config = get_mock_config()
        vault = Vault.create(config=config)

        project_todo = ExternalTodo(id=123, text="🕹 Игры", done=False)
        todo = ExternalTodo(
            id=1253, text="todo", done=True, external_parent_id=project_todo.id
        )

        external_todo_app_mock.get_todos = lambda: [project_todo, todo]
        external_todo_app_mock.update_todo = UpdateTodoMock()

        note = ProjectNote(name="🕹 Игры", text="lalala", config=config)
        note.add_todo(Todo(done=True, text="todo"))
        vault.projects_dir.add_child(note)

        syncer = ExternalTodosSyncer(external_todo_app_mock, vault, config)

        syncer.sync()

        assert todo.done is True
        assert external_todo_app_mock.update_todo.call_count == 0

    # fixing bug
    def test_create_external_todo_even_if_there_is_same_but_old_and_done(self):
        config = get_mock_config()
        vault = Vault.create(config=config)
        project_todo = ExternalTodo(id=123, text="🕹 Игры", done=False)
        external_todo = ExternalTodo(
            id=1253,
            text="todo",
            done=True,
            external_parent_id=project_todo.id,
            updated_at=datetime.now() - timedelta(hours=1),
        )
        external_todo_app_mock.get_todos = lambda: [project_todo, external_todo]
        external_todo_app_mock.create_todo = CreateTodoMock()
        external_todo_app_mock.update_todo = UpdateTodoMock()

        todo = create_todo(done=False, text="todo", updated_at=datetime.now())
        note = ProjectNote(name="🕹 Игры", text="lalala", config=config)
        note.add_todo(todo)
        vault.projects_dir.add_child(note)

        syncer = ExternalTodosSyncer(external_todo_app_mock, vault, config)
        syncer.sync()

        assert external_todo_app_mock.update_todo.call_count == 0
        assert external_todo_app_mock.create_todo.call_count == 1
        new_todo = external_todo_app_mock.create_todo.call_args_list[0].args[0]
        assert isinstance(new_todo, ExternalTodo)
        assert new_todo.text == "todo"
        assert new_todo.external_parent_id == 123

    def test_recreate_external_project_todo_if_it_was_engaged(self):
        config = get_mock_config()
        vault = Vault.create(config=config)

        note = ProjectNote(name="🕹 Игры", text="lalala", config=config)
        todo = create_todo(done=False, text="todo")
        note.add_todo(todo)
        vault.projects_dir.add_child(note)

        external_todo = ExternalTodo(done=False, text="todo", external_parent_id="123")
        external_todo_app_mock.get_todos = lambda: [
            ExternalTodo(done=True, text="🕹 Игры", id="123"),
            external_todo,
        ]

        external_todo_app_mock.create_todo = CreateTodoMock()
        external_todo_app_mock.update_todo = UpdateTodoMock()

        syncer = ExternalTodosSyncer(external_todo_app_mock, vault, config)

        syncer.sync()

        assert external_todo_app_mock.create_todo.call_count == 2

        new_todo1 = external_todo_app_mock.create_todo.call_args_list[0].args[0]
        assert new_todo1.text == note.name
        assert new_todo1.done is False
        assert external_todo.external_parent_id == new_todo1.id

        new_todo2 = external_todo_app_mock.create_todo.call_args_list[1].args[0]

        assert new_todo2.text == todo.text
        assert new_todo2.done is False
        assert new_todo2.external_parent_id == new_todo1.id

    # todoist automatically closes all subtodos, this is not what we want though
    def test_external_todos_of_engaged_project_are_ignored(
        self,
        external_todo_app_mock,
    ):
        config = get_mock_config()
        vault = Vault.create(config=config)
        note = ProjectNote(name="🕹 Игры", text="lalala", config=config)
        todo = create_todo(text="пройти зельду", done=False)
        note.add_todo(todo)
        vault.projects_dir.add_child(note)

        # ***ing todoist brakes link between child todo and project todo when they are done
        project_todo = ExternalTodo(id=4534534, text="🕹 Игры", done=True)
        child_todo = ExternalTodo(id=4526, text="пройти зельду", done=True)
        child_todo.external_parent_id = project_todo.id
        external_todo_app_mock.get_todos = lambda: [
            project_todo,
            child_todo,
        ]

        syncer = ExternalTodosSyncer(external_todo_app_mock, vault, config)

        syncer.sync()

        assert todo.done is False

    # fixing bug
    def test_done_orphaned_external_todo_same_as_not_done_local_project_todo(
        self,
        external_todo_app_mock,
    ):
        # pizdec
        config = get_mock_config()
        vault = Vault.create(config=config)

        external_todo_app_mock.create_todo = CreateTodoMock()

        note = ProjectNote(name="🕹 Игры", text="lalala", config=config)
        todo = create_todo(text="todo", done=False)
        todo.updated_at = datetime.now()
        note.add_todo(todo)
        vault.projects_dir.add_child(note)

        external_todo_app_mock.get_todos = lambda: [
            ExternalTodo(
                id=1234,
                text="todo",
                done=True,
                updated_at=datetime.now() - timedelta(hours=1),
            ),
            ExternalTodo(id=123, text="🕹 Игры", done=False),
        ]

        syncer = ExternalTodosSyncer(external_todo_app_mock, vault, config)

        syncer.sync()

        assert external_todo_app_mock.create_todo.call_count == 1

        assert (
            external_todo_app_mock.create_todo.call_args_list[0]
            .args[0]
            .external_parent_id
            == 123
        )


# class TestSourcingProjectPriorityFromScheduling:
#     def test_create_project(
#         self,
#         external_todo_app_mock,
#     ):
#         config = get_mock_config()
#         vault = Vault.create(config=config)

#         note = ProjectNote(name="🕹 Игры", text="lalala", config=config)
#         vault.projects_dir.add_child(note)
#         external_todo_app_mock.create_todo = CreateTodoMock()

#         syncer = ExternalTodosSyncer(
#             external_todo_app_mock,
#             vault,
#             config,
#             get_today_projects=lambda: [note],
#         )

#         syncer.sync()

#         assert external_todo_app_mock.create_todo.call_count == 1
#         assert (
#             external_todo_app_mock.create_todo.call_args_list[0].args[0].priority
#             == Priority.today
#         )

#     def test_update_project_with_high_priority(
#         self,
#         external_todo_app_mock,
#     ):
#         config = get_mock_config()
#         vault = Vault.create(config=config)

#         note = ProjectNote(name="🕹 Игры", text="lalala", config=config)
#         vault.projects_dir.add_child(note)
#         external_todo_app_mock.update_todo = UpdateTodoMock()
#         project_todo = ExternalTodo(
#             id=4526, text="🕹 Игры", done=False
#         )  # this todo should be represented as a project in vault
#         external_todo_app_mock.get_todos = lambda: [
#             project_todo,
#         ]

#         syncer = ExternalTodosSyncer(
#             external_todo_app_mock,
#             vault,
#             config,
#             get_today_projects=lambda: [note],
#         )

#         syncer.sync()

#         assert external_todo_app_mock.update_todo.call_count == 1
#         assert (
#             external_todo_app_mock.update_todo.call_args_list[0].args[0].priority
#             == Priority.today
#         )

#     def test_update_project_downgrade_priority(
#         self,
#         external_todo_app_mock,
#     ):
#         config = get_mock_config()
#         vault = Vault.create(config=config)

#         note = ProjectNote(name="🕹 Игры", text="lalala", config=config)
#         vault.projects_dir.add_child(note)
#         external_todo_app_mock.update_todo = UpdateTodoMock()
#         external_todo_app_mock.get_todos = lambda: [
#             ExternalTodo(id=4526, text="🕹 Игры", done=False, priority=Priority.today),
#         ]

#         syncer = ExternalTodosSyncer(
#             external_todo_app_mock,
#             vault,
#             config,
#             get_today_projects=lambda: [],
#         )

#         syncer.sync()

#         assert external_todo_app_mock.update_todo.call_count == 1
#         assert (
#             external_todo_app_mock.update_todo.call_args_list[0].args[0].priority
#             == Priority.later
#         )
