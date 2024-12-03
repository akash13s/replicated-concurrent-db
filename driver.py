"""
Authors:
    - Rishav Roy
    - Akash Kumar Shrivastva
"""


from site_manager import SiteManager
from transaction_manager import TransactionManager


class Driver:
    def __init__(self, verbose: bool):
        self.verbose = verbose
        self.sm = SiteManager(verbose)
        self.tm = TransactionManager(self.sm, verbose)

    def process_line(self, line: str, timestamp: int):
        parts = line.strip().split('(')
        if len(parts) < 2:
            return

        instruction = parts[0].strip()
        params = parts[1].rstrip(')').split(',')
        params = [param.strip() for param in params]

        if instruction == 'begin':
            self.tm.begin(params[0], timestamp)
        elif instruction == 'R':
            self.tm.read(params[0], params[1], timestamp)
        elif instruction == 'W':
            self.tm.write(params[0], params[1], int(params[2]), timestamp)
        elif instruction == 'end':
            self.tm.end(params[0], timestamp)
        elif instruction == 'fail':
            self.sm.fail(int(params[0]), timestamp)
        elif instruction == 'recover':
            self.sm.recover(int(params[0]), timestamp)
            self.tm.exec_pending(int(params[0]), timestamp)
        elif instruction == 'dump':
            self.sm.dump()


def read_file(file):
    commands_list = []
    with open(file, 'r') as file:
        for line in file:
            stripped_line = line.strip()
            if not stripped_line.startswith("//") and stripped_line:
                uncommented_line = stripped_line.split("//")[0]
                commands_list.append(uncommented_line.strip())
    return commands_list
