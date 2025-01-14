#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

DIST_FOLDER="dist"

echo "running nbdev_clean"
nbdev_clean
echo "running nbdev_export"
nbdev_export
echo "running nbdev_readme and nbdev_docs"
nbdev_readme
nbdev_docs

# Remove old .tar.gz files
echo "Cleaning up old tar.gz files in $DIST_FOLDER..."
rm -f $DIST_FOLDER/*.tar.gz
echo "Old files removed."

# Build the source distribution
echo "Creating a new source distribution..."
python setup.py sdist
echo "Source distribution created."

# Get the name of the newly created tar.gz file
LATEST_FILE=$(ls -t $DIST_FOLDER/*.tar.gz | head -n 1)

if [ -z "$LATEST_FILE" ]; then
    echo "Error: No tar.gz file was created."
    exit 1
fi

echo "New package built: $LATEST_FILE"
