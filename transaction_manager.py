from typing import Dict

from data_models import *
from site_manager import SiteManager


class TransactionManager:
    def __init__(self, site_manager: SiteManager):
        self.site_manager = site_manager
        self.transaction_map: Dict[str, Transaction] = {}  # t_id -> transaction information
        self.conflict_graph: Dict[str, Set[str]] = {}  # transaction_id -> set of conflicting transaction_ids

    def begin(self, t_id: str, timestamp: int):
        self.transaction_map[t_id] = Transaction(
            id=t_id,
            start_time=timestamp,
            status=TransactionStatus.ACTIVE,
            writes=set(),
            reads=set(),
            sites_accessed=[],
            is_read_only=True
        )
        self.conflict_graph[t_id] = set()
        print(f"Transaction {t_id} begins")

    def read(self, t_id: str, data_id: str, timestamp: int) -> bool:
        if self._is_invalid(t_id):
            return False

        # Get available sites for this data item
        available_sites = self.site_manager.get_available_sites(data_id)

        # TODO: If no sites are available, wait - how do we handle this??
        # TODO: Maybe have a list of pending reads that gets scanned each time a site recovers
        if not available_sites:
            print(f"No available sites for data item {data_id}")
            return False

        transaction = self.transaction_map[t_id]

        # Try to read from any available site
        for site_id in available_sites:
            value = self.site_manager.get_site(site_id).read(t_id, data_id, transaction.start_time)
            # TODO: should we update transaction reads regardless of available sites?
            # In that case, we need to move the next few lines of code to the top of self.read()
            if value is not None:
                transaction.reads.add(data_id)
                transaction.sites_accessed.append((site_id, Operations.READ, timestamp))
                return True

        return False

    def write(self, t_id: str, data_id: str, value: int, timestamp: int) -> bool:
        if self._is_invalid(t_id):
            return False

        transaction = self.transaction_map[t_id]

        # Mark the transaction as a read-write transaction. Useful for Available Copies Algorithm.
        if transaction.is_read_only:
            transaction.is_read_only = False

        # Get available sites for this data item
        available_sites = self.site_manager.get_available_sites(data_id)

        # TODO: what should be done if no sites are available for write ?
        if not available_sites:
            print(f"No available sites for data item {data_id}")
            return False

        # Write to all available sites
        success = False
        for site_id in available_sites:
            site = self.site_manager.get_site(site_id)
            if site.write(t_id, data_id, value, timestamp):
                success = True
                transaction.sites_accessed.append((site_id, Operations.WRITE, timestamp))

        if success:
            transaction = self.transaction_map[t_id]
            transaction.writes.add(data_id)
            # Update conflict graph
            for other_t_id, other_transaction in self.transaction_map.items():
                if other_t_id != t_id and other_transaction.status == TransactionStatus.ACTIVE:
                    if data_id in other_transaction.reads:
                        self.conflict_graph[t_id].add(other_t_id)

        return success

    def validate_site_failure(self, t_id: str, timestamp: int):
        """
        AVAILABLE COPIES: At Commit time: For a two phase locked transaction T, T tests whether all servers
        that T accessed (read or write) have been up since the first time T accessed them. If not, T aborts.
        (Note: Read-only transactions using multiversion read consistency need not abort in this case.)
        """

        transaction = self.transaction_map[t_id]

        sites_accessed = transaction.sites_accessed

        print(f"Sites accessed by Transaction {t_id}: {sites_accessed}")

        failure = False
        site_id_failed = None

        for site_id, operation, ts in sites_accessed:
            if self.site_manager.get_last_fail_time(site_id) > ts:
                failure = True
                site_id_failed = site_id
                break

        # if there is a site that failed and if the transaction is not read-only, then ABORT
        if failure and not transaction.is_read_only:
            print(f"Aborting Transaction {t_id} as site {site_id_failed} failed since it first wrote to it")
            return False

        print(f"All sites accessed by Transaction {t_id} have been up since the first time it accessed them")

        return True

    def validate_first_committer_rule(self, t_id: str, timestamp: int):
        """
        :param t_id:
        :param timestamp:
        :return: True if transaction can proceed ahead and False otherwise

        Check for the first committer rule using Snapshot Isolation algorithm

        Writes follow the first committer wins rule:
        Ti will successfully commit only if no other concurrent transaction
        Tk has already committed writes to data items where Ti has written
        versions that it intends to commit.

        That is, if (a) Ti starts at time start(Ti) and tries to commit at end(Ti);
        (b) Tk commits between start(Ti) and  end(Ti);
        and (c) Tk writes some data item x that Ti wants to write, then Ti should abort.
        """

        transaction = self.transaction_map[t_id]

        # check all data items that this transaction T wants to write for every data item x, check the possible sites
        # get the data history of every site for data item x and see if there is some transaction which wrote to x
        # after T began

        print(f"Data items that Transaction {t_id} wants to commit: {transaction.writes}")

        for data_id in transaction.writes:

            site_ids = self.site_manager.get_available_sites(data_id)

            for site_id in site_ids:
                logs = self.site_manager.get_all_logs_from_site_for_data_id(site_id, data_id)

                for log in logs:
                    if log.committed and log.transaction_id != t_id and log.timestamp > transaction.start_time:
                        print(f"Aborting Transaction {t_id} due to first committer rule")
                        return False

        print(f"Transaction {t_id} passes the 1st committer check")

        return True

    def end(self, t_id: str, timestamp: int):
        if self._is_invalid(t_id):
            return

        # Check for ABORT using Available Copies
        if not self.validate_site_failure(t_id, timestamp):
            return

        # First committer rule using Snapshot Isolation
        if not self.validate_first_committer_rule(t_id, timestamp):
            return

        # TODO: After the transaction commits, we should remove it from the adjacency list -> will come to this later

        # Commit after above checks
        self.site_manager.commit(t_id, timestamp)
        print(f"Transaction {t_id} commits")

    def _is_invalid(self, t_id: str):
        if t_id not in self.transaction_map:
            print(f"Error: Transaction {t_id} does not exist")
            return True

        transaction = self.transaction_map[t_id]
        if transaction.status != TransactionStatus.ACTIVE:
            print(f"Error: Transaction {t_id} is not active")
            return True

        return False
