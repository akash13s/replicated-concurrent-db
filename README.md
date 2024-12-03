# Replicated Concurrency Control and Recovery

## Project Members

- Akash Kumar Shrivastva (as18464)
- Rishav Roy (rr4577)

## Project Description

This project tries to simulate Replicated Concurrency Control and Recovery in a Database System. The objective is to implement a distributed database system with concurreny control and fault tolerance through concurrent transaction processing, data replication and site failure simulations.

We leverage the following algorithms to achieve the objectives:

1. Serializable Snapshot Isolation Algorithm for Concurrency Control and validation at commit time.
2. Available Copies Algorithm for Fault Tolerance and Recover

## Main Components

1. __Driver__: The distributed database system is built around four key components that work together to ensure reliable and consistent data operations. At the highest level, the Driver serves as the system's main controller and entry point, responsible for processing input commands and coordinating the overall flow of operations. It acts as an orchestrator, interpreting user instructions and directing them to appropriate components.


2. __Transaction Manager__: The Transaction Manager acts as the core processing engine for all transaction-related operations. It maintains complete control over transaction lifecycles, from initiation through to either commitment or abortion. This component implements concurrency control mechanisms through conflict detection and maintains transaction states.


3. __Site Manager__: Working closely with the Transaction Manager, the Site Manager operates as the central coordinator for all distributed operations across multiple database sites. It maintains a comprehensive view of the entire distributed system, tracking the health and availability of each site and managing data distribution. When sites fail or recover, the Site Manager handles the necessary adjustments, including managing pending operations and ensuring data consistency across replicated sites.


4. __Site__: At the lowest level, each Site represents an individual database node that handles actual data storage and operations. Sites implement multi-version concurrency control and manage local read and write operations on their stored data. Each site maintains detailed version histories of its data items and provides snapshot isolation capabilities to ensure consistent reads.

## UML Diagram

The following UML diagram is represents the components and data models used in the application:

![image](./uml_diagram.jpg)


## CLASSES - LOGICAL DESCRIPTION 

```python
class Driver:
    """
    The Driver class serves as the main interface for the transaction processing system.
    It handles file input and delegates instructions to the TransactionManager(begin, read, write, end) and the SiteManager(fail, recover).
    """
    def __init__(self, verbose: bool = False):
        """
        Initialize Driver with optional verbose mode for detailed logging
        
        Args:
            verbose (bool): Enable/disable detailed logging
        """
        self.site_manager: SiteManager
        self.transaction_manager: TransactionManager
        self.verbose: bool = verbose
    
    def read_file(self, file):
        """
        Read and process instructions from an input file
        Each line should contain a transaction operation
        
        Args:
            file: Input file containing transaction instructions
        """
        pass
        
    def process_line(self, line: str, timestamp: int):
        """
        Process a single instruction line from the input
        
        Args:
            line (str): The instruction to process
            timestamp (int): Current line number
        """
        pass
```

```python
class TransactionManager:
    """
    Manages transaction operations, conflict detection, and transaction lifecycle.
    Coordinates with SiteManager for data operations across multiple sites.
    """
    def __init__(self):
        """
        Initialize TransactionManager with required components:
        - site_manager: Reference to the SiteManager instance
        - transaction_map: Maps transaction IDs to Transaction objects
        - conflict_graph: Tracks conflicts between transactions for serializable snapshot isolation
        """
        self.site_manager: SiteManager
        self.transaction_map: Dict[str, Transaction]
        self.conflict_graph: Dict[str, Dict[EdgeType, Set[str]]]

    def begin(self, t_id: str, timestamp: int):
        """
        Start a new transaction
        
        Args:
            t_id (str): Transaction identifier
            timestamp (int): Start timestamp
        """
        pass

    def read(self, t_id: str, data_id: str, timestamp: int, is_pending_read: bool = False) -> int:
        """
        Execute a read operation for a transaction
        
        Args:
            t_id (str): Transaction identifier
            data_id (str): Data item to read
            timestamp (int): Operation timestamp
            is_pending_read (bool): Whether this is a pending read operation
        
        Returns:
            int: Value read from the data item
        """
        pass

    def write(self, t_id: str, data_id: str, value: int, timestamp: int, is_pending: bool = False):
        """
        Execute a write operation for a transaction
        
        Args:
            t_id (str): Transaction identifier
            data_id (str): Data item to write
            value (int): Value to write
            timestamp (int): Operation timestamp
            is_pending (bool): Whether this is a pending write operation
        """
        pass

    def clears_site_failure_check(self, t_id: str) -> bool:
        """
        Check for transaction ABORT based on Available Copies
        
        Args:
            t_id (str): Transaction identifier
        
        Returns:
            bool: True if transaction can proceed
        """
        pass

    def clears_first_committer_rule_check(self, t_id: str) -> bool:
        """
        Check if transaction satisfies the first-committer-wins rule of serializable snapshot isolation
        
        Args:
            t_id (str): Transaction identifier
        
        Returns:
            bool: True if rule is satisfied
        """
        pass

    def abort_transaction(self, abort_type: AbortType, t_id: str, data_id: str, site_id: int):
        """
        Abort a transaction with specified reason
        
        Args:
            abort_type (AbortType): Reason for abortion
            t_id (str): Transaction identifier
            data_id (str): Related data item
            site_id (int): Related site ID
        """
        pass

    def end(self, t_id: str, timestamp: int):
        """
        Performs various checks before committing/aborting a transaction.
        
        Args:
            t_id (str): Transaction identifier
            timestamp (int): End timestamp
        """
        pass

    def exec_pending(self, site_id: int, timestamp: int):
        """
        Execute pending operations(read, write) after site recovery
        
        Args:
            site_id (int): Site identifier
            timestamp (int): Current timestamp
        """
        pass
```

