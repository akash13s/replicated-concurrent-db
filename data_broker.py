from typing import Dict, List


class DataBroker:
    def __init__(self):
        self.data_locations = {}  # Dict[str, List[int]] mapping data_id to list of site_ids

        # Initialize data locations based on replication rules
        for i in range(1, 21):
            data_id = f"x{i}"
            if i % 2 == 0:  # Even items are replicated at all sites
                self.data_locations[data_id] = list(range(1, 11))
            else:  # Odd items are only at one site
                self.data_locations[data_id] = [(i % 10) + 1]

    def get_sites_for_data(self, data_id: str) -> List[int]:
        return self.data_locations.get(data_id, [])
