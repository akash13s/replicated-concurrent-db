import argparse
import os
import sys
from driver import Driver, read_file

if __name__ == "__main__":
    """
       Tests a single input file and prints the output to the console
    """

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("input_file", help="Path to the input file")
    arg_parser.add_argument("-v", "--verbose", action="store_true", help="increase output verbosity")
    args = arg_parser.parse_args()

    file_path = args.input_file
    allow_verbose = args.verbose

    if not os.path.exists(file_path):
        print(f"File does not exist: {file_path}")
        sys.exit(1)

    commands = read_file(file_path)

    driver = Driver(allow_verbose)

    for idx, command in enumerate(commands):
        driver.process_line(command, idx + 1)