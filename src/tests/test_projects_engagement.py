from unittest.mock import MagicMock

from event_bus import EventBus
from models import EngageShortTodo, ProjectNote, Vault, create_todo
from modules.projects_engagement import process_done_meta_todos
from tests.utils import get_mock_config


def test_engage_project():
    config = get_mock_config()
    vault = Vault.create(config=config)
    event_bus = EventBus()
    event_bus.fire_project_engaged = MagicMock()
    note = ProjectNote(name="🕹 Игры.md", text="lalala", config=config)
    note.add_todo(create_todo(text=EngageShortTodo.template, done=True))
    vault.projects_dir.add_child(note)

    process_done_meta_todos(vault, event_bus)

    assert event_bus.fire_project_engaged.call_count == 1
    assert event_bus.fire_project_engaged.call_args_list[0][1]["minutes"] == 20


# fixing bug
def test_engage_project_with_other_todos():
    config = get_mock_config()
    vault = Vault.create(config=config)
    event_bus = EventBus()
    event_bus.fire_project_engaged = MagicMock()
    note = ProjectNote(name="🕹 Игры.md", text="lalala", config=config)
    note.add_todo(create_todo(text="awd", done=False))
    note.add_todo(create_todo(text=EngageShortTodo.template, done=True))
    vault.projects_dir.add_child(note)

    process_done_meta_todos(vault, event_bus)

    assert event_bus.fire_project_engaged.call_count == 1
    assert event_bus.fire_project_engaged.call_args_list[0][1]["minutes"] == 20
