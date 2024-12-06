#!/bin/bash

# Check for correct number of arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <input_directory> <output_directory>"
    exit 1
fi

INPUT_DIR="$1"
OUTPUT_DIR="$2"
PYTHON_PROGRAM="./test_single_file.py"

mkdir -p "$OUTPUT_DIR"

for input_file in "$INPUT_DIR"/input*; do
	base_name=$(basename "$input_file")
	num=${base_name#input}
	
	output_file="$OUTPUT_DIR/output$num"
	
	echo "Executing input$num"
	python "$PYTHON_PROGRAM" "$input_file" > "$output_file"
done
