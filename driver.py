from transaction_manager import TransactionManager
from site_manager import SiteManager


class Driver:
    def __init__(self):
        self.sm = SiteManager()
        self.tm = TransactionManager(self.sm)

    def process_line(self, line: str, timestamp: int):
        parts = line.strip().split('(')
        if len(parts) < 2:
            return

        instruction = parts[0].strip()
        args = parts[1].rstrip(')').split(',')
        args = [arg.strip() for arg in args]

        if instruction == 'begin':
            self.tm.begin(args[0], timestamp)
        elif instruction == 'R':
            self.tm.read(args[0], args[1], timestamp)
        elif instruction == 'W':
            self.tm.write(args[0], args[1], int(args[2]), timestamp)
        elif instruction == 'end':
            self.tm.end(args[0], timestamp)
        elif instruction == 'fail':
            self.sm.fail(int(args[0]), timestamp)
        elif instruction == 'recover':
            self.sm.recover(int(args[0]), timestamp)
        elif instruction == 'dump':
            self.sm.dump()


if __name__ == "__main__":
    driver = Driver()
    commands = [
        "begin(T1)",
        "begin(T2)",
        "R(T1,x3)",
        "fail(2)",
        "W(T2,x8,88)",
        "R(T2,x3)",
        "W(T1,x5,91)",
        "end(T2)",
        "recover(2)",
        "end(T1)",
        "dump()"
    ]

    for idx, command in enumerate(commands):
        driver.process_line(command, idx + 1)
