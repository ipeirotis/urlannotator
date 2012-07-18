#!/bin/bash

. %(virtualenv_dir)s/bin/activate

rabbitmqctl -n %(project_name)s status
if [ $? != 0] then
    exec rabbitmq_server
else
    rabbitmqctl -n %(project_name)s stop_app
    rabbitmqctl -n %(project_name)s reset
    exec rabbitmqctl -n %(project_name)s start_app
fi
