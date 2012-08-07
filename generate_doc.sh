#!/bin/bash

# A simple documentation generation script.
# Relies on sphinx being installed, should be called from within virtualenv.

PROJECT='urlannotator'
export DJANGO_SETTINGS_MODULE=settings.development


export SOURCE_PATH=`pwd`/$PROJECT
export PYTHONPATH=`pwd`
export PYTHONPATH=$PYTHONPATH:$PYTHONPATH/$PROJECT
echo $PYTHONPATH

cd doc

# generate apidoc (automatically for each module)
SPHINX_APIDOC="sphinx-apidoc"

# find all directories in SOURCE_PATH that have name "migrations"
# ...to have them ignored
IGNORED_PATHS=`find $SOURCE_PATH -type d -name migrations`
$SPHINX_APIDOC -o source/api_auto $SOURCE_PATH $IGNORED_PATHS

make html

