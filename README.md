#### Ubuntu 20.04, Debian Buster (and LMDE4):

Use dpkg-buildpackage, the python3-grpc-tools and python3-grpcio versions in those repos are fine

#### Mint 19.x and Ubuntu Bionic (18.04) users

Add this PPA to satisfy dependencies (for the time being):

<https://launchpad.net/~clementlefebvre/+archive/ubuntu/grpc?field.series_filter=bionic>

#### Otherwise,
```
meson builddir --prefix=/usr  (I think it needs to be /usr for gobject introspection to work).
ninja -C builddir
sudo ninja -C builddir install
```
_____
##### build deps (ref: debian/control)
- meson (>= 0.45.0)
- python3-grpc-tools (>= 1.14.0)
- python3-protobuf (>= 3.6.1)
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

