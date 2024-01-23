from datetime import datetime
from pathlib import Path

import pytest
from config import Config
from models import Directory, Note, ProjectNote, Todo, Vault, create_todo
from modules.notes_consistency import delete_duplicate_todos
from tests.utils import get_mock_config


def test_vault_getitem():
    config = Config(
        vault_root_dir=Path("fixtures/vault_8"),
    )
    vault = Vault.read_from_fs(config)

    note = vault["a/b/c"]

    assert note.text == "lalala"


def test_vault_getitem_with_dot():
    config = Config(
        vault_root_dir=Path("fixtures/vault_8"),
    )
    vault = Vault.read_from_fs(config)

    note = vault["./a/b/c"]

    assert note.text == "lalala"


def test_add_directory_child_note():
    config = get_mock_config(vault_number=666)
    vault = Vault.create(config=config)

    note = Note(name="note", text="hehe", config=config)

    vault.root.add_child(note)

    assert vault["note"].name == "note"
    assert vault["note"].text == "hehe"


def test_add_same_child_note_2_times_fails():
    config = get_mock_config(vault_number=666)
    vault = Vault.create(config=config)

    note = Note(name="note", text="hehe", config=config)

    vault.root.add_child(note)

    with pytest.raises(AssertionError):
        vault.root.add_child(note)


def test_add_child_directory():
    config = get_mock_config(vault_number=666)
    vault = Vault.create(config=config)

    directory = Directory.create(name="dir", config=config)

    vault.root.add_child(directory)

    assert directory in vault.root.get_children()


def test_get_root_note_todos():
    config = get_mock_config(vault_number=666)
    vault = Vault.create(config=config)

    note1 = ProjectNote(name="note1", text="hehe", config=config)
    vault.root.add_child(note1)

    todo1 = create_todo(done=False, text="todo1")
    todo2 = create_todo(done=False, text="todo2")

    note1.add_todo(todo1)
    note1.add_todo(todo2)

    assert len(vault.root.get_child("note1").get_todos()) == 2
    assert vault.root.get_child("note1").get_todos()[0].done is False
    assert vault.root.get_child("note1").get_todos()[0].text == "todo1"
    assert vault.root.get_child("note1").get_todos()[1].done is False
    assert vault.root.get_child("note1").get_todos()[1].text == "todo2"


# def test_get_note_todos_with_nested_todos():
#     config = get_mock_config(vault_number=666)
#     vault = Vault.create(config=config)

#     note1 = Note(name="note1", text="hehe", config=config)
#     vault.root.add_child(note1)

#     todo1 = create_todo(done=False, text="todo1")
#     todo2 = create_todo(done=False, text="todo2")
#     todo1.add_child(todo2)

#     note1.add_todo(todo1)

#     assert len(vault.root.get_child("note1").get_todos()) == 2
#     assert vault.root.get_child("note1").get_todos()[0].done is False
#     assert vault.root.get_child("note1").get_todos()[0].text == "todo1"
#     assert vault.root.get_child("note1").get_todos()[1].done is False
#     assert vault.root.get_child("note1").get_todos()[1].text == "todo2"


def test_get_todos_in_nested_dir():
    config = get_mock_config(vault_number=666)
    vault = Vault.create(config=config)

    dir1 = Directory.create(name="dir1", config=config)
    vault.projects_dir.add_child(dir1)

    dir2 = Directory.create(name="dir2", config=config)
    dir1.add_child(dir2)

    note = ProjectNote(name="note", text="", config=config)
    dir2.add_child(note)

    todo = create_todo(done=False, text="to do")

    note.add_todo(todo)

    assert len(vault["projects/dir1/dir2/note"].get_todos()) == 1
    assert vault["projects/dir1/dir2/note"].get_todos()[0].done is False
    assert vault["projects/dir1/dir2/note"].get_todos()[0].text == "to do"

    assert len(vault.get_todos()) == 1
    assert vault.get_todos()[0].done is False
    assert vault.get_todos()[0].text == "to do"


