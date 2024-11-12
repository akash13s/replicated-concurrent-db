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
    timestamp: float
    transaction_id: str
    committed: bool


@dataclass
class Transaction:
    id: str
    start_time: float
    status: TransactionStatus
    writes: Set[str]  # Set of data_ids written by this transaction
    reads: Set[str]  # Set of data_ids read by this transaction


@dataclass
class SiteStatus:
    status: bool  # True if site is up, False if down
    last_failure_time: float
    site_log: List[Tuple[float, bool]]
