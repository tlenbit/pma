from models import Note, ProjectNote, create_todo
from tests.utils import get_mock_config


class TestAliases:
    def test_parse_regular(self):
        config = get_mock_config(vault_number=666)

        note = Note(
            name="Пианино", text="---\naliases: [piano]\n---\n\nlalala", config=config
        )

        assert note.get_aliases() == ("piano",)

    def test_parse_trailing_comma(self):
        config = get_mock_config(vault_number=666)

        note = Note(
            name="Пианино", text="---\naliases: [piano,]\n---\n\nlalala", config=config
        )

        assert note.get_aliases() == ("piano",)

    def test_parse_converting_to_lower(self):
        config = get_mock_config(vault_number=666)

        note = Note(
            name="Пианино",
            text="---\naliases: [Piano,huiano]\n---\n\nlalala",
            config=config,
        )

        assert set(note.get_aliases()) == {"piano", "huiano"}

    def test_parse_with_spaces(self):
        config = get_mock_config(vault_number=666)

        note = Note(
            name="Пианино",
            text="---\naliases: [piano, huiano, ]\n---\n\nlalala",
            config=config,
        )

        assert set(note.get_aliases()) == {"piano", "huiano"}

    def test_change_aliases(self):
        config = get_mock_config(vault_number=666)

        note = Note(
            name="Пианино",
            text="---\naliases: [Piano,huiano]\n---\n\nlalala",
            config=config,
        )

        note.set_aliases(["peano"])

        assert "aliases: [peano,]" in note.text

    def test_change_aliases_multiple(self):
        config = get_mock_config(vault_number=666)

        note = Note(
            name="Пианино",
            text="---\naliases: [Piano,huiano]\n---\n\nlalala",
            config=config,
        )

        note.set_aliases(("peano", "hueano"))

        assert set(note.get_aliases()) == {"peano", "hueano"}

    def test_change_aliases_using_tuple(self):
        config = get_mock_config(vault_number=666)

        note = Note(
            name="Пианино",
            text="---\naliases: [Piano,huiano]\n---\n\nlalala",
            config=config,
        )

        note.set_aliases(("peano",))

        assert "aliases: [peano,]" in note.text

    def test_add_alias(self):
        config = get_mock_config(vault_number=666)

        note = Note(
            name="Пианино",
            text="---\naliases: []\n---\n\nlalala",
            config=config,
        )

        note.add_alias("peano")

        assert "aliases: [peano,]" in note.text

    def test_add_alias_idempotency(self):
        config = get_mock_config(vault_number=666)

        note = Note(
            name="Пианино",
            text="---\naliases: []\n---\n\nlalala",
            config=config,
        )

        note.add_alias("peano")
        note.add_alias("peano")

        assert "aliases: [peano,]" in note.text


def test_read_empty_metadata():
    config = get_mock_config(vault_number=666)

    note = Note(
        name="Пианино",
        text="---\n---\nlalala",
        config=config,
    )

    assert note.metadata == "---\n---"


def test_create_metadata_when_adding_alias():
    config = get_mock_config(vault_number=666)

    note = Note(
        name="Пианино",
        text="",
        config=config,
    )

    assert not note.metadata

    note.add_alias("peano")

    assert note.metadata
    assert "aliases: [peano,]" in note.text


def test_remove_duplicate_aliases_if_present():
    config = get_mock_config(vault_number=666)

    note = Note(
        name="Пианино",
        text="---\naliases: [p iano,p iano]\n---\n\nlalala",
        config=config,
    )

    assert "aliases: [p iano,]" in note.text


class TestInternalLinksParsing:
    def test_internal_basic(self):
        config = get_mock_config(vault_number=666)

        note = Note(
            name="opana",
            text="asdf [[lalala]] gjiofg",
            config=config,
        )
        assert note.internal_links == ["lalala"]

    def test_internal_links_with_whitespaces(self):
        config = get_mock_config(vault_number=666)

        note = Note(
            name="opana",
            text="asdf [[ lalala ]] gjiofg",
            config=config,
        )
        assert note.internal_links == ["lalala"]

    def test_broken_parenthesis(self):
        config = get_mock_config(vault_number=666)

        note = Note(
            name="opana",
            text="asdf [[ lalala ] gjiofg",
            config=config,
        )
        assert note.internal_links == []


def test_get_child_todos_creates_new_object():
    config = get_mock_config(vault_number=666)

    note = ProjectNote(
        name="opana",
        text="asdfgjiofg",
        config=config,
    )
    todo = create_todo(done=False, text="awd")
    note.add_todo(todo)
    assert note.get_todos() is not note.get_todos()
    assert note.get_todos() is not note._todos
