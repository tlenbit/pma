from models import EngageShortTodo, ProjectNote, Todo, Vault, create_todo
from tests.utils import get_mock_config


def test_add_todo_to_a_note():
    config = get_mock_config(vault_number=404)
    vault = Vault.create(config=config)
    note = ProjectNote(
        name="note",
        text="",
        config=config,
    )
    vault.projects_dir.add_child(note)

    todo = create_todo(done=False, text="to do")

    note.add_todo(todo)
    assert len(note.get_todos()) == 1
    assert note.get_todos()[0].text == "to do"
    assert note.get_todos()[0].done is False

    assert "- [ ] to do" in note.text
    assert note.parent == vault.projects_dir


def test_parse_not_done_todo():
    todo = Todo.parse_from_line(
        line="- [ ] test_todo",
    )

    assert todo.done is False
    assert todo.text == "test_todo"


def test_parse_done_todo():
    todo = Todo.parse_from_line(
        line="- [x] test_todo",
    )

    assert todo.done is True
    assert todo.text == "test_todo"


class TestParseFromLines:
    def test_parse_1_child(self):
        todos = Todo.parse_from_lines(
            lines=[
                "- [ ] parent_todo",
                "\t- [ ] child_todo",
            ]
        )
        assert len(todos) == 1
        assert todos[0].text == "parent_todo"
        assert len(todos[0].children) == 1
        assert todos[0].children[0].text == "child_todo"

    def test_parse_many_children(self):
        todos = Todo.parse_from_lines(
            lines=[
                "- [ ] parent_todo",
                "\t- [ ] child_todo1",
                "\t- [ ] child_todo2",
                "\t- [ ] child_todo3",
            ]
        )
        assert len(todos) == 1
        assert todos[0].text == "parent_todo"
        assert len(todos[0].children) == 3

    def test_parse_many_parents_many_children(self):
        todos = Todo.parse_from_lines(
            lines=[
                "- [ ] parent_todo1",
                "\t- [ ] child_todo1",
                "- [ ] parent_todo2",
                "\t- [ ] child_todo2",
                "\t- [ ] child_todo3",
            ]
        )
        assert len(todos) == 2
        assert todos[0].text == "parent_todo1"
        assert len(todos[0].children) == 1
        assert todos[0].children[0].text == "child_todo1"

        assert todos[1].text == "parent_todo2"
        assert len(todos[1].children) == 2
        assert todos[1].children[0].text == "child_todo2"
        assert todos[1].children[1].text == "child_todo3"

    def test_parse_deep_nested_todos(self):
        todos = Todo.parse_from_lines(
            lines=[
                "- [ ] todo1",
                "\t- [ ] todo2",
                "\t\t- [ ] todo3",
            ]
        )
        assert len(todos) == 1
        todo1 = todos[0]
        assert todo1.text == "todo1"
        assert len(todo1.children) == 1
        todo2 = todo1.children[0]
        assert todo2.text == "todo2"
        assert len(todos[0].children[0].children) == 1
        todo3 = todo2.children[0]
        assert todo3.text == "todo3"

    def test_parse_deep_nested_then_1_step_down(self):
        todos = Todo.parse_from_lines(
            lines=[
                "- [ ] todo1",
                "\t- [ ] todo2",
                "\t\t- [ ] todo3",
                "\t- [ ] todo4",
            ]
        )
        assert len(todos) == 1
        todo1 = todos[0]
        assert todo1.text == "todo1"
        assert len(todo1.children) == 2
        todo2 = todo1.children[0]
        assert todo2.text == "todo2"
        assert len(todos[0].children[0].children) == 1
        todo3 = todo2.children[0]
        assert todo3.text == "todo3"

        todo4 = todo1.children[1]
        assert todo4.text == "todo4"

    def test_parse_deep_nested_then_not_nested(self):
        todos = Todo.parse_from_lines(
            lines=[
                "- [ ] todo1",
                "\t- [ ] todo2",
                "\t\t- [ ] todo3",
                "- [ ] todo4",
            ]
        )
        assert len(todos) == 2
        todo1 = todos[0]
        assert todo1.text == "todo1"
        assert len(todo1.children) == 1
        todo2 = todo1.children[0]
        assert todo2.text == "todo2"
        assert len(todos[0].children[0].children) == 1
        todo3 = todo2.children[0]
        assert todo3.text == "todo3"

        todo4 = todos[1]
        assert todo4.text == "todo4"


