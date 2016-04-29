#!/bin/bash

PYTHON=/usr/bin/python
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

failed=0
for t in $SCRIPT_DIR/test_*.py; do
    $PYTHON $t
    if [ $? != 0 ]; then
        failed=1
    fi
done

if [ $failed != 0 ]; then
    echo -e "\n[NG] One or more tests failed."
    exit 1
fi

echo -e "\n[OK] All tests have passed."
