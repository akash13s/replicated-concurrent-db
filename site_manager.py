from typing import Dict, List

from Site import Site
from data_models import SiteStatus, DataLog


class SiteManager:
    def __init__(self):
        # map of sites
        self.sites: Dict[int, Site] = {
            i: Site(i) for i in range(1, 11)
        }

        # Stores the latest status of each site -> Dict[int, SiteStatus]
        # Format: site_id -> SiteStatus
        self.site_status = {}

        # Initialize all sites as up
        for site_id in range(1, 11):
            self.site_status[site_id] = SiteStatus(
                status=True,
                last_failure_time=-100,
                site_log=[(True, 0)]
            )

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

    def get_all_logs_from_site_for_data_id(self, site_id: int, data_id: str) -> list[DataLog]:
        site = self.sites.get(site_id)
        return site.data_history.get(data_id, [])

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

    def recover(self, site_id: int, timestamp: int):
        self.site_status[site_id].status = True
        self.site_status[site_id].site_log.append((True, timestamp))
        # TODO: check which pending reads and writes can be completed
        print(f"Site {site_id} recovers")

    def dump(self):
        for site_id in range(1, 11):
            if self.is_site_up(site_id):
                self.get_site(site_id).dump()
