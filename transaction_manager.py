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
        # Dict of transaction_id -> Dict of EdgeType and a set of conflicting transaction_ids
        self.conflict_graph: Dict[str, Dict[EdgeType, Set[str]]] = {}

    def begin(self, t_id: str, timestamp: int):
        self.transaction_map[t_id] = Transaction(
            id=t_id,
            start_time=timestamp,
            status=TransactionStatus.ACTIVE,
            writes=set(),
            reads=set(),
            sites_accessed=[],
            is_read_only=True,
            commit_time=-1
        )
        self.conflict_graph[t_id] = dict()
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

        # Remove the read from pending reads
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
            if AbortType.CONSECUTIVE_RW_CYCLE == abort_type:
                print(f"Aborting {t_id} due to consecutive read-write cycle in the conflict graph")

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

        # Check for ABORT based on Consecutive RW edges in Serialization Graph
        if not self.update_conflict_graph(t_id, timestamp):
            return

        # Commit after above checks
        transaction = self.transaction_map[t_id]
        self.site_manager.commit(transaction, timestamp)
        transaction.status = TransactionStatus.COMMITTED
        transaction.commit_time = timestamp
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

    def update_conflict_graph(self, t_id: str, timestamp: int) -> bool:
        # In every case below:
        # If committing T' causes a serialization graph cycle
        # having two rw edges in a row, then don't commit T' and
        # remove T' and all associated edges from  the serialization graph,
        # otherwise commit T' and leave
        # it in the serialization graph.
        success = True
        if success:
            success = self.add_ww_edge(t_id)
        if success:
            success = self.add_wr_edge(t_id)
        if success:
            success = self.add_rw_edge(t_id, timestamp)

        if success and self.verbose:
            print(f"{t_id} passes the back-to-back RW edge cycle check")
        return success

    def add_ww_edge(self, t_id: str) -> bool:
        # Upon end(T'), add
        # T --ww--> T' to the serialization graph if T commits before T'
        # begins, and they both write to x

        t_map = self.transaction_map
        txn = self.transaction_map[t_id]

        for other_txn in t_map.values():
            if other_txn.id == t_id:
                continue
            if other_txn.status == TransactionStatus.COMMITTED and other_txn.commit_time < txn.start_time:
                common_writes = [data_id for data_id in other_txn.writes if data_id in txn.writes]
                if common_writes:
                    if EdgeType.WW not in self.conflict_graph[other_txn.id]:
                        self.conflict_graph[other_txn.id][EdgeType.WW] = set()
                    self.conflict_graph[other_txn.id][EdgeType.WW].add(txn.id)

                    # Check for RW cycle
                    if self.has_rw_edge_cycle():
                        self.remove_transaction_from_conflict_graph(t_id)
                        self.abort_transaction(AbortType.CONSECUTIVE_RW_CYCLE, t_id)
                        return False

        return True

    def add_wr_edge(self, t_id: str) -> bool:
        # Upon end(T'), add
        # T --wr--> T' to the serialization graph if T writes to x,
        # commits before T' begins, and T' reads from x

        t_map = self.transaction_map
        txn = self.transaction_map[t_id]

        for other_txn in t_map.values():
            if other_txn.id == t_id:
                continue
            if other_txn.status == TransactionStatus.COMMITTED and other_txn.commit_time < txn.start_time:
                write_reads = [data_id for data_id in other_txn.writes if data_id in txn.reads]
                if write_reads:
                    if EdgeType.WR not in self.conflict_graph[other_txn.id]:
                        self.conflict_graph[other_txn.id][EdgeType.WR] = set()
                    self.conflict_graph[other_txn.id][EdgeType.WR].add(txn.id)

                    # Check for RW cycle
                    if self.has_rw_edge_cycle():
                        self.remove_transaction_from_conflict_graph(t_id)
                        self.abort_transaction(AbortType.CONSECUTIVE_RW_CYCLE, t_id)
                        return False

        return True

    def add_rw_edge(self, t_id: str, t_end_time: int) -> bool:
        # Upon end(T'), add
        # T --rw--> T' to the serialization graph if T reads from x, T' writes to
        # x, and T begins before end(T')

        t_map = self.transaction_map
        txn = self.transaction_map[t_id]

        for other_txn in t_map.values():
            if other_txn.id == t_id:
                continue
            if other_txn.start_time < t_end_time:
                read_writes = [data_id for data_id in other_txn.reads if data_id in txn.writes]
                if read_writes:
                    if EdgeType.RW not in self.conflict_graph[other_txn.id]:
                        self.conflict_graph[other_txn.id][EdgeType.RW] = set()
                    self.conflict_graph[other_txn.id][EdgeType.RW].add(txn.id)

                    # Check for RW cycle
                    if self.has_rw_edge_cycle():
                        self.remove_transaction_from_conflict_graph(t_id)
                        self.abort_transaction(AbortType.CONSECUTIVE_RW_CYCLE, t_id)
                        return False

        return True

    def has_rw_edge_cycle(self) -> bool:
        visited = set()
        current_path = set()
        edge_set = dict()

        def dfs(node: str) -> bool:
            visited.add(node)
            current_path.add(node)

            for edgeType in self.conflict_graph[node]:
                for neighbor in self.conflict_graph[node][edgeType]:
                    edge_set[node] = (edgeType, neighbor)

                    if neighbor in current_path:
                        return True

                    has_cycle = dfs(neighbor)
                    if has_cycle:
                        return True
            return False

        def has_b2b_rw_edges(node: str, is_prev_rw: bool = False) -> bool:
            edge_type, next_node = edge_set[node]
            if edge_type == EdgeType.RW and is_prev_rw:
                return True
            if edge_type == EdgeType.RW:
                check = has_b2b_rw_edges(next_node, True)
                if check:
                    return True

            check = has_b2b_rw_edges(next_node, False)
            if check:
                return True

        for t_id in self.transaction_map.keys():
            if t_id not in visited:
                current_path = set()
                edge_set = dict()
                contains_cycle = dfs(t_id)
                if contains_cycle:
                    if self.verbose:
                        print("Cycle detected in conflict graph")
                        print(edge_set)
                    if has_b2b_rw_edges(t_id, is_prev_rw=False):
                        if self.verbose:
                            print("Cycle has back to back RW edges")
                        return True

        return False

    def remove_transaction_from_conflict_graph(self, t_id: str):
        self.conflict_graph[t_id] = dict()

        for transaction in self.transaction_map.values():
            for edgeType in self.conflict_graph[transaction.id]:
                for neighbor_id in self.conflict_graph[transaction.id][edgeType].copy():
                    if neighbor_id == t_id:
                        self.conflict_graph[transaction.id][edgeType].remove(neighbor_id)
