from typing import Dict, List, Optional, Set
from data_models import DataLog


class SiteManager:
    def __init__(self, site_id: int):
        self.site_id = site_id

        # main data storage for committed values -> Dict[str: int] (data_id -> data_value)
        self.data_store = {}

        # temporary storage for uncommitted values -> Dict[str: list[DataLog]] (This will contain only the
        # uncommitted writes) (data_id -> history of data_values)
        self.data_history = {}

        # initialising data items
        # even indexed items are replicated at all sites
        # odd indexed items are replicated only at site (i % 10) + 1
        for i in range(1, 21):
            data_id = f"x{i}"
            if i % 2 == 0 or (i % 10) + 1 == site_id:
                self.data_store[data_id] = 10 * i  # Initial value

    # TODO: How to read ?? Always read the Snapshot of DB at Ti start? OR Read the latest uncommited value?
    def read(self, t_id: str, data_id: str) -> Optional[int]:
        """Reads the most recent value for a data item, considering uncommitted writes by the transaction."""
        # check if the transaction has a temporary write in data_history
        if data_id in self.data_history:
            uncommitted_writes = [entry for entry in self.data_history[data_id] if entry.transaction_id == t_id]
            if uncommitted_writes:
                # return the most recent uncommitted value written by this transaction
                value = uncommitted_writes[-1].value
                print(f"Transaction {t_id} reads {value} from uncommitted {data_id} at site {self.site_id}")
                return value

        # if no uncommitted value for this transaction is found, we then read from the committed data_store
        if data_id in self.data_store:
            value = self.data_store[data_id]
            print(f"Transaction {t_id} reads {value} from committed {data_id} at site {self.site_id}")
            return value

        print(f"Data {data_id} not found at site {self.site_id}")
        return None

    def write(self, t_id: str, data_id: str, value: int) -> bool:
        pass

    def persist(self, t_id: str):
        pass

    def dump(self):
        for data_id, value in sorted(self.data_store.items()):
            print(f"{data_id}: {value}")
        print('*' * 15)

    def fail(self):
        pass

    def recover(self):
        pass
