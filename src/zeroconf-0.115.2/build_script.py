#!/usr/bin/python3

import sys
import os
import subprocess

srcdir = sys.argv[1]
outdir = sys.argv[2]

print("Building zeroconf s:%s, t:%s" % (srcdir, outdir), flush=True)

try:
    os.chdir(srcdir)
    os.environ["SKIP_CYTHON"] = "1"
    subprocess.run(["python3", "setup.py", "build"])
    subprocess.run("cp -r build/lib/zeroconf %s" % outdir, shell=True)
except Exception as e:
    print(e)
    sys.exit(1)

sys.exit(0)