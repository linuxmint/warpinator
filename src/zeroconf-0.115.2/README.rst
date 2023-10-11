python-zeroconf
===============

.. image:: https://github.com/python-zeroconf/python-zeroconf/workflows/CI/badge.svg
   :target: https://github.com/python-zeroconf/python-zeroconf?query=workflow%3ACI+branch%3Amaster

.. image:: https://img.shields.io/pypi/v/zeroconf.svg
    :target: https://pypi.python.org/pypi/zeroconf

.. image:: https://codecov.io/gh/python-zeroconf/python-zeroconf/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/python-zeroconf/python-zeroconf

`Documentation <https://python-zeroconf.readthedocs.io/en/latest/>`_.

This is fork of pyzeroconf, Multicast DNS Service Discovery for Python,
originally by Paul Scott-Murphy (https://github.com/paulsm/pyzeroconf),
modified by William McBrine (https://github.com/wmcbrine/pyzeroconf).

The original William McBrine's fork note::

    This fork is used in all of my TiVo-related projects: HME for Python
    (and therefore HME/VLC), Network Remote, Remote Proxy, and pyTivo.
    Before this, I was tracking the changes for zeroconf.py in three
    separate repos. I figured I should have an authoritative source.

    Although I make changes based on my experience with TiVos, I expect that
    they're generally applicable. This version also includes patches found
    on the now-defunct (?) Launchpad repo of pyzeroconf, and elsewhere
    around the net -- not always well-documented, sorry.

Compatible with:

* Bonjour
* Avahi

Compared to some other Zeroconf/Bonjour/Avahi Python packages, python-zeroconf:

* isn't tied to Bonjour or Avahi
* doesn't use D-Bus
* doesn't force you to use particular event loop or Twisted (asyncio is used under the hood but not required)
* is pip-installable
* has PyPI distribution
* has an optional cython extension for performance (pure python is supported as well)

Python compatibility
--------------------

* CPython 3.7+
* PyPy3.7 7.3+

Versioning
----------

This project uses semantic versioning.

Status
------

This project is actively maintained.

Traffic Reduction
-----------------

Before version 0.32, most traffic reduction techniques described in https://datatracker.ietf.org/doc/html/rfc6762#section-7
where not implemented which could lead to excessive network traffic.  It is highly recommended that version 0.32 or later
is used if this is a concern.

IPv6 support
------------

IPv6 support is relatively new and currently limited, specifically:

* `InterfaceChoice.All` is an alias for `InterfaceChoice.Default` on non-POSIX
  systems.
* Dual-stack IPv6 sockets are used, which may not be supported everywhere (some
  BSD variants do not have them).
* Listening on localhost (`::1`) does not work. Help with understanding why is
  appreciated.

How to get python-zeroconf?
===========================

* PyPI page https://pypi.org/project/zeroconf/
* GitHub project https://github.com/python-zeroconf/python-zeroconf

The easiest way to install python-zeroconf is using pip::

    pip install zeroconf



How do I use it?
================

Here's an example of browsing for a service:

.. code-block:: python

    from zeroconf import ServiceBrowser, ServiceListener, Zeroconf


    class MyListener(ServiceListener):

        def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            print(f"Service {name} updated")

        def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            print(f"Service {name} removed")

        def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
            info = zc.get_service_info(type_, name)
            print(f"Service {name} added, service info: {info}")


    zeroconf = Zeroconf()
    listener = MyListener()
    browser = ServiceBrowser(zeroconf, "_http._tcp.local.", listener)
    try:
        input("Press enter to exit...\n\n")
    finally:
        zeroconf.close()

.. note::

    Discovery and service registration use *all* available network interfaces by default.
    If you want to customize that you need to specify ``interfaces`` argument when
    constructing ``Zeroconf`` object (see the code for details).

If you don't know the name of the service you need to browse for, try:

.. code-block:: python

    from zeroconf import ZeroconfServiceTypes
    print('\n'.join(ZeroconfServiceTypes.find()))

See examples directory for more.

Changelog
=========

`Changelog <CHANGELOG.md>`_

License
=======

LGPL, see COPYING file for details.
