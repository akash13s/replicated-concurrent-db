from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum


# Data Models
class TransactionStatus(Enum):
    ACTIVE = "ACTIVE"
    COMMITTED = "COMMITTED"
    ABORTED = "ABORTED"


@dataclass
class DataLog:
    value: int
    timestamp: float    # TODO: change to int ?
    transaction_id: str
    committed: bool


@dataclass
class Transaction:
    id: str
    start_time: float   # TODO: change to int ??
    status: TransactionStatus
    writes: Set[str]  # Set of data_ids written by this transaction
    reads: Set[str]  # Set of data_ids read by this transaction
#     TODO: add the following fields ?
#   sites_accessed: List[site_id]
#   commit_time: float or int

@dataclass
class SiteStatus:
    status: bool  # True if site is up, False if down
    last_failure_time: float    # TODO: change to int ?
    site_log: List[Tuple[float, bool]]
