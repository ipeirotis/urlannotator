#!/bin/bash

. %(virtualenv_dir)s/bin/activate

rabbitmqctl -n %(project_name)s stop
# if [ $? != 0 ]
# then
export RABBITMQ_NODE_PORT=5673
export RABBITMQ_NODENAME="%(project_name)s"
exec rabbitmq-server
# else
#     rabbitmqctl -n %(project_name)s stop_app
#     rabbitmqctl -n %(project_name)s reset
#     exec rabbitmqctl -n %(project_name)s start_app
# fi