class TestConvertTodoToLines:
    def test_1_todo_no_subtodos(self):
        todo = create_todo(done=False, text="todo")

        lines = todo.to_lines()

        assert lines == ["- [ ] todo"]

    def test_1_todo_with_1_subtodo(self):
        todo1 = create_todo(done=False, text="todo1")
        todo2 = create_todo(done=False, text="todo2")
        todo1.add_child(todo2)

        lines = todo1.to_lines()

        assert lines == ["- [ ] todo1", "\t- [ ] todo2"]

    def test_1_todo_with_2_subtodos(self):
        todo1 = create_todo(done=False, text="todo1")
        todo2 = create_todo(done=False, text="todo2")
        todo3 = create_todo(done=False, text="todo3")
        todo1.add_child(todo2)
        todo1.add_child(todo3)

        lines = todo1.to_lines()

        assert lines == ["- [ ] todo1", "\t- [ ] todo2", "\t- [ ] todo3"]

    def test_deep_nested(self):
        todo1 = create_todo(done=False, text="todo1")
        todo2 = create_todo(done=False, text="todo2")
        todo3 = create_todo(done=False, text="todo3")
        todo1.add_child(todo2)
        todo2.add_child(todo3)

        lines = todo1.to_lines()

        assert lines == ["- [ ] todo1", "\t- [ ] todo2", "\t\t- [ ] todo3"]

    def test_nested_then_not_nested(self):
        todo1 = create_todo(done=False, text="todo1")
        todo2 = create_todo(done=False, text="todo2")
        todo3 = create_todo(done=False, text="todo3")
        todo4 = create_todo(done=False, text="todo4")

        todo1.add_child(todo2)
        todo2.add_child(todo3)
        todo1.add_child(todo4)

        lines = todo1.to_lines()

        assert lines == [
            "- [ ] todo1",
            "\t- [ ] todo2",
            "\t\t- [ ] todo3",
            "\t- [ ] todo4",
        ]


def test_traverse_bfs():
    todo1 = create_todo(done=False, text="todo1")
    todo2 = create_todo(done=False, text="todo2")
    todo3 = create_todo(done=False, text="todo3")
    todo4 = create_todo(done=False, text="todo4")
    todo1.add_child(todo2)
    todo2.add_child(todo3)
    todo1.add_child(todo4)

    todos = list(todo1.traverse())

    assert len(todos) == 4
    assert todos[0] == todo1
    assert todos[1] == todo2
    assert todos[2] == todo4
    assert todos[3] == todo3


def test_get_child():
    todo1 = create_todo(done=False, text="todo1")
    todo2 = create_todo(done=False, text="todo2")
    todo3 = create_todo(done=False, text="todo3")
    todo1.add_child(todo2)
    todo1.add_child(todo3)

    assert todo1.get_child(todo2.text) == todo2
    assert todo1.get_child(todo3.text) == todo3


def test_traverse_preserves_objects():
    todo1 = create_todo(done=False, text="todo1")
    todo2 = create_todo(done=False, text="todo2")
    todo3 = create_todo(done=False, text="todo3")
    todo4 = create_todo(done=False, text="todo4")
    todo1.add_child(todo2)
    todo2.add_child(todo3)
    todo1.add_child(todo4)

    todos1 = list(todo1.traverse())
    todos2 = list(todo1.traverse())

    assert {id(t) for t in todos1} == {id(t) for t in todos2}


def test_delete_child_todo():
    child = create_todo(done=False, text="child")
    parent = create_todo(done=False, text="parent")
    parent.add_child(child)

    child.delete()

    assert len(parent.children) == 0


def test_delete_todo_in_project():
    config = get_mock_config(vault_number=404)
    vault = Vault.create(config=config)
    todo = create_todo(done=False, text="todo")
    project = ProjectNote(name="🕹 Игры", text="lalala", config=config)
    project.add_todo(todo)
    vault.projects_dir.add_child(project)

    assert len(project.get_todos()) == 1
    assert len(vault.get_todos()) == 1

    todo.delete()

    assert len(project.get_todos()) == 0
    assert len(vault.get_todos()) == 0


def test_create_meta_todo():
    todo = create_todo(done=False, text="♲ 20 mins of СОН")

    assert isinstance(todo, EngageShortTodo)


def test_get_children_creates_new_object():
    todo = create_todo(done=False, text="awd")
    todo1 = create_todo(done=False, text="awd1")
    todo.add_child(todo1)
    assert todo.children is not todo.children
    assert todo.children is not todo._children
