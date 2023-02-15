#!/usr/bin/python3

import os
import sys
import subprocess
import re

if os.getuid() != 0:
    print("Need to be root")
    sys.exit(1)

# Match n in '[n] 42001/tcp                  ALLOW IN    Anywhere                   # WARPINATOR'
num_finder = re.compile(r'(?!\[\s+)\d+(?=\])')

try:
    main_port = sys.argv[1]
    auth_port = sys.argv[2]
except IndexError:
    print("use: ufw-modify <main port number to open> <auth port to open>")
    exit(1)

# Remove any old rule for Warpinator
numbered = subprocess.check_output(["ufw", "status", "numbered"]).decode("utf-8")

found = []

for line in numbered.split("\n"):
    if any(label in line for label in ("WARPINATOR_MAIN", "WARPINATOR_AUTH", "WARPINATOR")):
        try:
            num = num_finder.search(line)[0]
            found.append(num)
        except TypeError:
            pass

if len(found) > 0:
    found.reverse()
    print("Found %d existing rules" % len(found))

    for number in found:
        subprocess.run(["ufw", "--force", "delete", number])

# Backwards compatibility requires we keep doing both udp and tcp on the main port.
subprocess.run(["ufw", "allow", "from", "any", "to", "any", "port", main_port, "comment", "WARPINATOR_MAIN"])
subprocess.run(["ufw", "allow", "proto", "tcp", "from", "any", "to", "any", "port", auth_port, "comment", "WARPINATOR_AUTH"])
# Zeroconf has discovery issues when two flatpaks are attempting to connect. Explicitly opening udp port 5353
# resolves this. It's already open using the default ufw profile, as it is required for network device discovery
# (for things like printers).
#
# This script is only available to non-flatpak versions, but this way it'll already be set if the user decides to switch to
# the flatpak.
subprocess.run(["ufw", "allow", "proto", "udp", "from", "any", "to", "any", "port", "5353", "comment", "WARPINATOR_FLATPAK_ZC_FIX"])
exit(0)