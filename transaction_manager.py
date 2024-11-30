from typing import Dict

from data_models import *
from site_manager import SiteManager


class TransactionManager:
    def __init__(self, site_manager: SiteManager, verbose: bool):
        self.site_manager = site_manager
        self.verbose = verbose

        # storage to store transaction information
        self.transaction_map: Dict[str, Transaction] = {}

        # Serialization Graph to identify data dependencies
        # transaction_id -> set of conflicting transaction_ids
        self.conflict_graph: Dict[str, Set[str]] = {}

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
        print(f"{t_id} begins")

    def read(
            self,
            t_id: str,
            data_id: str,
            timestamp: int,
            is_pending_read: bool = False
    ):
        if self.is_invalid(t_id):
            return

        transaction = self.transaction_map[t_id]

        previously_running_sites = self.site_manager.get_previously_running_sites(data_id, transaction)

        # ABORT if it is an impossible read - (Based on Available Copies)
        if not previously_running_sites:
            self.abort_transaction(AbortType.IMPOSSIBLE_READ, t_id, data_id=data_id)
            return

        # Get available sites for this data item
        available_sites = self.site_manager.get_available_sites(data_id)
        read_ready_sites = [site for site in available_sites if site in previously_running_sites]

        if not read_ready_sites:
            print(f"No sites available - Moving (R,{t_id},{data_id}) to pending reads")

            for site_id in previously_running_sites:
                self.site_manager.add_to_pending_reads(site_id, t_id, data_id)
            return

        # Try to read from any of the read ready sites
        success = False
        for site_id in read_ready_sites:
            value = self.site_manager.get_site(site_id).read(data_id, transaction.start_time)

            # TODO: should we update transaction reads regardless of available sites?
            # In that case, we need to move the next few lines of code to the top of self.read()
            if value is not None:
                transaction.reads.add(data_id)
                transaction.sites_accessed.append((site_id, Operations.READ, timestamp))

                if self.verbose:
                    print(f"{t_id} reads {value} from committed {data_id} at site {site_id}")
                print(f"{data_id}: {value}")

                success = True
                break

            if self.verbose and value is None:
                print(f"Data {data_id} not found at site {site_id}")

        # remove the read from pending reads
        if success and is_pending_read:
            for site_id in read_ready_sites:
                self.site_manager.remove_from_pending_reads(site_id, t_id, data_id)

    def write(
            self,
            t_id: str,
            data_id: str,
            value: int,
            timestamp: int,
            is_pending_write: bool = False
    ):
        if self.is_invalid(t_id):
            return

        transaction = self.transaction_map[t_id]

        # Mark the transaction as a read-write transaction.
        # Useful for Available Copies Algorithm.
        if transaction.is_read_only:
            transaction.is_read_only = False

        # Get available sites for this data item
        available_sites = self.site_manager.get_available_sites(data_id)

        if not available_sites:
            print(f"No sites available - Moving (W,{t_id},{data_id},{value}) to pending writes")

            writable_sites = self.site_manager.get_all_site_ids(data_id)
            for site_id in writable_sites:
                self.site_manager.add_to_pending_writes(site_id, t_id, data_id, value)
            return

        # Write to all available sites
        success = False
        success_sites = []
        for site_id in available_sites:
            site = self.site_manager.get_site(site_id)
            if site.write(t_id, data_id, value, timestamp):
                success = True
                success_sites.append(site_id)
                transaction.sites_accessed.append((site_id, Operations.WRITE, timestamp))
                if self.verbose:
                    print(f"{t_id} writes {value} to {data_id} at site {site_id}")

        if success and is_pending_write:
            writable_sites = self.site_manager.get_all_site_ids(data_id)
            for site_id in writable_sites:
                self.site_manager.remove_from_pending_writes(site_id, t_id, data_id, value)

        if success:
            print(f"{t_id} writes {value} to {data_id} at sites {success_sites}")

            transaction = self.transaction_map[t_id]
            transaction.writes.add(data_id)
            # Update conflict graph
            for other_t_id, other_transaction in self.transaction_map.items():
                if (
                        other_t_id != t_id and
                        other_transaction.status == TransactionStatus.ACTIVE and
                        data_id in other_transaction.reads
                ):
                    self.conflict_graph[t_id].add(other_t_id)

    def clears_site_failure_check(self, t_id: str) -> bool:
        """
        AVAILABLE COPIES: At Commit time: Transaction T tests whether all servers
        that T accessed (read or write) have been up since the first time T accessed them. If not, T aborts.
        (Note: Read-only transactions using multi-version read consistency need not abort in this case.)
        """

        transaction = self.transaction_map[t_id]

        if transaction.is_read_only:
            if self.verbose:
                print(f"{t_id} is in Read-only mode - no need to check for site failures")
            return True

        sites_accessed = transaction.sites_accessed

        if self.verbose:
            print(f"Sites accessed by {t_id}: {sites_accessed}")

        failure = False
        site_id_failed = None

        for site_id, operation, ts in sites_accessed:
            if self.site_manager.get_last_fail_time(site_id) > ts:
                failure = True
                site_id_failed = site_id
                break

        # if there is a site that failed, then ABORT
        if failure:
            self.abort_transaction(AbortType.SITE_FAILURE, t_id, site_id=site_id_failed)
            return False

        if self.verbose:
            print(f"All sites accessed by {t_id} have been up since the first time it accessed them")

        return True

    def clears_first_committer_rule_check(self, t_id: str) -> bool:
        """
        :param t_id:
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

        if transaction.is_read_only:
            if self.verbose:
                print(f"{t_id} is in Read-only mode - no need to check for first committer rule")
            return True

        if self.verbose:
            print(f"Data items that {t_id} wants to commit: {transaction.writes}")

        for data_id in transaction.writes:

            site_ids = self.site_manager.get_available_sites(data_id)

            for site_id in site_ids:
                logs = self.site_manager.get_committed_logs_from_site_for_data_id(site_id, data_id)
                for log in logs:
                    if log.committed and log.transaction_id != t_id and log.timestamp > transaction.start_time:
                        self.abort_transaction(AbortType.FIRST_COMMITTER_WRITE, t_id)
                        return False

        if self.verbose:
            print(f"{t_id} passes the 1st committer check")

        return True

    def abort_transaction(self, abort_type: AbortType, t_id: str, data_id: str = None, site_id: int = None):
        if self.verbose:
            if AbortType.IMPOSSIBLE_READ == abort_type:
                print(f"Aborting {t_id} due to impossible read rule on {data_id}")
            if AbortType.FIRST_COMMITTER_WRITE == abort_type:
                print(f"Aborting {t_id} due to first committer rule")
            if AbortType.SITE_FAILURE == abort_type:
                print(f"Aborting {t_id} as site {site_id} failed since it first wrote to it")

        transaction = self.transaction_map[t_id]
        transaction.status = TransactionStatus.ABORTED
        print(f"{t_id} aborts")

    def end(self, t_id: str, timestamp: int):
        if self.is_invalid(t_id):
            return

        # Check for ABORT based on Available Copies
        if not self.clears_site_failure_check(t_id):
            return

        # Check for ABORT based on First committer rule in Snapshot Isolation
        if not self.clears_first_committer_rule_check(t_id):
            return

        # TODO: After the transaction commits, we should remove it from the adjacency list -> will come to this later

        # Commit after above checks
        transaction = self.transaction_map[t_id]
        self.site_manager.commit(transaction, timestamp)
        print(f"{t_id} commits")

    def exec_pending(self, site_id: int, timestamp: int):
        pending_reads = self.site_manager.pending_reads[site_id].copy()
        pending_writes = self.site_manager.pending_writes[site_id].copy()
        for t_id, data_id in pending_reads:
            self.read(t_id, data_id, timestamp, True)
        for t_id, data_id, value in pending_writes:
            self.write(t_id, data_id, value, timestamp, True)

    def is_invalid(self, t_id: str) -> bool:
        if t_id not in self.transaction_map:
            print(f"Error: {t_id} does not exist")
            return True

        transaction = self.transaction_map[t_id]
        if transaction.status != TransactionStatus.ACTIVE:
            print(f"Error: {t_id} is not active")
            return True

        return False
