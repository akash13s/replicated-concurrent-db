from typing import Optional, Any

from data_models import DataLog


def extract_num(key: str) -> int:
    return int(key[1:])


class Site:

    def __init__(self, site_id: int):

        self.site_id = site_id

        # main data storage for the committed values -> Dict[str: list[DataLog]]
        # Format: data_id -> list[DataLog]
        self.data_store = {}

        # temporary storage for any write instruction -> Dict[str: list[DataLog]]
        # Format: data_id -> history of data_values
        self.data_history = {}

        self.initialize_site_data()

    def initialize_site_data(self):
        # initialize data items with their corresponding initial values
        # even indexed items are replicated at all sites
        # odd indexed items are replicated only at site (i % 10) + 1
        for i in range(1, 21):
            data_id = f"x{i}"
            if i % 2 == 0 or (i % 10) + 1 == self.site_id:
                self.data_store[data_id] = []
                self.data_store[data_id].append(DataLog(
                    value=10 * i,
                    timestamp=-1,
                    transaction_id="T_init",
                    committed=True
                ))

                self.data_history[data_id] = []

    def get_value_using_snapshot_isolation(self, data_id: str, timestamp: int) -> Any:
        committed_writes = reversed(self.data_store[data_id])
        for write in committed_writes:
            if write.timestamp < timestamp:
                return write.value

        return None

    def read(self, data_id: str, timestamp: int) -> Optional[int]:
        # Data is read from the committed data_store
        if data_id in self.data_store:
            value = self.get_value_using_snapshot_isolation(data_id, timestamp)
            return value

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
        return True

    def persist(self, t_id: str, data_id: str, timestamp: int):
        data_history = self.data_history[data_id]
        valid_logs = [log for log in reversed(data_history) if log.transaction_id == t_id]
        if not valid_logs:
            return

        last_log = valid_logs[0]
        commit_value = last_log.value

        self.data_store[data_id].append(DataLog(
            value=commit_value,
            timestamp=timestamp,
            transaction_id=t_id,
            committed=True
        ))

    def dump(self) -> str:
        status = f"site {self.site_id} - "
        ordered_data = sorted(self.data_store.keys(), key=extract_num)
        data_status = [f"{data_id}: {self.data_store[data_id][-1].value}" for data_id in ordered_data]
        status += ", ".join(data_status)
        return status
