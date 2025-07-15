#!/usr/bin/python3

import sys
import os
import subprocess

srcdir = sys.argv[1]
outdir = sys.argv[2]

print("Building grpc s:%s, t:%s" % (srcdir, outdir), flush=True)

# Modifications to grpc tarball (1.73.1) #################################################################

try:
    os.chdir(srcdir)
    os.environ["GRPC_PYTHON_BUILD_EXT_COMPILER_JOBS"] = "2"
    subprocess.run(["python3", "setup.py", "build"])
    subprocess.run("cp -r pyb/lib*/grpc %s" % outdir, shell=True)
except Exception as e:
    print(e)
    sys.exit(1)

sys.exit(0)