#!/usr/bin/python3

import threading
import logging
import netifaces
import ipaddress

import gi
gi.require_version('NM', '1.0')
from gi.repository import GLib, Gio, GObject, NM

import prefs
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
        "state-changed": (GObject.SignalFlags.RUN_LAST, None, (bool,)),
        "details-changed": (GObject.SignalFlags.RUN_LAST, None, ())
    }

    def __init__(self):
        GObject.Object.__init__(self)
        logging.debug("Starting network monitor")
        self.nm_client = None
        self.device = None
        self.current_iface = None
        self.online = False

        self.signals_connected = False
        self.details_idle_id = 0

        self.initing = True
        self.gio_monitor = Gio.NetworkMonitor.get_default()
        NM.Client.new_async(None, self.nm_client_acquired);

    def nm_client_acquired(self, source, res, data=None):
        try:
            self.nm_client = NM.Client.new_finish(res)
            self.nm_client.connect("notify::connectivity", self.nm_client_connectivity_changed)
            self.signals_connected = True
            self.reload_state()

            prefs.prefs_settings.connect("changed", self.on_prefs_changed)

            self.initing = False
            self.emit("ready")
        except GLib.Error as e:
            logging.critical("NetworkMonitor: Could not create NM Client: %s" % e.message)

    def ready(self):
        return self.nm_client != None

    def on_prefs_changed(self, settings, key, data=None):
        new_main_port = prefs.get_port()
        new_auth_port = prefs.get_auth_port()
        new_iface = prefs.get_preferred_iface()

        emit = False

        if self.device == None or self.device.get_iface() != new_iface:
            self.reload_state()
            return

        if self.main_port != new_main_port:
            self.main_port = new_main_port
            emit = True
        if self.auth_port != new_auth_port:
            self.auth_port = new_auth_port
            emit = True

        if emit:
            self.emit_details_changed()

    def reload_state(self):
        if self.nm_client == None:
            return

        old_online = self.online
        new_device = None
        new_iface = self.get_preferred_or_default_iface()

        if self.device != None:
            if new_iface == self.device.get_iface():
                return

        if new_iface:
            new_device = self.nm_client.get_device_by_iface(new_iface)

        need_restart = False

        if new_device == None or new_iface == None:
            self.device = None
            self.current_iface = None
            self.online = False
            need_restart = True
        elif new_device != self.device or new_iface != self.current_iface:
            self.device = new_device
            self.current_iface = new_iface
            self.online = self.check_online()
            need_restart = True

        self.main_port = prefs.get_port()
        self.auth_port = prefs.get_auth_port()

        if self.initing:
            return

        if need_restart:
            self.emit_state_changed()
            logging.debug("Current network changed (%s), connectivity: %s" % (prefs.get_preferred_iface(), str(self.online)))

    def check_online(self):
        if self.device == None or self.current_iface == None:
            return False

        try:
            reqd_states = (NM.ConnectivityState.LIMITED, NM.ConnectivityState.FULL)

            return self.device.get_connectivity(GLib.SYSDEF_AF_INET) in reqd_states or \
                   self.device.get_connectivity(GLib.SYSDEF_AF_INET6) in reqd_states
        except AttributeError:
            # libnm < 1.16
            conn = self.device.get_active_connection()
            if conn:
                config = conn.get_ip4_config()
                if config:
                    gateway = config.get_gateway()
                    try:
                        connectable = Gio.NetworkAddress.parse(gateway, 53)
                        return self.gio_monitor.can_reach(connectable, None)
                    except Exception as e:
                        return False

    def nm_client_connectivity_changed(self, client, pspec, data=None):
        logging.debug("NM client connectivity prop changed: %s" % client.props.connectivity)
        self.reload_state()

    def stop(self):
        logging.debug("Stopping network monitor")
        try:
            self.nm_client.disconnect_by_func(self.nm_client_connectivity_changed)
        except:
            pass

        self.nm_client = None

    def get_interface_names(self):
        names = []
        for device in self.nm_client.get_devices():
            names.append(device.get_ip_iface())

        return names

    def get_ips(self):
        return util.IPAddresses(self.get_ipv4(), self.get_ipv6())

    def get_ipv4(self):
        if self.device != None:
            con = self.device.get_active_connection()

            if con != None:
                ip4c = con.get_ip4_config()
                if ip4c != None:
                    addrs = ip4c.get_addresses()

                    if addrs != []:
                        return addrs[0].get_address()

        return "0.0.0.0"

    def get_ipv6(self):
        # We don't actually support ipv6 currently.
        return None

        if self.device != None:
            con = self.device.get_active_connection()

            if con != None:
                ip6c = con.get_ip6_config()
                if ip6c != None:
                    addrs = ip6c.get_addresses()

                    if addrs != []:
                        return addrs[0].get_address()

        return None

    def get_preferred_or_default_iface(self):
        iface = prefs.get_preferred_iface()
        def_iface = self.get_default_interface()

        if iface == "auto" or iface == "":
            logging.debug("Automatic interface selection: %s" % def_iface)
            return def_iface

        if iface != "auto":
            for dev in self.get_devices():
                if dev.get_iface() == iface:
                    return iface

        logging.warning("Preferred interface (%s) not available.")
        return None

    def get_current_iface(self):
        return self.current_iface

    def get_default_interface(self):
        con = self.nm_client.get_primary_connection()

        if con != None:
            return con.get_devices()[0].get_iface()

        return None

    def get_devices(self):
        devices = []

        for device in self.nm_client.get_devices():
            if device.get_device_type() in (NM.DeviceType.ETHERNET, NM.DeviceType.WIFI):
                devices.append(device)

        return devices

    # TODO: Do this with libnm
    def same_subnet(self, other_ips):
        net = netifaces.ifaddresses(self.device.get_ip_iface())

        addresses = net[netifaces.AF_INET]
        for address in addresses:
            if address["addr"] == self.get_ipv4():
                iface = ipaddress.IPv4Interface("%s/%s" % (address["addr"], address["netmask"]))

        my_net = iface.network

        if my_net == None:
            # We're more likely to have failed here than to have found something on a different subnet.
            return True

        if my_net.netmask.exploded == "255.255.255.255":
            logging.warning("Discovery: netmask is 255.255.255.255 - are you on a vpn?")
            return False

        for addr in list(my_net.hosts()):
            if other_ips.ip4 == addr.exploded:
                return True

        return False

    @util._idle
    def emit_state_changed(self):
        logging.debug("Network state changed: online = %s" % str(self.online))
        self.emit("state-changed", self.online)

    def emit_details_changed(self):
        def cb(data=None):
            if self.device != None:
                iface = self.device.get_iface()
            else:
                iface = "none"

            logging.debug("Network details changed: iface: %s, mp: %d, ap: %s" % (iface, self.main_port, self.auth_port))
            self.emit("details-changed")

        if self.details_idle_id > 0:
            GLib.source_remove(self.details_idle_id)

        self.details_idle_id = GLib.timeout_add(50, cb)

