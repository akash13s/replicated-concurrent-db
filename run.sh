#!/bin/bash

# Check for correct number of arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <input_directory> <output_directory>"
    exit 1
fi

INPUT_DIR="$1"
OUTPUT_DIR="$2"

PYTHON_PROGRAM="./driver.py"

mkdir -p "$OUTPUT_DIR/verbose"
mkdir -p "$OUTPUT_DIR/concise"


for input_file in "$INPUT_DIR"/input*; do
	base_name=$(basename "$input_file")
	num=${base_name#input}
	
	concise_output_file="$OUTPUT_DIR/concise/output$num"
	verbose_output_file="$OUTPUT_DIR/verbose/output$num"
	
	echo "Executing input$num"
	python "$PYTHON_PROGRAM" "$input_file" > "$concise_output_file"
	python "$PYTHON_PROGRAM" -v "$input_file" > "$verbose_output_file"
done
