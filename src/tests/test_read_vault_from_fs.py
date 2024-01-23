from pathlib import Path

from config import Config
from models import ProjectNote, Vault


def test_vault_name():
    config = Config(vault_root_dir=Path("fixtures/vault_14"))

    vault = Vault.read_from_fs(config=config)

    assert vault.name == "vault_14"


def test_read_vault_1():
    config = Config(vault_root_dir=Path("fixtures/vault_1"))

    vault = Vault.read_from_fs(config=config)

    assert vault.root.path == Path("fixtures/vault_1")
    assert len(vault.root.get_children()) == 1

    note = vault.root.get_child("note_1")
    assert note.path == Path("fixtures/vault_1/note_1")
    assert note.text == "content_1"


def test_read_vault_2():
    config = Config(vault_root_dir=Path("fixtures/vault_2"))

    vault = Vault.read_from_fs(config=config)

    assert len(vault.root.get_children()) == 4

    assert vault.root.path == Path("fixtures/vault_2")

    note_1 = vault.root.get_child("note_1")
    assert note_1.path == Path("fixtures/vault_2/note_1")
    assert note_1.text == ""

    note_2 = vault.root.get_child("note_2")
    assert note_2.path == Path("fixtures/vault_2/note_2")
    assert note_2.text == ""

    assert len(vault.root.get_child("folder_1").get_children()) == 1

    note_3 = vault.root.get_child("folder_1").get_child("note_3")
    assert note_3.path == Path("fixtures/vault_2/folder_1/note_3")
    assert note_3.text == ""

    assert len(vault.root.get_child("folder_2").get_children()) == 2

    note_4 = vault.root.get_child("folder_2").get_child("note_4")
    assert note_4.path == Path("fixtures/vault_2/folder_2/note_4")
    assert note_4.text == ""

    note_5 = vault.root.get_child("folder_2").get_child("note_5")
    assert note_5.path == Path("fixtures/vault_2/folder_2/note_5")
    assert note_5.text == ""


def test_ignore_dir():
    config = Config(
        vault_root_dir=Path("fixtures/vault_4"),
        ignore_paths=["./dir_to_be_ignored"],
    )
    vault = Vault.read_from_fs(config)

    assert vault.root.get_children() == []


def test_ignore_dir_with_trailing_slash():
    config = Config(
        vault_root_dir=Path("fixtures/vault_4"),
        ignore_paths=["./dir_to_be_ignored/"],
    )
    vault = Vault.read_from_fs(config)

    assert vault.root.get_children() == []


def test_ignore_dir_without_dot():
    config = Config(
        vault_root_dir=Path("fixtures/vault_4"),
        ignore_paths=["dir_to_be_ignored"],
    )
    vault = Vault.read_from_fs(config)

    assert vault.root.get_children() == []


def test_ignore_note():
    config = Config(
        vault_root_dir=Path("fixtures/vault_26"),
        ignore_paths=["note_to_be_ignored"],
    )
    vault = Vault.read_from_fs(config)

    assert vault.root.get_children() == []


def test_read_vault_with_todos():
    config = Config(
        vault_root_dir=Path("fixtures/vault_7"),
    )
    vault = Vault.read_from_fs(config)

    todos = vault.get_todos()

    assert set(todo.text for todo in todos) == {"todo_1", "todo_2"}


def test_read_note_with_todos():
    config = Config(vault_root_dir=Path("fixtures/vault_3"))
    vault = Vault.read_from_fs(config=config)
    todo = vault["projects/note_with_todos"].get_todos()[0]

    assert todo.done is False
    assert todo.text == "lalala"


def test_note_text_with_todos_preserve_other_lines():
    config = Config(vault_root_dir=Path("fixtures/vault_17"))
    vault = Vault.read_from_fs(config=config)

    assert {"todo1", "todo2", "todo3"} == set(todo.text for todo in vault.get_todos())
    assert not any(todo.done for todo in vault.get_todos())

    assert all(
        line in vault["projects/note"].text for line in ["line1", "line2", "line3"]
    )


# fixing a bug
def test_real_note_metainfo_is_preserved():
    config = Config(vault_root_dir=Path("fixtures/vault_18"))
    vault = Vault.read_from_fs(config=config)

    note = vault.projects_dir.get_children()[0].get_children()[0]
    metadata = "---\naliases: [Personal Management System,]\n---".lower()

    assert note.metadata != ""
    assert note.metadata == metadata
    assert note.text.startswith(metadata + "\n")

    assert metadata not in note.text[len(metadata) :]


def test_read_project_note():
    config = Config(vault_root_dir=Path("fixtures/vault_21"))
    vault = Vault.read_from_fs(config=config)

    assert len(vault.get_projects()) == 2
    assert isinstance(vault.get_projects()[0], ProjectNote)
    assert isinstance(vault.get_projects()[1], ProjectNote)


# fixing bug
def test_todos_in_project_note_have_link_to_project():
    config = Config(vault_root_dir=Path("fixtures/vault_24"))
    vault = Vault.read_from_fs(config=config)

    project = vault.get_projects()[0]
    assert vault.get_all_todos()[0].project == project
    assert vault.get_all_todos()[1].project == project


def test_todos_links_to_projects():
    config = Config(vault_root_dir=Path("fixtures/vault_23"))
    vault = Vault.read_from_fs(config=config)

    vault.get_projects()[0].get_todos()[0].project == vault.get_projects()[0]
    vault.get_projects()[1].get_todos()[0].project == vault.get_projects()[1]


def test_get_todos_preserves_todo_objects():
    config = Config(
        vault_root_dir=Path("fixtures/vault_7"),
    )
    vault = Vault.read_from_fs(config)

    todos1 = vault.get_todos()
    todos2 = vault.get_todos()

    assert {id(t) for t in todos1} == {id(t) for t in todos2}
