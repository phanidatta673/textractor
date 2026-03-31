#!/bin/bash
set -e

# Build script for Python Lambdas
# Get the absolute path of the backend directory
BACKEND_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if ! command -v pip3 &> /dev/null
then
    echo "pip3 could not be found, please install python3-pip"
    exit 1
fi

LAMBDAS=("get-presigned-url" "start-extraction" "extraction-processor" "get-status" "github-issue-handler")

for LAMBDA in "${LAMBDAS[@]}"
do
    echo "Building $LAMBDA..."
    LAMBDA_DIR="$BACKEND_DIR/lambdas/$LAMBDA"
    DIST_DIR="$LAMBDA_DIR/dist"
    
    # Clean up and recreate dist directory
    rm -rf "$DIST_DIR"
    mkdir -p "$DIST_DIR"

    # Copy index.py to dist
    if [ -f "$LAMBDA_DIR/index.py" ]; then
        cp "$LAMBDA_DIR/index.py" "$DIST_DIR/"
    else
        echo "Error: $LAMBDA_DIR/index.py not found!"
        exit 1
    fi

    # Install dependencies if requirements.txt exists and is not empty
    if [ -s "$LAMBDA_DIR/requirements.txt" ]; then
        echo "Installing dependencies for $LAMBDA..."
        pip3 install -r "$LAMBDA_DIR/requirements.txt" --target "$DIST_DIR/"
    fi
done

echo "Build complete."
