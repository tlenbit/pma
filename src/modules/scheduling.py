import logging
from datetime import datetime
from typing import Optional

from event_bus import (EventBus, ProjectEngagedEvent, ProjectEngagedSubscriber,
                       SchedulingReset, SchedulingResetSubscriber)
from models import Note, ProjectNote
from pydantic import BaseModel, ConfigDict, computed_field

CELL_WIDTH = 12


class ScheduleItem(BaseModel):
    project: ProjectNote
    last_engaged: datetime
    engaged_total: int = 0
    engaged: int = 0
    norm: int = 60

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @computed_field
    def engaged_percent(self) -> int:
        return int(100 * self.engaged / self.norm) if self.norm else 0

    @computed_field
    def completeness(self) -> str:
        total = 10
        full = self.engaged_percent // total
        if full > 10:
            full = 10
        empty = total - full
        return "■" * full + "□" * empty

    @classmethod
    def model_fields_list(cls):
        result = []
        for field in cls.model_fields.keys():
            result.append(field)
        result.insert(1, "completeness")
        result.append("engaged_percent")
        return result

    def to_line(self) -> str:
        row_values = []
        for field in ScheduleItem.model_fields_list():
            if field == "project":
                value = f"[[{self.project.name}]]"
                cell_width = 25
            elif field == "last_engaged":
                value = datetime.strftime(self.last_engaged, "%d %b")
                cell_width = 5
            else:
                value = str(getattr(self, field))
                cell_width = CELL_WIDTH
            row_values.append(value.rjust(cell_width, " "))

        return "|" + "|".join(row_values) + "|"


# todo: make a separate schedule note type and parse items/output to file there?
class Scheduler(ProjectEngagedSubscriber, SchedulingResetSubscriber):
    _items: list[ScheduleItem]
    projects: dict[str, ProjectNote]
    schedule_note: Note
    event_bus: Optional[EventBus]
    DAY_CAPACITY: float = 4

    def __init__(
        self,
        schedule_note: Note,
        projects: list[ProjectNote],
        event_bus: Optional[EventBus] = None,
    ):
        if event_bus:
            self.event_bus = event_bus
            event_bus.subscribe(event_type=ProjectEngagedEvent, subscriber=self)
            event_bus.subscribe(event_type=SchedulingReset, subscriber=self)
        assert schedule_note
        self.schedule_note = schedule_note
        assert projects
        self.projects = {p.name: p for p in projects}
        self.items = []
        self._parse_items(schedule_note)

    @property
    def items(self) -> list[ScheduleItem]:
        self._items.sort(key=lambda x: x.engaged_percent)
        return self._items

    @items.setter
    def items(self, val: list[ScheduleItem]) -> None:
        self._items = val

    def _parse_items(self, schedule_note: Note) -> None:
        lines = schedule_note.content.split("\n")
        headers = None
        for line in lines:
            row_values = [v.strip() for v in line.split("|") if v.strip()]
            if not headers:
                if len(set(row_values) & set(ScheduleItem.model_fields)) > 0:
                    headers = row_values
            else:
                row = {
                    row_header: row_value
                    for row_header, row_value in zip(headers, row_values)
                }
                try:
                    row["last_engaged"] = datetime.strptime(
                        row["last_engaged"], "%d %b"
                    )
                    project_name = row["project"][2:-2].strip()
                    row["project"] = self.projects.get(project_name)
                    self.items.append(ScheduleItem(**row))
                except Exception as e:
                    logging.info(f"Can not parse schedule item from line '{line}'")
                    logging.info(e)
        if not self.items:
            logging.error("Couldn't find any scheduling items!")

    def output_to_schedule_note(self):
        lines = []
        lines.append("|" + "|".join(ScheduleItem.model_fields_list()) + "|")
        lines.append(
            "|" + "|".join("-" for _ in ScheduleItem.model_fields_list()) + "|"
        )

        for item in self.items:
            lines.append(item.to_line())

        self.schedule_note.text = (
            "\n".join(lines)
            + "\n\n"
            + f"total hours: {sum(i.norm for i in self.items)}"
        )

    def handle_project_engaged(self, project: ProjectNote, minutes: int) -> None:
        self.engage_project(project, minutes)

    def engage_project(self, project: ProjectNote, minutes: int) -> None:
        for item in self.items:
            if item.project is project:
                item.engaged += minutes
                item.last_engaged = datetime.now()
                # breakpoint()
                self.output_to_schedule_note()
                return

        logging.error(
            f"Can not engage on project {project}: corresponding schedule item not found"
        )

    def reset(self) -> None:
        for item in self.items:
            item.engaged_total += item.engaged
            item.engaged = 0
        self.output_to_schedule_note()

    def handle_scheduling_reset(self) -> None:
        self.reset()
