import logging
from abc import ABC, abstractmethod
from typing import Optional, Type

from models import (
    EngageLongTodo,
    EngageMediumTodo,
    EngageShortTodo,
    MetaTodo,
    ProjectNote,
    SchedulingResetTodo,
    Todo,
)
from pydantic import BaseModel, ConfigDict


class Event(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


class ProjectEngagedEvent(Event):
    project: ProjectNote
    minutes: int


class MetaTodoHasBeenDone(Event):
    todo: MetaTodo
    project: ProjectNote


class SchedulingReset(Event):
    ...


class EventSubscriber(ABC):
    event_type: Type[Event]

    @abstractmethod
    def handle_event(self, event: Event):
        pass


class ProjectEngagedSubscriber(EventSubscriber):
    def handle_event(self, event: Event):
        super().handle_event(event)
        if isinstance(event, ProjectEngagedEvent):
            self.handle_project_engaged(event.project, event.minutes)

    @abstractmethod
    def handle_project_engaged(self, project: ProjectNote, minutes: int):
        pass


class SchedulingResetSubscriber(EventSubscriber):
    def handle_event(self, event: Event):
        super().handle_event(event)
        if isinstance(event, SchedulingReset):
            self.handle_scheduling_reset()

    @abstractmethod
    def handle_scheduling_reset(self, project: ProjectNote, minutes: int):
        pass


# todo: maybe separate everything to files


class EventBus:
    _subscribers: list[tuple[EventSubscriber, Type[Event]]]

    def __init__(self):
        self._subscribers = []

    # todo: maybe remove parts about specific events out of EventBus class
    def fire_project_engaged(self, project: ProjectNote, minutes: int):
        logging.info(f"Firing event 'project engaged' for project {project.name}")
        event = ProjectEngagedEvent(project=project, minutes=minutes)
        self.fire_event(event)

    def fire_scheduling_reset(self):
        logging.info("Firing event 'scheduling reset'")
        event = SchedulingReset()
        self.fire_event(event)

    def fire_done_meta_todo(self, todo: Todo, project: Optional[ProjectNote] = None):
        assert todo.done

        # todo: refactor switch
        if isinstance(todo, EngageShortTodo):
            self.fire_project_engaged(project=project, minutes=EngageShortTodo.minutes)
        if isinstance(todo, EngageMediumTodo):
            self.fire_project_engaged(project=project, minutes=EngageMediumTodo.minutes)
        if isinstance(todo, EngageLongTodo):
            self.fire_project_engaged(project=project, minutes=EngageLongTodo.minutes)
        if isinstance(todo, SchedulingResetTodo):
            self.fire_scheduling_reset()

    def fire_event(self, event):
        for subscriber, event_type in self._subscribers:
            if isinstance(event, event_type):
                subscriber.handle_event(event)

    def subscribe(self, event_type: Type[Event], subscriber: EventSubscriber):
        logging.debug(f"{subscriber} subscribed to '{event_type}' events")
        self._subscribers.append((subscriber, event_type))
