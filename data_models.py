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
    #   commit_time: int
    # List of sites accessed by this transaction
    # Tuple content - (site_id, operation, timestamp)
    sites_accessed: List[Tuple[int, str, int]]


@dataclass
class SiteStatus:
    status: bool  # True if site is up, False if down
    last_failure_time: int
    site_log: List[Tuple[bool, int]]
