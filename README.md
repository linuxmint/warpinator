## How to build and install
________
#### Mint 20, LMDE 4:
```
sudo apt-get install warpinator
```

#### Ubuntu 20.04, related:
```
# Install build dependencies listed below, note minimum versions:
sudo apt-get install python3-grpc-tools python3-grpcio

# Clone this repo:
git clone https://github.com/linuxmint/warpinator.git

# Enter the folder, specify version:
cd warpinator

# Check out appropriate branch (1.0.6 is current official, master is development)
git checkout 1.0.6

# Try to build. If this fails, it's probably due to missing dependencies.
# Take note of these packages, install them using apt-get:
dpkg-buildpackage --no-sign

# Once that succeeds, install:
cd ..
sudo dpkg -i *warp*.deb

# If this fails, make note of missing runtime dependencies (check list below),
# install them, repeat previous command (apt-get install -f may also work).
```
##### Note for Mint 19.x and Ubuntu Bionic (18.04) users:

Add this PPA to satisfy dependencies, then you can follow steps above:
<https://launchpad.net/~clementlefebvre/+archive/ubuntu/grpc?field.series_filter=bionic>

#### Otherwise (and this is valid anywhere if you want to avoid packaging):
```
meson builddir --prefix=/usr  (This is typical).
ninja -C builddir
sudo ninja -C builddir install
```
_____
##### build deps (ref: debian/control)
- meson (>= 0.45.0)
- python3-grpc-tools (>= 1.14.0)
- python3-protobuf (>= 3.6.1)
- python3-packaging
- gobject-introspection

##### runtime deps
- gir1.2-glib-2.0
- gir1.2-gtk-3.0 (>= 3.20.0)
- gir1.2-xapp-1.0 (>= 1.6.0)
- python3
- python3-gi
- python3-setproctitle
- python3-xapp (>= 1.6.0)
- python3-zeroconf
- python3-grpcio (>= 1.16.0)
- python3-cryptography
- python3-nacl

##### You can get grpcio and grpc-tools from pip3 also:
```
pip3 install grpcio grpcio-tools
```
