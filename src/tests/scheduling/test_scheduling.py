from datetime import datetime
from pathlib import Path

from config import Config
from models import Note, ProjectNote, SchedulingNote, Vault
from modules.scheduling import ScheduleItem, Scheduler
from tests.utils import get_mock_config


def test_parsing_schedule_note():
    config = get_mock_config()
    project_note_1 = ProjectNote(
        name="project1",
        text="lalala",
        config=config,
    )
    project_note_2 = ProjectNote(
        name="project2",
        text="lalala",
        config=config,
    )
    project_note_3 = ProjectNote(
        name="project3",
        text="lalala",
        config=config,
    )

    schedule_note = Note.read_from_fs(
        config=config, path=Path("scheduling/fixtures/scheduling_1")
    )

    scheduler = Scheduler(
        schedule_note=schedule_note,
        projects=[project_note_1, project_note_2, project_note_3],
    )

    assert len(scheduler.items) == 3
    assert scheduler.items[0].project == project_note_1
    assert scheduler.items[1].project == project_note_2
    assert scheduler.items[2].project == project_note_3


def test_read_scheduling_note_from_fs():
    config = Config(vault_root_dir=Path("fixtures/vault_28"))
    config.scheduling_note_name = "Scheduling"

    vault = Vault.read_from_fs(config=config)

    assert isinstance(vault["projects/Scheduling"], SchedulingNote)

    assert isinstance(vault.get_projects()[1], SchedulingNote)


# fixing bug (scheduling note with extension was recognised as ProjectNote)
def test_read_scheduling_note_from_fs_with_extension():
    config = Config(vault_root_dir=Path("fixtures/vault_29"))
    config.scheduling_note_name = "Scheduling"

    vault = Vault.read_from_fs(config=config)

    assert isinstance(vault["projects/Scheduling"], SchedulingNote)

    assert isinstance(vault.get_projects()[0], SchedulingNote)


def test_output_schedule_table_to_note():
    config = get_mock_config()
    project_note_1 = ProjectNote(name="project1", text="lalala", config=config)
    project_note_2 = ProjectNote(name="project2", text="lalala", config=config)
    project_note_3 = ProjectNote(name="project3", text="lalala", config=config)
    schedule_note = SchedulingNote(name="Scheduler", text="", config=config)

    scheduler = Scheduler(
        schedule_note=schedule_note,
        projects=[project_note_1, project_note_2, project_note_3],
    )

    item1 = ScheduleItem(
        project=project_note_1,
        last_engaged=datetime(2021, 8, 22),
        engaged=100,
    )
    item2 = ScheduleItem(
        project=project_note_2,
        last_engaged=datetime(2021, 8, 23),
    )
    item3 = ScheduleItem(
        project=project_note_3,
        last_engaged=datetime(2021, 8, 24),
    )

    scheduler.items = [item1, item2, item3]

    scheduler.output_to_schedule_note()

    # to check if everything is ok just recreate Scheduler that will parse this note

    scheduler = Scheduler(
        schedule_note=schedule_note,
        projects=[project_note_1, project_note_2, project_note_3],
    )

    assert len(scheduler.items) == 3
    assert {item.project for item in scheduler.items} == {
        project_note_1,
        project_note_2,
        project_note_3,
    }
    assert {item.last_engaged.day for item in scheduler.items} == {22, 23, 24}


def test_engage_item():
    config = get_mock_config()
    project_note_1 = ProjectNote(name="project1", text="lalala", config=config)
    project_note_2 = ProjectNote(name="project2", text="lalala", config=config)
    project_note_3 = ProjectNote(name="project3", text="lalala", config=config)
    schedule_note = Note(name="Scheduler", text="", config=config)

    scheduler = Scheduler(
        schedule_note=schedule_note,
        projects=[project_note_1, project_note_2, project_note_3],
    )

    item1 = ScheduleItem(
        project=project_note_1,
        last_engaged=datetime(2021, 8, 22),
        engaged=10,
        norm=100,
    )
    item2 = ScheduleItem(
        project=project_note_2,
        last_engaged=datetime(2021, 8, 23),
    )
    item3 = ScheduleItem(
        project=project_note_3,
        last_engaged=datetime(2021, 8, 24),
    )

    scheduler.items = [item1, item2, item3]

    scheduler.engage_project(project_note_1, 20)

    assert item1.engaged == 30
    assert item1.engaged_percent == 30


def test_reset():
    config = get_mock_config()
    project_note_1 = ProjectNote(name="project1", text="lalala", config=config)
    schedule_note = Note(name="Scheduler", text="", config=config)

    scheduler = Scheduler(
        schedule_note=schedule_note,
        projects=[project_note_1],
    )

    item1 = ScheduleItem(
        project=project_note_1,
        last_engaged=datetime(2021, 8, 22),
        engaged=20 + 20,
        engaged_total=100,
    )

    scheduler.items = [item1]

    scheduler.reset()

    scheduler = Scheduler(
        schedule_note=schedule_note,
        projects=[project_note_1],
    )
    assert scheduler.items[0].engaged == 0
    assert scheduler.items[0].engaged_total == 140


def test_ordering():
    config = get_mock_config()
    project_note_1 = ProjectNote(name="project1", text="lalala", config=config)
    project_note_2 = ProjectNote(name="project2", text="lalala", config=config)
    project_note_3 = ProjectNote(name="project3", text="lalala", config=config)
    schedule_note = Note(name="Scheduler", text="", config=config)

    scheduler = Scheduler(
        schedule_note=schedule_note,
        projects=[project_note_1, project_note_2, project_note_3],
    )

    item1 = ScheduleItem(
        project=project_note_1,
        last_engaged=datetime(2021, 8, 22),
        engaged=30,
        norm=100,
    )
    item2 = ScheduleItem(
        project=project_note_2,
        last_engaged=datetime(2021, 8, 23),
        engaged=20,
        norm=100,
    )
    item3 = ScheduleItem(
        project=project_note_3,
        last_engaged=datetime(2021, 8, 24),
        engaged=10,
        norm=100,
    )

    scheduler.items = [item1, item2, item3]

    assert scheduler.items[0] == item3
    assert scheduler.items[1] == item2
    assert scheduler.items[2] == item1


def test_completeness():
    item = ScheduleItem(
        project=ProjectNote(name="project1", text="lalala", config=get_mock_config()),
        last_engaged=datetime(2021, 8, 22),
        engaged=30,
        norm=100,
    )

    assert item.completeness == "■■■□□□□□□□"


def test_completeness_overflow():
    item = ScheduleItem(
        project=ProjectNote(name="project1", text="lalala", config=get_mock_config()),
        last_engaged=datetime(2021, 8, 22),
        engaged=300,
        norm=100,
    )

    assert item.completeness == "■■■■■■■■■■"
