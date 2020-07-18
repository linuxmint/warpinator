import threading
import logging

import gi
gi.require_version('NM', '1.0')
from gi.repository import GLib, GObject, NM

import util

network_monitor = None

def get_network_monitor():
    global network_monitor

    if network_monitor == None:
        network_monitor = NetworkMonitor()

    return network_monitor

class NetworkMonitor(GObject.Object):
    __gsignals__ = {
        "ready": (GObject.SignalFlags.RUN_LAST, None, ()),
        "state-changed": (GObject.SignalFlags.RUN_LAST, None, (bool,))
    }

    def __init__(self):
        GObject.Object.__init__(self)
        logging.debug("Starting network monitor")
        self.nm_client = None
        self.nm_device = None
        self.sleep_timer = None
        self.online = False
        self.iface = None
        self.ip = None

        self.signals_connected = False

        NM.Client.new_async(None, self.nm_client_acquired);

    def update_current_network(self, iface, ip):
        self.iface = iface
        self.ip = ip
        self.online = self.nm_check_interface_online()
        logging.debug("Current network changed (%s), connectivity: %s" % (iface, str(self.online)))

        if not self.signals_connected:
            self.nm_client.connect("notify::connectivity", self.nm_client_connectivity_changed)
            self.signals_connected = True

    def nm_client_acquired(self, source, res, data=None):
        try:
            self.nm_client = NM.Client.new_finish(res)
            self.emit("ready")
        except GLib.Error as e:
            logging.critical("NetworkMonitor: Could not create NM Client, using polling instead: %s" % e.message)
            self.sleep_timer = threading.Event()
            self.start_polling()

    def nm_check_interface_online(self):
        device = self.nm_client.get_device_by_iface(self.iface)

        if device == None:
            return False

        conn = device.get_active_connection()

        if conn != None:
            return conn.get_state() == NM.ActiveConnectionState.ACTIVATED
        elif device.get_state() == NM.DeviceState.UNMANAGED:
            return util.get_ip_for_iface(self.iface) != "0.0.0.0"

        return False

    def nm_client_connectivity_changed(self, *args, **kwargs):
        online = self.nm_check_interface_online()

        if online != self.online:
            self.online = online
            self.emit_state_changed()

    @util._async
    def start_polling(self):
        while not self.sleep_timer.is_set():
            self.check_online_fallback()
            self.sleep_timer.wait(4)

    def stop(self):
        logging.debug("Stopping network monitor")
        if self.nm_client != None:
            try:
                self.nm_client.disconnect_by_func(self.nm_client_connectivity_changed)
            except:
                pass
            self.nm_client = None
        else:
            self.sleep_timer.set()

    def check_online_fallback(self):
        old_online = self.online
        old_ip = self.current_ip

        self.current_ip = util.get_ip_for_iface(self.iface)
        self.online = self.current_ip != "0.0.0.0"

        if (self.online != old_online) or (self.current_ip != old_ip):
            self.emit_state_changed()

    @util._idle
    def emit_state_changed(self):
        logging.debug("Network state changed: online = %s" % str(self.online))
        self.emit("state-changed", self.online)
