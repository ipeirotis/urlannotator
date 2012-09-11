#!/bin/bash

. %(virtualenv_dir)s/bin/activate

exec supervisorctl -c "%(supervisor_dir)s/config/supervisor-rabbitmq.conf"
