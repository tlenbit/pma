from abc import ABC, abstractmethod
from datetime import timedelta

from config import Config


class Job(ABC):
    config: Config
    period: timedelta

    @abstractmethod
    def run(self):
        ...
