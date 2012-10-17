#!/bin/bash

. %(virtualenv_dir)s/bin/activate

cd %(manage_py_dir)s
# ulimit -v 1000000
exec %(virtualenv_dir)s/bin/python %(manage_py_dir)s/manage.py celery worker -B -E -l DEBUG