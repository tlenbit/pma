import logging
from dataclasses import dataclass
from time import sleep
from typing import Any

import requests
from config import get_config
from event_bus import EventBus
from models import Vault
from modules import ExternalTodosSyncJob
from modules.notes_consistency import NotesConsistencyJob
from modules.projects_engagement import MetaTodosProcessingJob
from modules.scheduling import Scheduler
from modules.sync_todos.todoist import TodoistApp

FORMAT = "%(asctime)s %(levelname)s %(message)s"
logging.basicConfig(format=FORMAT)
logging.getLogger().setLevel(get_config().logging_level)
logging.getLogger("httpx").setLevel(logging.WARNING)


def run_job(job) -> None:
    logging.info(f"Running {job.__class__.__name__}")
    job.run()


@dataclass
class SaveToDiskJob:
    vault: Vault

    def run(self):
        self.vault.write_to_fs()


class VaultRecentlyUpdatedError(Exception):
    ...


@dataclass
class DebounceJob:
    vault: Vault

    def run(self):
        if self.vault.updated_recently:
            raise VaultRecentlyUpdatedError()


@dataclass
class SchedulingJob:
    vault: Vault
    scheduler: Scheduler

    def run(self):
        self.scheduler.output_to_schedule_note()


# todo: fix type
def init_jobs() -> list[Any]:
    config = get_config()

    todoist_app = TodoistApp()

    vault = Vault.read_from_fs(config=config)
    event_bus = EventBus()
    debouncing = DebounceJob(vault=vault)
    scheduler = Scheduler(
        schedule_note=vault["projects/⚙️ Scheduling"],
        projects=vault.get_projects(),
        event_bus=event_bus,
    )
    todos_syncing = ExternalTodosSyncJob(
        vault=vault,
        external_todo_app=todoist_app,
        config=config,
        event_bus=event_bus,
    )
    notes_consistency = NotesConsistencyJob(
        vault=vault,
        config=config,
    )
    projects_engagement = MetaTodosProcessingJob(
        vault=vault,
        event_bus=event_bus,
    )
    scheduling = SchedulingJob(
        vault=vault,
        scheduler=scheduler,
    )
    save_to_disk = SaveToDiskJob(vault)

    return [
        # debouncing,
        todos_syncing,
        projects_engagement,
        scheduling,
        notes_consistency,
        save_to_disk,
    ]


def main() -> None:
    while True:
        logging.info("...")

        try:
            jobs = init_jobs()

            for job in jobs:
                run_job(job)
        except (requests.exceptions.ConnectionError, requests.exceptions.HTTPError):
            logging.error("Network error, aborting...")
        except VaultRecentlyUpdatedError:
            logging.error("Vault has been updated recently, aborting...")

        sleep(60)


if __name__ == "__main__":
    main()
