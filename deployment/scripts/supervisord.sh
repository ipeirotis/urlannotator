#!/bin/bash

. %(virtualenv_dir)s/bin/activate

exec supervisord -c "%(supervisor_dir)s/config/supervisord.conf"
