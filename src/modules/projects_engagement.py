from dataclasses import dataclass
from typing import Optional

from event_bus import EventBus
from models import MetaTodo, Vault


def process_done_meta_todos(vault: Vault, event_bus: Optional[EventBus]) -> None:
    for project in vault.get_projects():
        for todo in project.get_todos():
            if not todo.done:
                continue

            if isinstance(todo, MetaTodo):
                event_bus.fire_done_meta_todo(todo=todo, project=project)
                todo.done = False


@dataclass
class MetaTodosProcessingJob:
    vault: Vault
    event_bus: EventBus

    def run(self):
        process_done_meta_todos(self.vault, self.event_bus)
