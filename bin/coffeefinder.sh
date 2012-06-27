#! /bin/bash
# Very simple script for finding CoffeeScript compiler binary regardless on 
# which machine we're running.

COFFEE=`which coffee`

exec $COFFEE $*
