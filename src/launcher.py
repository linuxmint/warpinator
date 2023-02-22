#!/usr/bin/python3

import sys
import os

try:
    import warpinator
    ret = warpinator.main()

    if "RESTART_WARPINATOR" in os.environ.keys():
        ret = 100
    sys.exit(ret)
except Exception as e:
    print(e)
    sys.exit(1)