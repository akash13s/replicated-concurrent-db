from typing import Optional

from data_models import DataLog


class Site:

    def __init__(self, site_id: int):

        self.site_id = site_id

        # main data storage for the latest committed values -> Dict[str: int]
        # Format: data_id -> data_value
        self.data_store = {}

        # temporary storage for any write instruction -> Dict[str: list[DataLog]]
        # Format: data_id -> history of data_values
        self.data_history = {}

        # initialize data items with their corresponding initial values
        # even indexed items are replicated at all sites
        # odd indexed items are replicated only at site (i % 10) + 1
        for i in range(1, 21):
            data_id = f"x{i}"
            if i % 2 == 0 or (i % 10) + 1 == site_id:
                self.data_store[data_id] = 10 * i
                self.data_history[data_id] = []

    # TODO: How to read ?? Always read the Snapshot of DB at Ti start?
    # OR Read the latest uncommited value?
    def read(self, t_id: str, data_id: str) -> Optional[int]:
        """Reads the most recent value for a data item, considering uncommitted writes by the transaction."""

        # check if the transaction has an entry in the data_history
        # return the most recent uncommitted value written by this transaction
        if data_id in self.data_history:
            uncommitted_writes = [entry for entry in self.data_history[data_id] if entry.transaction_id == t_id]
            if uncommitted_writes:
                value = uncommitted_writes[-1].value
                print(f"Transaction {t_id} reads {value} from uncommitted {data_id} at site {self.site_id}")
                return value

        # if no uncommitted value for this transaction is found,
        # Data is read from the committed data_store
        if data_id in self.data_store:
            value = self.data_store[data_id]
            print(f"Transaction {t_id} reads {value} from committed {data_id} at site {self.site_id}")
            return value

        print(f"Data {data_id} not found at site {self.site_id}")
        return None

    def write(self, t_id: str, data_id: str, value: int, timestamp: int) -> bool:
        if data_id not in self.data_store:
            return False

        self.data_history[data_id].append(DataLog(
            value=value,
            timestamp=timestamp,
            transaction_id=t_id,
            committed=False
        ))

        # TODO: remove print statement
        print(f"Transaction {t_id} writes {value} to {data_id} at site {self.site_id}")
        return True

    def persist(self, t_id: str, timestamp: int):
        for data_id in self.data_history:
            valid_logs = [log for log in reversed(self.data_history[data_id]) if log.transaction_id == t_id]
            if not valid_logs:
                continue
            last_log = valid_logs[0]
            committed_value = last_log.value
            self.data_store[data_id] = committed_value
            self.data_history[data_id].append(DataLog(
                value=committed_value,
                timestamp=timestamp,
                transaction_id=t_id,
                committed=True
            ))

    def dump(self):
        status = f"site {self.site_id} - "
        ordered_data = sorted(self.data_store.keys(), key=self._extract_num)
        data_status = [f"{data_id}: {self.data_store[data_id]}" for data_id in ordered_data]
        status += ", ".join(data_status)
        print(status)

    # TODO: remove fail() from Site Manager ?
    # Does not perform any action so far
    def fail(self):
        return

    # TODO: remove recover() from Site Manager ?
    # Does not perform any action so far
    def recover(self):
        return

    def _extract_num(self, key: str) -> int:
        return int(key[1:])
