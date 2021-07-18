
from enum import Enum


class SparkJobs(Enum):
    raw2processed = "raw2processed.py"

    @classmethod
    def names(cls):
        return list(map(lambda c: c.name, cls))
