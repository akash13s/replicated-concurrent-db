from dataclasses import dataclass
from enum import Enum
from typing import List, Set, Tuple


# Data Models
class TransactionStatus(Enum):
    ACTIVE = "ACTIVE"
    COMMITTED = "COMMITTED"
    ABORTED = "ABORTED"


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


#   TODO: should we add the following fields ?
#   sites_accessed: List[site_id]
#   commit_time: float or int

@dataclass
class SiteStatus:
    status: bool  # True if site is up, False if down
    last_failure_time: int
    site_log: List[Tuple[bool, int]]
