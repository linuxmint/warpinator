#!/usr/bin/python3

import sys
import json
import subprocess

from gi.repository import Gio, GLib

try:
    reply = Gio.DBusConnection.call_sync(
        Gio.bus_get_sync(Gio.BusType.SESSION, None),
        "org.x.Warpinator",
        "/org/x/Warpinator",
        "org.x.Warpinator",
        "ListRemotes",
        None,
        GLib.VariantType("(aa{sv})"),
        Gio.DBusCallFlags.NO_AUTO_START,
        2000,
        None
    )

    remote_list = reply[0]
    exit(0 if len(remote_list) > 0 else 1)
except GLib.Error as e:
    if e.code != Gio.DBusError.NAME_HAS_NO_OWNER:
        print("warpinator-send-check error %d: %s" % (e.code, e.message), file=sys.stderr)

exit(1)