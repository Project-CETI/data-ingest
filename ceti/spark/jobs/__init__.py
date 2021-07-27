
from enum import Enum


class SparkJobs(Enum):
    raw2processed = "raw2processed.py"
    helloworld = "helloworld.py"

    @classmethod
    def names(cls):
        return list(map(lambda c: c.name, cls))
