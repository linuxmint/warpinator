#!/usr/bin/python3

#Parts:
# Copyright 2015 gRPC authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Runs protoc with the gRPC plugin to generate messages and gRPC stubs."""



import sys
import os
import tempfile

relative_path = os.path.join("libexec", "warpinator", "zeroconf_")
install_dir = os.path.join(os.environ['MESON_INSTALL_DESTDIR_PREFIX'], relative_path)

version = "0.29.0"
gh_url = "https://raw.githubusercontent.com/jstasiak/python-zeroconf"
full_url = os.path.join(gh_url, version, "zeroconf", "__init__.py")

if os.environ.get('DESTDIR'):
    print("\n\nDownloading and packaging zeroconf %s in %s" % (version, relative_path))
else:
    print("\n\nDownloading and installing zeroconf %s in %s" % (version, install_dir))

print("Package url: %s" % full_url)
with tempfile.NamedTemporaryFile() as f:
    if (os.system('curl -sS %s > %s' % (full_url, f.name))) == 0:
        os.makedirs(install_dir, exist_ok=True)
        os.system("cp %s %s/__init__.py" % (f.name, install_dir))
        os.system('touch %s/py.typed' % install_dir)
    else:
        print("\nCould not download zeroconf. If you wish skip this and install it via package manager, "
              "set the 'use-zeroconf' build option to false. See the README.\n")
        exit(1)

exit(0)

