from typing import Dict, List

from Site import Site
from data_models import SiteStatus, DataLog, Transaction


class SiteManager:
    def __init__(self):
        # map of sites
        self.sites: Dict[int, Site] = {
            i: Site(i) for i in range(1, 11)
        }

        # Stores the latest status of each site -> Dict[int, SiteStatus]
        # Format: site_id -> SiteStatus
        self.site_status = {}

        # reads pending for a site -> Dict(site_id, Set(Tuple(t_id, data_id)))
        self.pending_reads = dict()

        # writes pending for a site -> Dict(site_id, Set(Tuple(t_id, data_id, value)))
        self.pending_writes = dict()

        # Initialize all the sites:
        # 1. initial status is up
        # 2. pending reads is empty
        # 3. pending writes is empty
        for site_id in range(1, 11):
            self.site_status[site_id] = SiteStatus(
                status=True,
                last_failure_time=-100,
                site_log=[(True, 0)]
            )
            self.pending_reads[site_id] = set()
            self.pending_writes[site_id] = set()

        # map of data locations: essentially it also knows where every data item is stored
        self.data_locations = {}  # Dict[str, List[int]] mapping data_id to list of site_ids

        # Initialize data locations based on replication rules
        for i in range(1, 21):
            data_id = f"x{i}"
            if i % 2 == 0:  # Even items are replicated at all sites
                self.data_locations[data_id] = list(range(1, 11))
            else:  # Odd items are only at one site
                self.data_locations[data_id] = [(i % 10) + 1]

    def get_available_sites(self, data_id: str) -> List[int]:
        possible_sites = self.data_locations.get(data_id, [])
        return [site_id for site_id in possible_sites if self.is_site_up(site_id)]

    def get_all_site_ids(self, data_id: str) -> List[int]:
        return self.data_locations.get(data_id, [])

    def get_site(self, site_id: int):
        return self.sites.get(site_id)

    def get_all_logs_from_site_for_data_id(self, site_id: int, data_id: str) -> List[DataLog]:
        site = self.sites.get(site_id)
        return site.data_history.get(data_id, [])

    def get_previously_running_sites(self, data_id: str, transaction: Transaction) -> List[int]:
        """
        AVAILABLE COPIES - Read only from previously running sites
        Condition:
        If a site has a committed write to the data before T began,
        and it was continuously up until T began, then it is a previously running site
        """
        t_start_time = transaction.start_time
        all_sites = self.get_all_site_ids(data_id)

        previously_running_sites = list()
        for site_id in all_sites:
            site = self.get_site(site_id)
            valid_commit_logs = [log for log in site.data_store[data_id] if log.timestamp < t_start_time]
            if not valid_commit_logs:
                continue
            last_valid_commit_time = valid_commit_logs[-1].timestamp
            site_logs = self.site_status[site_id].site_log

            # If site was down between t_start_time and last_valid_commit_time,
            # it is a bad site
            down_logs = [log for log in reversed(site_logs) if not log[0]]
            down_ranged_logs = [log for log in down_logs if t_start_time > log[1] > last_valid_commit_time]
            if down_ranged_logs:
                continue

            previously_running_sites.append(site_id)

        return previously_running_sites

    def is_site_up(self, site_id: int) -> bool:
        return self.site_status[site_id].status

    def get_last_fail_time(self, site_id: int):
        return self.site_status[site_id].last_failure_time

    def commit(self, t_id: str, timestamp: int):
        for site_id in self.sites.keys():
            if self.is_site_up(site_id):
                site = self.get_site(site_id)
                site.persist(t_id, timestamp)

    def fail(self, site_id: int, timestamp: int):
        self.site_status[site_id].status = False

        self.site_status[site_id].last_failure_time = timestamp
        self.site_status[site_id].site_log.append((False, timestamp))
        print(f"Site {site_id} fails")

    def recover(self, site_id: int, timestamp: int) -> int:
        self.site_status[site_id].status = True
        self.site_status[site_id].site_log.append((True, timestamp))
        print(f"Site {site_id} recovers")
        return site_id

    def dump(self):
        for site_id in range(1, 11):
            if self.is_site_up(site_id):
                self.get_site(site_id).dump()

    def add_to_pending_reads(self, site_id: int, t_id: str, data_id: str):
        self.pending_reads[site_id].add((t_id, data_id))

    def add_to_pending_writes(self, site_id: int, t_id: str, data_id: str, value: int):
        self.pending_writes[site_id].add((t_id, data_id, value))

    def remove_from_pending_reads(self, site_id: int, t_id: str, data_id: str):
        self.pending_reads[site_id].discard((t_id, data_id))

    def remove_from_pending_writes(self, site_id: int, t_id: str, data_id: str, value: int):
        self.pending_writes[site_id].discard((t_id, data_id, value))
