#!/bin/bash
set -e

# Build script for Python Lambdas

if ! command -v pip3 &> /dev/null
then
    echo "pip3 could not be found, please install python3-pip"
    exit
fi

LAMBDAS=("get-presigned-url" "start-extraction" "extraction-processor" "get-status" "github-issue-handler")

for LAMBDA in "${LAMBDAS[@]}"
do
    echo "Building $LAMBDA..."
    cd "lambdas/$LAMBDA"
    
    # Clean up old build artifacts if any
    rm -rf dist
    mkdir -p dist

    # Copy index.py to dist
    cp index.py dist/

    # Install dependencies if requirements.txt is not empty
    if [ -s requirements.txt ]; then
        echo "Installing dependencies for $LAMBDA..."
        pip3 install -r requirements.txt --target dist/
    fi

    cd ../..
done

echo "Build complete."