def test_get_vault_todos():
    config = get_mock_config(vault_number=666)
    vault = Vault.create(config=config)

    note1 = ProjectNote(name="note1", text="hehe", config=config)

    todo1 = create_todo(done=False, text="todo1")
    todo2 = create_todo(done=False, text="todo2")

    note1.add_todo(todo1)
    note1.add_todo(todo2)

    note2 = ProjectNote(name="note2", text="hehehe", config=config)

    todo3 = create_todo(done=True, text="todo3")

    note2.add_todo(todo3)

    vault.root.add_child(note1)
    vault.root.add_child(note2)

    directory = Directory.create(name="dir", config=config)
    vault.root.add_child(directory)

    note3 = Note(name="note3", text="khekhe", config=config)

    directory.add_child(note3)

    assert vault.root.get_child("note1").name == "note1"
    assert "hehe" in vault.root.get_child("note1").text
    assert len(vault.root.get_child("note1").get_todos()) == 2
    assert vault.root.get_child("note1").get_todos()[0].done is False
    assert vault.root.get_child("note1").get_todos()[0].text == "todo1"
    assert vault.root.get_child("note1").get_todos()[1].done is False
    assert vault.root.get_child("note1").get_todos()[1].text == "todo2"

    assert vault.root.get_child("note2").name == "note2"
    assert "hehehe" in vault.root.get_child("note2").text

    assert vault.root.get_child("dir").get_child("note3").name == "note3"
    assert "khekhe" in vault.root.get_child("dir").get_child("note3").text


# fixing bug - error if regular notes are present besides project notes
def test_get_all_todos():
    config = Config(
        vault_root_dir=Path("fixtures/vault_27"),
    )
    vault = Vault.read_from_fs(config)

    vault.get_all_todos()  # should work


def test_get_projects_dir():
    config = get_mock_config(vault_number=666)
    vault = Vault.create(config=config)

    assert isinstance(vault.projects_dir, Directory)
    assert vault[config.projects_dir_name] == vault.projects_dir


def test_get_projects():
    config = get_mock_config(vault_number=666)
    vault = Vault.create(config=config)

    directory_for_projects_about_learning = Directory.create(
        name="learn", config=config
    )
    note_inside_subdir = ProjectNote(
        name="🎤 Пение и Речь", text="lalala", config=config
    )
    directory_for_projects_about_learning.add_child(note_inside_subdir)
    note_in_the_project_root = ProjectNote(
        name="🚑 Здоровье", text="lalala", config=config
    )
    vault.projects_dir.add_child(directory_for_projects_about_learning)
    vault.projects_dir.add_child(note_in_the_project_root)
    note_that_should_not_be_returned = Note(
        name="Just some random note", text="lalala", config=config
    )
    vault.root.add_child(note_that_should_not_be_returned)

    assert note_inside_subdir in vault.get_projects()
    assert note_in_the_project_root in vault.get_projects()
    assert note_that_should_not_be_returned not in vault.get_projects()

    assert vault.get_project("🎤 Пение и Речь")
    assert vault.get_project("🚑 Здоровье")
    assert not vault.get_project("Just some random note")
    assert not vault.get_project("sljgheirfgiurnj")


def test_get_notes():
    config = get_mock_config(vault_number=666)
    vault = Vault.create(config=config)

    directory = Directory.create(name="directory", config=config)
    note1 = Note(name="note1", text="awd", config=config)
    note2 = Note(name="note2", text="awd", config=config)
    directory.add_child(note2)
    vault.projects_dir.add_child(note1)
    vault.root.add_child(directory)

    assert note1 in vault.get_notes()
    assert note2 in vault.get_notes()


class TestDeleteDuplicateTodos:
    def test_delete_duplicate_todos_same_note(self):
        config = get_mock_config(vault_number=666)
        vault = Vault.create(config=config)

        note = ProjectNote(name="note1", text="awd", config=config)
        todo1 = create_todo(done=False, text="todo")
        todo2 = create_todo(done=False, text="todo")
        note.add_todo(todo1)
        note.add_todo(todo2)
        vault.projects_dir.add_child(note)

        len(vault.get_all_todos()) == 2
        len(note.get_todos()) == 2

        delete_duplicate_todos(vault)

        len(vault.get_all_todos()) == 1
        len(note.get_todos()) == 1

    def test_delete_duplicate_subtodos(self):
        config = get_mock_config(vault_number=666)
        vault = Vault.create(config=config)

        note = ProjectNote(name="note1", text="awd", config=config)
        parent = create_todo(done=False, text="parent")
        todo1 = create_todo(done=False, text="todo")
        todo2 = create_todo(done=False, text="todo")
        parent.add_child(todo1)
        parent.add_child(todo2)
        note.add_todo(parent)
        vault.projects_dir.add_child(note)

        assert len(vault.get_all_todos()) == 3

        delete_duplicate_todos(vault)

        assert len(vault.get_all_todos()) == 2


def test_vault_updated_at():
    config = get_mock_config(vault_number=666)
    vault = Vault.create(config=config)

    note1 = ProjectNote(
        name="note1", text="awd", config=config, updated_at=datetime(2021, 8, 22)
    )
    note2 = ProjectNote(
        name="note2", text="awd", config=config, updated_at=datetime(2222, 8, 22)
    )
    vault.projects_dir.add_child(note1)
    vault.projects_dir.add_child(note2)

    assert vault.updated_at == datetime(2222, 8, 22)
