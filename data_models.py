from dataclasses import dataclass
from enum import Enum
from typing import List, Set, Tuple


# Data Models
class TransactionStatus(Enum):
    ACTIVE = "ACTIVE"
    COMMITTED = "COMMITTED"
    ABORTED = "ABORTED"


class Operations:
    READ = "READ"
    WRITE = "WRITE"


class AbortType(Enum):
    SITE_FAILURE = "SITE_FAILURE"
    IMPOSSIBLE_READ = "IMPOSSIBLE_READ"
    FIRST_COMMITTER_WRITE = "FIRST_COMMITTER_WRITE"
    CONSECUTIVE_RW_CYCLE = "CONSECUTIVE_RW_CYCLE"


class EdgeType(Enum):
    RW = "RW"
    WW = "WW"
    WR = "WR"


@dataclass
class DataLog:
    value: int
    timestamp: int
    transaction_id: str
    committed: bool


@dataclass
class Transaction:
    id: str
    start_time: int
    status: TransactionStatus
    writes: Set[str]  # Set of data_ids written by this transaction
    reads: Set[str]  # Set of data_ids read by this transaction
    is_read_only: bool
    # List of sites accessed by this transaction - Tuple content - (site_id, operation, timestamp)
    sites_accessed: List[Tuple[int, str, int]]
    commit_time: int


@dataclass
class SiteStatus:
    status: bool  # True if site is up, False if down
    last_failure_time: int
    site_log: List[Tuple[bool, int]]
