#!/bin/bash

. %(virtualenv_dir)s/bin/activate

ulimit -v 1000000
exec %(virtualenv_dir)s/bin/python %(manage_py_dir)s/manage.py celery worker -E -l INFO