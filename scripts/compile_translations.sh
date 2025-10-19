#!/bin/bash

# script to compile translation files

echo "compiling translation files..."

# compile all .po files to .mo
uv run manage.py compilemessages --ignore=.venv

echo "translation files compiled successfully!"
echo "restart the server for changes to take effectd"