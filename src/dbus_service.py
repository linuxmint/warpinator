#!/usr/bin/python3

import logging

from gi.repository import Gio, GObject, GLib

interface_xml = """
<node>
  <interface name='org.x.Warpinator'>
    <method name='ListRemotes'>
      <!-- ident, display_name, user_name, hostname -->
      <arg type='aa{sv}' name='remotes' direction='out'/>
    </method>
    <method name='SendFiles'>
      <arg type='s' name='remote_uuid' direction='in'/>
      <arg type='as' name='uri_list' direction='in'/>
    </method>
  </interface>
</node>
"""
interface_node_info = Gio.DBusNodeInfo.new_for_xml(interface_xml)

class WarpinatorDBusService(GObject.Object):
    __gsignals__ = {
        'handle-get-live-remotes': (GObject.SignalFlags.RUN_LAST, object, ()),
        'handle-send-files': (GObject.SignalFlags.RUN_LAST, None, (str, object))
    }

    def __init__(self):
        GObject.Object.__init__(self)
        self.reg_id = 0

    def register(self, connection, path):
        self.reg_id = connection.register_object(
            path,
            interface_node_info.interfaces[0],
            self._method_cb,
            None,
            None
        )

    def unregister(self, connection, path):
        if self.reg_id > 0:
            connection.unregister_object(self.reg_id)
            self.reg_id = 0

    def _method_cb(self, connection, sender, path, iface_name, method_name, params, invocation, user_data=None):
        if method_name == "ListRemotes":
            remotes = self.emit("handle-get-live-remotes")

            builder = GLib.VariantBuilder(GLib.VariantType("aa{sv}"))

            for remote in remotes:
                vdict = GLib.VariantDict.new()
                vdict.insert_value("uuid", GLib.Variant.new_string(remote.ident))
                vdict.insert_value("display-name", GLib.Variant.new_string(remote.display_name))
                vdict.insert_value("username", GLib.Variant.new_string(remote.user_name))
                vdict.insert_value("hostname", GLib.Variant.new_string(remote.display_hostname))
                vdict.insert_value("favorite", GLib.Variant.new_boolean(remote.favorite))
                vdict.insert_value("recent-time", GLib.Variant.new_int64(remote.recent_time))
                builder.add_value(vdict.end())
            props = builder.end()

            logging.debug("Received DBus call 'ListRemotes'. Returning: %s\n" % props)
            invocation.return_value(GLib.Variant.new_tuple(props))
        elif method_name == "SendFiles":
            ident, files = params.unpack()

            logging.debug("Received DBus call 'SendFiles'.\nRecipient: %s\nFiles: %s\n" % (ident, str(files)))

            self.emit("handle-send-files", *params.unpack())
            invocation.return_value(None)

