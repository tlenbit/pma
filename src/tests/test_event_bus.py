from unittest.mock import MagicMock

from event_bus import (
    EventBus,
    MetaTodoHasBeenDone,
    ProjectEngagedEvent,
    ProjectEngagedSubscriber,
    SchedulingReset,
    SchedulingResetSubscriber,
)
from models import EngageShortTodo, ProjectNote, SchedulingResetTodo, create_todo
from tests.utils import get_mock_config


class TestSubscriber(ProjectEngagedSubscriber, SchedulingResetSubscriber):
    def handle_project_engaged(self, project: ProjectNote):
        ...

    def handle_scheduling_reset(self):
        ...


def test_project_engaged_event():
    event_bus = EventBus()
    subscriber = TestSubscriber()
    subscriber.handle_project_engaged = MagicMock()
    event_bus.subscribe(event_type=ProjectEngagedEvent, subscriber=subscriber)
    project = ProjectNote(name="name", text="text", config=get_mock_config())
    todo = create_todo(text=EngageShortTodo.template, done=True)

    event_bus.fire_done_meta_todo(todo=todo, project=project)

    assert subscriber.handle_project_engaged.call_count == 1
    assert subscriber.handle_project_engaged.call_args_list[0].args[0] is project
    assert subscriber.handle_project_engaged.call_args_list[0].args[1] == 20  # minutes


def test_scheduing_reset_event():
    event_bus = EventBus()
    subscriber = TestSubscriber()
    subscriber.handle_scheduling_reset = MagicMock()
    event_bus.subscribe(event_type=SchedulingReset, subscriber=subscriber)
    todo = create_todo(text=SchedulingResetTodo.template, done=True)

    event_bus.fire_done_meta_todo(todo=todo)

    assert subscriber.handle_scheduling_reset.call_count == 1
