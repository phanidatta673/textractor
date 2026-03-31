#!/bin/bash
set -e

# Compile all lambdas using esbuild
# This script will install esbuild if not present

if ! command -v npx &> /dev/null
then
    echo "npx could not be found, please install nodejs"
    exit
fi

LAMBDAS=("get-presigned-url" "start-extraction" "extraction-processor" "get-status" "github-issue-handler")

for LAMBDA in "${LAMBDAS[@]}"
do
    echo "Building $LAMBDA..."
    cd "lambdas/$LAMBDA"
    npm install
    npx esbuild index.ts --bundle --minify --platform=node --target=node18 --outfile=index.js
    cd ../..
done
