from typing import Dict

from data_broker import DataBroker
from data_models import *
from site_broker import SiteBroker
from site_manager import SiteManager


class TransactionManager:
    def __init__(self):
        self.data_broker = DataBroker()
        self.site_broker = SiteBroker()
        self.transaction_map: Dict[str, Transaction] = {}  # t_id -> transaction information
        self.conflict_graph: Dict[str, Set[str]] = {}  # transaction_id -> set of conflicting transaction_ids
        self.site_managers: Dict[int, SiteManager] = {
            i: SiteManager(i) for i in range(1, 11)
        }

    def begin(self, t_id: str, timestamp: int):
        self.transaction_map[t_id] = Transaction(
            id=t_id,
            start_time=timestamp,
            status=TransactionStatus.ACTIVE,
            writes=set(),
            reads=set()
        )
        self.conflict_graph[t_id] = set()
        print(f"Transaction {t_id} begins")

    def read(self, t_id: str, data_id: str) -> bool:
        if self._is_invalid(t_id):
            return False

        # Get available sites for this data item
        available_sites = self.site_broker.get_available_sites(data_id, self.data_broker)

        # TODO: If no sites are available, wait - how do we handle this??
        # TODO: Maybe have a list of pending reads that gets scanned each time a site recovers
        if not available_sites:
            print(f"No available sites for data item {data_id}")
            return False

        transaction = self.transaction_map[t_id]

        # Try to read from any available site
        for site_id in available_sites:
            value = self.site_managers[site_id].read(t_id, data_id)
            # TODO: should we update transaction reads regardless of available sites?
            # In that case, we need to move the next few lines of code to the top of self.read()
            if value is not None:
                transaction.reads.add(data_id)
                return True

        return False

    def write(self, t_id: str, data_id: str, value: int, timestamp: int) -> bool:
        if self._is_invalid(t_id):
            return False

        # Get available sites for this data item
        available_sites = self.site_broker.get_available_sites(data_id, self.data_broker)

        # TODO: what should be done if no sites are available for write ?
        if not available_sites:
            print(f"No available sites for data item {data_id}")
            return False

        # Write to all available sites
        success = False
        for site_id in available_sites:
            if self.site_managers[site_id].write(t_id, data_id, value, timestamp):
                success = True

        if success:
            transaction = self.transaction_map[t_id]
            transaction.writes.add(data_id)
            # Update conflict graph
            for other_t_id, other_transaction in self.transaction_map.items():
                if other_t_id != t_id and other_transaction.status == TransactionStatus.ACTIVE:
                    if data_id in other_transaction.reads:
                        self.conflict_graph[t_id].add(other_t_id)

        return success

    def end(self, t_id: str, timestamp: int):
        if self._is_invalid(t_id):
            return

        transaction = self.transaction_map[t_id]

        # TODO: Incorrect implementation of Serializable Snapshot Isolation
        # Check for conflicts using Serializable Snapshot Isolation
        should_abort = False
        for other_t_id, other_transaction in self.transaction_map.items():
            if other_t_id != t_id and other_transaction.status == TransactionStatus.COMMITTED:
                # Check for write-write conflicts
                if transaction.writes & other_transaction.writes:
                    should_abort = True
                    break

        # Check for cycle in conflict graph
        if not should_abort:
            # Simple cycle detection (this could be more sophisticated)
            visited = set()

            def has_cycle(node: int, path: Set[int]) -> bool:
                if node in path:
                    return True
                if node in visited:
                    return False

                visited.add(node)
                path.add(node)

                for next_node in self.conflict_graph[node]:
                    if has_cycle(next_node, path):
                        return True

                path.remove(node)
                return False

            should_abort = has_cycle(t_id, set())

        if should_abort:
            transaction.status = TransactionStatus.ABORTED
            print(f"Transaction {t_id} aborts")
        else:
            transaction.status = TransactionStatus.COMMITTED
            # Persist changes to all sites
            for site_id in self.site_managers.keys():
                if self.site_broker.is_site_up(site_id):
                    self.site_managers[site_id].persist(t_id, timestamp)
            print(f"Transaction {t_id} commits")

        # TODO: After the transaction commits, we should remove it from the adjacency list

    def fail(self, site_id: int, timestamp: int):
        self.site_broker.site_status[site_id].status = False
        self.site_broker.site_status[site_id].last_failure_time = timestamp
        self.site_broker.site_status[site_id].site_log.append((False, timestamp))
        self.site_managers[site_id].fail()
        print(f"Site {site_id} fails")

    def recover(self, site_id: int, timestamp: int):
        self.site_broker.site_status[site_id].status = True
        self.site_broker.site_status[site_id].site_log.append((True, timestamp))
        self.site_managers[site_id].recover()
        # TODO: check which pending reads can be completed
        print(f"Site {site_id} recovers")

    def dump(self):
        for site_id in self.site_managers.keys():
            if self.site_broker.is_site_up(site_id):
                self.site_managers[site_id].dump()

    def _is_invalid(self, t_id: str):
        if t_id not in self.transaction_map:
            print(f"Error: Transaction {t_id} does not exist")
            return True

        transaction = self.transaction_map[t_id]
        if transaction.status != TransactionStatus.ACTIVE:
            print(f"Error: Transaction {t_id} is not active")
            return True

        return False
