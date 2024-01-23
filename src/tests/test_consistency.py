from models import Note, ProjectNote, SchedulingNote, Vault, create_todo
from modules.notes_consistency import (
    add_translited_name_to_notes_aliases,
    delete_all_done_todos,
    ensure_meta_todos_present_in_every_project,
)
from tests.utils import get_mock_config


class TestAddTranslitedNameAlias:
    def test_simple(self):
        config = get_mock_config(vault_number=666)
        vault = Vault.create(config=config)

        note = Note(
            name="Пианино",
            text="---\naliases: []\n---\n\nlalala",
            config=config,
        )

        vault.projects_dir.add_child(note)

        add_translited_name_to_notes_aliases(vault)

        assert "gbfybyj" in note.text

    def test_english_not_changed(self):
        config = get_mock_config(vault_number=666)
        vault = Vault.create(config=config)

        note = Note(
            name="Pianino",
            text="---\naliases: []\n---\n\nlalala",
            config=config,
        )

        vault.projects_dir.add_child(note)

        add_translited_name_to_notes_aliases(vault)

        assert (
            "aliases: []" in note.text
            or "aliases: [,]" in note.text
            or "aliases:[]" in note.text
        )


# fixing bug
def test_no_duplicates_after_transliteration():
    config = get_mock_config(vault_number=666)
    vault = Vault.create(config=config)

    note = Note(
        name="Аккорды",
        text="---\naliases: [frrjhls,]\n---\n\nawojdhjsngf",
        config=config,
    )
    vault.root.add_child(note)
    add_translited_name_to_notes_aliases(vault)

    assert note.text.startswith("---\naliases: [frrjhls,]\n---")


class TestMetaTodoInProjects:
    def test_engage_todo_is_added_to_every_project_note(self):
        config = get_mock_config(vault_number=666)
        vault = Vault.create(config=config)

        note = ProjectNote(
            name="Project",
            text="---\naliases: [frrjhls,]\n---\n\nawojdhjsngf",
            config=config,
        )
        vault.projects_dir.add_child(note)

        assert len(note.get_todos()) == 0

        ensure_meta_todos_present_in_every_project(vault)

        assert "♲ 20 mins of Project" in [t.text for t in note.get_todos()]

    def test_engage_todo_is_not_added_to_non_project_notes(self):
        config = get_mock_config(vault_number=666)
        vault = Vault.create(config=config)

        note = ProjectNote(
            name="Project",
            text="---\naliases: [frrjhls,]\n---\n\nawojdhjsngf",
            config=config,
        )
        vault.root.add_child(note)  # not projects dir

        assert len(note.get_todos()) == 0

        ensure_meta_todos_present_in_every_project(vault)

        assert len(note.get_todos()) == 0

    def test_scheduling_meta_todo(self):
        config = get_mock_config(vault_number=666)
        vault = Vault.create(config=config)

        note = SchedulingNote(
            name="Scheduling",
            text="",
            config=config,
        )
        vault.projects_dir.add_child(note)

        assert len(note.get_todos()) == 0

        ensure_meta_todos_present_in_every_project(vault)

        assert len(note.get_todos()) == 1


def test_delete_all_done_todos():
    config = get_mock_config(vault_number=666)
    vault = Vault.create(config=config)

    note = ProjectNote(
        name="Project",
        text="---\naliases: [frrjhls,]\n---\n\nawojdhjsngf",
        config=config,
    )

    note.add_todo(create_todo(done=False, text="todo1"))
    note.add_todo(create_todo(done=True, text="todo2"))
    todo3 = create_todo(done=False, text="todo3")
    todo3.add_child(create_todo(done=True, text="todo4"))
    todo3.add_child(create_todo(done=False, text="todo5"))
    note.add_todo(todo3)
    vault.projects_dir.add_child(note)

    delete_all_done_todos(vault)

    assert len(note.get_todos()) == 2
    assert note.get_todos()[0].text == "todo1"
    assert note.get_todos()[1].text == "todo3"
    assert len(note.get_todos()[1].children) == 1
    assert note.get_todos()[1].children[0].text == "todo5"
