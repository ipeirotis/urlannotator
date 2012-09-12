#!/bin/bash

gu=`git config user.name`
ESCAPES="TODO|XXX|FIXME"
for f in `find urlannotator/ -type f | grep "\.py$" | grep -v "/migrations/"`; do 
    r=`git blame $f | grep "$gu" | egrep "$ESCAPES"`
    if [ -n "$r" ]; then
        echo "In file $f :"
        echo -e "$r"
        echo
    fi
done
