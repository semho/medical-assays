#!/bin/bash

# script to generate translation files for django project

echo "generating translation files..."

# create locale directory if not exists
mkdir -p locale

# generate messages for russian
echo "generating russian translations..."
uv run manage.py makemessages -l ru --ignore=venv --ignore=staticfiles

# generate messages for english
echo "generating english translations..."
uv run manage.py makemessages -l en --ignore=venv --ignore=staticfiles

echo "translation files generated successfully!"
echo "edit locale/ru/LC_MESSAGES/django.po and locale/en/LC_MESSAGES/django.po"
echo "then run: python manage.py compilemessages"