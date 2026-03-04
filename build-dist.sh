#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

DIST_FOLDER="dist"

# Ensure setuptools is available (needed for pkg_resources)
pip install --upgrade setuptools wheel

# Ensure required environment variables exist (provide safe defaults for build)
export PLAID_CLIENT_ID="${PLAID_CLIENT_ID:-}"
export PLAID_SECRET="${PLAID_SECRET:-}"
export PLAID_ENV="${PLAID_ENV:-sandbox}"
export POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
export POSTGRES_USER="${POSTGRES_USER:-user}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-password}"
export POSTGRES_ENCRYPTION_KEY="${POSTGRES_ENCRYPTION_KEY:-key}"

echo "Building distribution package..."

echo "running nbdev_clean"
nbdev_clean
echo "running nbdev_export"
nbdev_export
echo "running nbdev_readme and nbdev_docs"
nbdev_readme
nbdev_docs

# Ensure dist folder exists before cleaning old artifacts
mkdir -p "$DIST_FOLDER"

# Remove old .tar.gz files
echo "Cleaning up old tar.gz files in $DIST_FOLDER..."
rm -f $DIST_FOLDER/*.tar.gz
rm -f $DIST_FOLDER/*.whl
echo "Old files removed."

# Build both source and wheel distributions
echo "Creating source and wheel distributions..."
python -m build
echo "Distributions created."

# Get the name of the newly created tar.gz file
LATEST_FILE=$(ls -t $DIST_FOLDER/*.tar.gz 2>/dev/null | head -n 1)

if [ -z "$LATEST_FILE" ]; then
    echo "Error: No tar.gz file was created."
    exit 1
fi

echo "New package built: $LATEST_FILE"
echo "Build complete. To install, run: pip install -e . or pip install $LATEST_FILE"
pip install -e .