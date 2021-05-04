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

relative_path = os.path.join("libexec", "warpinator", "zeroconf_")
install_dir = os.path.join(os.environ['MESON_INSTALL_DESTDIR_PREFIX'], relative_path)
os.makedirs(install_dir, exist_ok=True)

version = "0.29.0"

if os.environ.get('DESTDIR'):
    print("\n\nDownloading and packaging zeroconf %s in %s\n\n" % (version, relative_path))
else:
    print("\n\nDownloading and installing zeroconf %s in %s\n\n" % (version, install_dir))

os.system('curl -s https://raw.githubusercontent.com/jstasiak/python-zeroconf/%s/zeroconf/__init__.py > %s/__init__.py' % (version, install_dir))
os.system('touch %s/py.typed' % install_dir)
