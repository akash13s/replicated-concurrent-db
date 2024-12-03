import argparse
import os
import sys
from driver import Driver, read_file


def process_directory(input_dir: str, verbose: bool = False):
    """
    Process all files in the input directory using the Driver class.
    Each file gets its own Driver instance.
    """
    # Ensure the input directory exists
    if not os.path.exists(input_dir):
        print(f"Error: Directory '{input_dir}' does not exist")
        sys.exit(1)

    # Get all files in the directory
    files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]

    # Sort files to ensure consistent processing order
    files.sort()

    # Process each file
    for file_name in files:
        file_path = os.path.join(input_dir, file_name)
        print(f"\n{'=' * 50}")
        print(f"Processing file: {file_name}")
        print(f"{'=' * 50}")

        try:
            # Create new Driver instance for each file
            driver = Driver(verbose)

            # Read commands from file
            commands = read_file(file_path)

            # Process each command with timestamp
            for idx, command in enumerate(commands):
                driver.process_line(command, idx + 1)

            print(f"\nCompleted processing {file_name}")

        except Exception as e:
            print(f"Error processing {file_name}: {str(e)}")
            continue


def main():
    parser = argparse.ArgumentParser(description='Process multiple input files using the Driver class')
    parser.add_argument('input_dir', help='Directory containing input files')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')

    args = parser.parse_args()

    process_directory(args.input_dir, args.verbose)


if __name__ == "__main__":
    main()