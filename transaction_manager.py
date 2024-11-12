import time
from data_models import *
from data_broker import DataBroker
from site_broker import SiteBroker
from site_manager import SiteManager


class TransactionManager:
    def __init__(self):
        self.data_broker = DataBroker()
        self.site_broker = SiteBroker()
        self.transaction_map: Dict[str, Transaction] = {}
        self.conflict_graph: Dict[str, Set[str]] = {}  # transaction_id -> set of conflicting transaction_ids
        self.site_managers: Dict[int, SiteManager] = {
            i: SiteManager(i) for i in range(1, 11)
        }

    def begin(self, t_id: str):
        self.transaction_map[t_id] = Transaction(
            id=t_id,
            start_time=time.time(),
            status=TransactionStatus.ACTIVE,
            writes=set(),
            reads=set()
        )
        self.conflict_graph[t_id] = set()
        print(f"Transaction {t_id} begins")

    def read(self, t_id: str, data_id: str) -> bool:
        if t_id not in self.transaction_map:
            print(f"Error: Transaction {t_id} does not exist")
            return False

        transaction = self.transaction_map[t_id]
        if transaction.status != TransactionStatus.ACTIVE:
            print(f"Error: Transaction {t_id} is not active")
            return False

        # Get available sites for this data item
        available_sites = self.site_broker.get_available_sites(data_id, self.data_broker)
        if not available_sites:
            print(f"No available sites for data item {data_id}")
            return False

        # Try to read from any available site
        for site_id in available_sites:
            value = self.site_managers[site_id].read(t_id, data_id)
            if value is not None:
                transaction.reads.add(data_id)
                return True

        return False

    def write(self, t_id: str, data_id: str, value: int) -> bool:
        pass

    def end(self, t_id: str):
        pass

    def fail(self, site_id: int):
        pass

    def recover(self, site_id: int):
        pass

    def dump(self):
        for site_id in range(1, 11):
            if self.site_broker.is_site_up(site_id):
                print(f"Site {site_id}:")
                self.site_managers[site_id].dump()