```python

class SiteManager:
    """
    Manages multiple sites in the distributed database system.
    Handles site failures, recovery, and data distribution.
    """
    def __init__(self):
        """
        Initialize SiteManager with:
        - sites: Dictionary mapping site IDs to Site objects
        - site_status: Status information for each site
        - pending_reads/writes: Track pending operations during site failures
        - data_locations: Track which data items are stored at which sites
        """
        self.sites: Dict[int, Site]
        self.site_status: Dict[int, SiteStatus]
        self.pending_reads: Dict[str, Set[Tuple[int, str, int]]]
        self.pending_writes: Dict[str, Set[Tuple[int, str, int]]]
        self.data_locations: Dict[str, List[int]]

    def get_available_sites(self, data_id: str) -> List[int]:
        """
        Get list of available sites containing the specified data item
        
        Args:
            data_id (str): Data item identifier
        
        Returns:
            List[int]: List of available site IDs
        """
        pass

    def get_site(self, site_id: int) -> Site:
        """
        Get a specific site instance
        
        Args:
            site_id (int): Site identifier
        
        Returns:
            Site: Site instance
        """
        pass

    def commit(self, transaction: Transaction, timestamp: int):
        """
        Commit transaction changes to all relevant sites
        
        Args:
            transaction (Transaction): Transaction to commit
            timestamp (int): Commit timestamp
        """
        pass

    def fail(self, site_id: int, timestamp: int):
        """
        Handle site failure
        
        Args:
            site_id (int): Failed site identifier
            timestamp (int): Failure timestamp
        """
        pass

    def recover(self, site_id: int, timestamp: int):
        """
        Handle site recovery
        
        Args:
            site_id (int): Recovered site identifier
            timestamp (int): Recovery timestamp
        """
        pass

    def dump(self):
        """
        Output the current state of all sites for debugging
        """
        pass
```

```python
class Site:
    """
    Represents a single database site in the distributed system.
    Manages data storage, versioning, and operations for its local data items.
    """
    def __init__(self, site_id: int):
        """
        Initialize a database site
        
        Args:
            site_id (int): Unique identifier for the site
            
        Attributes:
            site_id (int): Site identifier
            data_store (Dict[str, List[DataLog]]): Current data versions
            data_history (Dict[str, List[DataLog]]): Historical data versions
        """
        self.site_id: int = site_id
        self.data_store: Dict[str, List[DataLog]] = {}
        self.data_history: Dict[str, List[DataLog]] = {}

    def initialize_site_data(self):
        """
        Initialize the site with its designated data items.
        Each site is responsible for certain data items based on its site_id.
        """
        pass

    def get_value_using_snapshot_isolation(self, data_id: str, timestamp: int) -> int:
        """
        Retrieve data value using snapshot isolation
        
        Args:
            data_id (str): Identifier of the data item
            timestamp (int): Timestamp for snapshot isolation
            
        Returns:
            int: Value of the data item at the specified timestamp
        """
        pass

    def read(self, data_id: str, timestamp: int) -> int:
        """
        Read a data item's value using snapshot isolation by calling self.get_value_using_snapshot_isolation.
        
        Args:
            data_id (str): Identifier of the data item
            timestamp (int): Transaction start time
            
        Returns:
            int: Value of the data item
        """
        pass

    def write(self, t_id: str, data_id: str, value: int, timestamp: int):
        """
        Write a new value to a data item
        
        Args:
            t_id (str): Transaction identifier
            data_id (str): Identifier of the data item
            value (int): Value to write
            timestamp (int): Write timestamp
        """
        pass

    def persist(self, t_id: str, data_id: str, timestamp: int):
        """
        Persist a written value to the data store
        
        Args:
            t_id (str): Transaction identifier
            data_id (str): Identifier of the data item
            timestamp (int): Commit timestamp
        """
        pass

    def dump(self):
        """
        Output the current state of all data items at this site
        Used for debugging and monitoring
        """
        pass
```
