import os
import shutil
from pathlib import Path

from config import Config
from models import Directory, Note, ProjectNote, Todo, Vault, create_todo
from tests.utils import get_mock_config


class TestWriteVaultToFs:
    def test_if_root_folder_does_not_exist(self):
        config = get_mock_config(vault_number=666)
        vault = Vault.create(config)

        assert os.path.isdir(config.vault_root_dir) is False

        vault.write_to_fs()

        assert os.path.isdir(config.vault_root_dir) is True

        shutil.rmtree(config.vault_root_dir)

    def test_if_root_folder_already_exists(self):
        config = get_mock_config(vault_number=15)
        vault = Vault.create(config)

        assert os.path.isdir(config.vault_root_dir) is True

        vault.write_to_fs()

        assert os.path.isdir(config.vault_root_dir) is True

    def test_write_some_vault(self):
        config = get_mock_config(vault_number=16)

        # refactor file management
        if os.path.isdir(config.vault_root_dir):
            shutil.rmtree(config.vault_root_dir)

        vault = Vault.create(config)

        directory = Directory.create(name="directory", config=config)
        note1 = Note(name="note1", text="text1", config=config)
        note2 = Note(name="note2", text="text2", config=config)

        directory.add_child(note1)
        directory.add_child(note2)
        vault.root.add_child(directory)

        vault.write_to_fs()

        assert os.path.isdir(os.path.join(config.vault_root_dir, "directory")) is True

        assert (
            os.path.isfile(os.path.join(config.vault_root_dir, "directory", "note1"))
            is True
        )
        assert (
            os.path.isfile(os.path.join(config.vault_root_dir, "directory", "note2"))
            is True
        )

        with open(
            str(os.path.join(config.vault_root_dir, "directory", "note1")),
            "r",
        ) as f:
            assert f.read() == "text1"

        with open(
            str(os.path.join(config.vault_root_dir, "directory", "note2")),
            "r",
        ) as f:
            assert f.read() == "text2"

    def test_write_vault_with_deep_nested_directories(self):
        config = get_mock_config(vault_number=16)

        # refactor
        if os.path.isdir(config.vault_root_dir):
            shutil.rmtree(config.vault_root_dir)

        vault = Vault.create(config)

        note = Note(name="note", text="text1", config=config)
        directory1 = Directory.create(name="directory1", config=config)
        directory2 = Directory.create(name="directory2", config=config)
        directory3 = Directory.create(name="directory3", config=config)
        directory4 = Directory.create(name="directory4", config=config)
        vault.root.add_child(directory1)
        directory1.add_child(directory2)
        directory2.add_child(directory3)
        directory3.add_child(directory4)
        directory4.add_child(note)

        vault.write_to_fs()

        assert (
            os.path.isfile(
                os.path.join(
                    config.vault_root_dir,
                    "directory1",
                    "directory2",
                    "directory3",
                    "directory4",
                    "note",
                )
            )
            is True
        )

    def test_write_todos(self):
        config = get_mock_config(vault_number=16)

        # refactor
        if os.path.isdir(config.vault_root_dir):
            shutil.rmtree(config.vault_root_dir)

        vault = Vault.create(config)

        line1 = "line 1"
        line2 = "line 2"
        line3 = "line 3"
        text = f"{line1}\n{line2}\n{line3}"
        note = ProjectNote(name="note", text=text, config=config)

        vault.root.add_child(note)

        todo1 = create_todo(done=False, text="todo1")
        todo2 = create_todo(done=False, text="todo2")
        todo3 = create_todo(done=False, text="todo3")
        todo2.add_child(todo3)

        note.add_todo(todo1)
        note.add_todo(todo2)

        vault.write_to_fs()

        with open(
            str(os.path.join(config.vault_root_dir, "note")),
            "r",
        ) as f:
            lines = [l.strip() for l in f.readlines()]
            assert todo1.to_line() in lines
            assert todo2.to_line() in lines
            assert todo3.to_line() in lines
            assert line1 in lines
            assert line2 in lines
            assert line3 in lines


# todo: make and remove folders in context manager
# because if test fails then folders are not cleaned up


def test_create_projects_folder_if_it_does_not_exist():
    config = Config(
        vault_root_dir=Path("fixtures/vault_11"),
    )
    vault = Vault.create(config)
    assert os.path.isdir(vault.projects_dir.path) is False

    vault.write_to_fs()

    assert os.path.isdir(vault.projects_dir.path) is True

    shutil.rmtree(vault.projects_dir.path)
