#!/usr/bin/python3

import os
import gettext
import subprocess
import logging
import json
import re

from xapp.GSettingsWidgets import GSettingsSwitch, GSettingsFileChooser, GSettingsComboBox
from xapp.SettingsWidgets import SettingsWidget, SettingsPage, SettingsStack, SpinButton, Entry, Button, ComboBox
from gi.repository import Gtk, Gio, GLib

import config
import auth
import util
import networkmonitor

_ = gettext.gettext

PREFS_SCHEMA = "org.x.warpinator.preferences"

FOLDER_NAME_KEY = "receiving-folder"
START_WITH_WINDOW_KEY = "start-with-window"
AUTOSTART_KEY = "autostart"
ASK_PERMISSION_KEY = "ask-for-send-permission"
NO_OVERWRITE_KEY = "no-overwrite"
KEEP_PERMISSIONS_KEY = "keep-permissions"
PRESERVE_TIMESTAMP_KEY = "preserve-timestamp"
NET_IFACE="preferred-network-iface"
PORT_KEY = "port"
REG_PORT_KEY = "reg-port"
SHOW_NOTIFICATIONS_KEY = "show-notifications"
FAVORITES_KEY = "favorites"
TRAY_ICON_KEY = "use-tray-icon"
SERVER_THREAD_POOL_SIZE_KEY = "server-thread-pool-size"
RPC_THREAD_POOL_SIZE_KEY = "rpc-thread-pool-size"
USE_COMPRESSION_KEY = "use-compression"
COMPRESSION_LEVEL_KEY = "zlib-compression-level"
BLOCK_SIZE_KEY = "transfer-block-size"
MIN_FREE_SPACE_KEY = "minimum-free-space"

prefs_settings = Gio.Settings(schema_id=PREFS_SCHEMA)

#### One-time initializers
if prefs_settings.get_string(FOLDER_NAME_KEY) == "":
    default = Gio.File.new_for_path(os.path.join(GLib.get_home_dir(), "Warpinator"))

    try:
        os.makedirs(default.get_path(), exist_ok=True)
    except:
        default = Gio.File.new_for_path(GLib.get_home_dir())

    prefs_settings.set_string(FOLDER_NAME_KEY, default.get_uri())
####

if prefs_settings.get_int(PORT_KEY) == prefs_settings.get_int(REG_PORT_KEY):
    prefs_settings.set_int(REG_PORT_KEY, prefs_settings.get_int(PORT_KEY) + 1)

def get_preferred_iface():
    return prefs_settings.get_string(NET_IFACE)

def get_port():
    return prefs_settings.get_int(PORT_KEY)

def get_auth_port():
    return prefs_settings.get_int(REG_PORT_KEY)

def get_save_uri():
    uri = prefs_settings.get_string(FOLDER_NAME_KEY)

    return uri

def get_save_path():
    return Gio.File.new_for_uri(get_save_uri()).get_path()

def use_tray_icon():
    return prefs_settings.get_boolean(TRAY_ICON_KEY)

def get_start_with_window():
    return prefs_settings.get_boolean(START_WITH_WINDOW_KEY)

def require_permission_for_transfer():
    return prefs_settings.get_boolean(ASK_PERMISSION_KEY)

def prevent_overwriting():
    return prefs_settings.get_boolean(NO_OVERWRITE_KEY)

def preserve_permissions():
    return prefs_settings.get_boolean(KEEP_PERMISSIONS_KEY)

def preserve_timestamp():
    return prefs_settings.get_boolean(PRESERVE_TIMESTAMP_KEY)

def get_show_notifications():
    return prefs_settings.get_boolean(SHOW_NOTIFICATIONS_KEY)

def get_is_favorite(ident):
    return ident in prefs_settings.get_strv(FAVORITES_KEY)

def toggle_favorite(ident):
    faves = prefs_settings.get_strv(FAVORITES_KEY)

    if ident in faves:
        faves.remove(ident)
    else:
        faves.append(ident)

    prefs_settings.set_strv(FAVORITES_KEY, faves)

def get_remote_pool_max_threads():
    setting_value = prefs_settings.get_int(RPC_THREAD_POOL_SIZE_KEY)

    if setting_value == 0:
        setting_value = max(8, os.cpu_count() + 4)

    return setting_value

def get_server_pool_max_threads():
    setting_value = prefs_settings.get_int(SERVER_THREAD_POOL_SIZE_KEY)

    return max(setting_value, 2)

def use_compression():
    return prefs_settings.get_boolean(USE_COMPRESSION_KEY)

def get_compression_level():
    level = prefs_settings.get_int(COMPRESSION_LEVEL_KEY)
    if level in range(-1, 9 + 1):
        return level

    logging.warning("Compression setting out of range (must be -1 thru 9), using default.")
    return -1

def get_block_size():
    return prefs_settings.get_int(BLOCK_SIZE_KEY) * 1024

def get_min_free_space():
    return prefs_settings.get_uint(MIN_FREE_SPACE_KEY)

class Preferences():
    def __init__(self, transient_for):
        self.builder = Gtk.Builder.new_from_file(os.path.join(config.pkgdatadir, "prefs-window.ui"))

        self.window = self.builder.get_object("prefs_window")
        self.content_box = self.builder.get_object("content_box")
        self.page_switcher = self.builder.get_object("page_switcher")

        self.window.set_title(title=_("Warpinator Preferences"))
        self.window.set_icon_name("preferences-system")

        self.window.set_transient_for(transient_for)

        size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)

        page_stack = SettingsStack()
        self.content_box.pack_start(page_stack, True, True, 0)
        self.page_switcher.set_stack(page_stack)

        # Settings
        page = SettingsPage()
        page_stack.add_titled(page, "general", _("General"))

        section = page.add_section(_("Desktop"))

        widget = GSettingsSwitch(_("Show an icon in the notification area"),
                                               PREFS_SCHEMA, TRAY_ICON_KEY)
        section.add_row(widget)

        widget = GSettingsSwitch(_("Start with main window open"),
                                 PREFS_SCHEMA, START_WITH_WINDOW_KEY)

        section.add_reveal_row(widget, PREFS_SCHEMA, TRAY_ICON_KEY)

        widget = GSettingsSwitch(_("Start automatically"),
                                 PREFS_SCHEMA, AUTOSTART_KEY)
        section.add_row(widget)

        section = page.add_section(_("File Transfers"))

        widget = GSettingsSwitch(_("Use compression when possible."),
                                 PREFS_SCHEMA, USE_COMPRESSION_KEY,
                                 tooltip=_("Warning: This may have a negative impact on performance on some faster networks."))
        section.add_row(widget)

        widget = GSettingsFileChooser(_("Location for received files"),
                                      PREFS_SCHEMA, FOLDER_NAME_KEY,
                                      size_group=size_group, dir_select=True)
        section.add_row(widget)

        widget = GSettingsSwitch(_("Require approval before accepting files"),
                                 PREFS_SCHEMA, ASK_PERMISSION_KEY)
        section.add_row(widget)

        widget = GSettingsSwitch(_("Require approval when files would be overwritten"),
                                 PREFS_SCHEMA, NO_OVERWRITE_KEY)
        section.add_row(widget)

        widget = GSettingsSwitch(_("Display a notification when someone sends (or tries to send) you files"),
                                 PREFS_SCHEMA, SHOW_NOTIFICATIONS_KEY)
        section.add_row(widget)

        page = SettingsPage()
        page_stack.add_titled(page, "network", _("Connection"))

        section = page.add_section(_("Identification"))

        entry_size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.VERTICAL)
        button_size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.BOTH)

        widget = GroupCodeEntry(_("Group Code"),
                                tooltip=_("You cannot communicate with computers that do not use the same code."),
                                entry_size_group=entry_size_group,
                                button_size_group=button_size_group)

        section.add_row(widget)

        section = page.add_section(_("Network"))

        options = []
        options.append(("auto", _("Automatic")))

        current = get_preferred_iface()
        current_selection_exists = current == "auto" or False

        # use lshw to get any interface 'product' names (Intel blah blah)
        j = []
        try:
            lshw_out = subprocess.check_output(["lshw", "-class", "network", "-sanitize", "-json"],
                                               stderr=subprocess.DEVNULL
                                              ).decode("utf-8")

            lshw_out = re.sub("\A\s*{", "[{", lshw_out)
            lshw_out = re.sub("}\s*{", "}, {", lshw_out)
            lshw_out = re.sub("}\s*\\n\Z", "}]\n", lshw_out)
            j = json.loads(lshw_out)
        except:
            pass

        def lookup_name(iface, node):
            for entry in node:
                try:
                    entry_product = entry["product"]
                except KeyError:
                    entry_product = ""

                try:
                    entry_iface = entry["logicalname"]
                    if entry_iface == iface:
                        return entry_product
                    else:
                        continue
                except KeyError:
                    try:
                        children = entry["children"]
                        name = lookup_name(iface, children)
                        if name != "":
                            return name
                        # Use the parent product if it had one
                        elif entry_product != "":
                            return entry_product
                    except KeyError:
                        continue

            return ""

        available = networkmonitor.get_network_monitor().get_valid_interface_infos()
        valid_info = []

        for info in available:
            item = {}
            item["logicalname"] = info.iface
            item["product"] = lookup_name(info.iface, j)
            valid_info.append(item)

        for dev in valid_info:
            iface = dev["logicalname"]

            try:
                desc = dev["product"]
            except KeyError:
                desc = ""

            if iface == current:
                current_selection_exists = True

            if (desc != None and desc != ""):
                orig_label = "%s - %s" % (iface, desc)
                if len(orig_label) > 50:
                    label = orig_label[:47] + "..."
                else:
                    label = orig_label

                options.append((iface, label))
            else:
                options.append((iface, iface))

        if not current_selection_exists:
            # translation: combobox item shown when a previosuly set interface can no longer be found - 'wlan0 - not found'
            options.append((get_preferred_iface(), _("%s - not found") % get_preferred_iface()))

        self.iface_combo = ComboBox(_("Network interface to use"),
                                    options,
                                    valtype=str)
        self.iface_combo.content_widget.set_active_iter(self.iface_combo.option_map[get_preferred_iface()])
        self.iface_combo.label.set_line_wrap(False)

        section.add_row(self.iface_combo)

        self.main_port = PortSpinButton(_("Incoming port for transfers"),
                                        mini=1024, maxi=49151, step=1, page=10,
                                        size_group=size_group,
                                        entry_size_group=entry_size_group,
                                        button_size_group=button_size_group)
        section.add_row(self.main_port)

        self.auth_port = PortSpinButton(_("Incoming port for registration"),
                                        mini=1024, maxi=49151, step=1, page=10,
                                        size_group=size_group,
                                        entry_size_group=entry_size_group,
                                        button_size_group=button_size_group)
        section.add_row(self.auth_port)

        self.main_port.content_widget.set_value(get_port())
        self.auth_port.content_widget.set_value(get_auth_port())

        self.settings = Gio.Settings(schema_id=PREFS_SCHEMA)
        self.main_port.content_widget.connect("value-changed", self.net_values_changed)
        self.auth_port.content_widget.connect("value-changed", self.net_values_changed)
        self.iface_combo_id = self.iface_combo.content_widget.connect("changed", self.net_values_changed)

        self.port_button = Button(_("Apply network changes"), self.apply_net_settings)
        self.port_button.content_widget.set_sensitive(False)
        self.port_button.content_widget.get_style_context().add_class("suggested-action")

        section.add_row(self.port_button)

        widget = SettingsWidget()

        if config.include_firewall_mod and GLib.find_program_in_path("ufw"):
            button = Gtk.Button(label=_("Update firewall rules"), valign=Gtk.Align.CENTER)
            button.connect("clicked", self.open_port)

            widget.pack_end(button, False, False, 0)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        widget.pack_start(box, True, True, 0)

        # Pulling in a label with attributes was simpler than trying to add attributes
        # to a label here - the PangoAttribute python binding for font weight is missing.
        box.pack_start(self.builder.get_object("port_help_heading"), False, False, 0)

        label = Gtk.Label(wrap=True, xalign=0.0, label=_("""\
Any port numbers will work for the application, but using the same ports for all computers \
can make it simpler to add firewall exceptions if necessary."""))
        box.pack_start(label, False, False, 0)

        section.add_row(widget)

        self.window.show_all()

    def open_port(self, widget):
        self.run_port_script(self.settings.get_int(PORT_KEY), self.settings.get_int(REG_PORT_KEY))

    def net_values_changed(self, widget, data=None):
        main_widget_value = self.main_port.content_widget.get_value()
        auth_widget_value = self.auth_port.content_widget.get_value()

        iface_widget_value = None
        tree_iter = self.iface_combo.content_widget.get_active_iter()
        if tree_iter != None:
            iface_widget_value = self.iface_combo.model[tree_iter][0]

        if main_widget_value == get_port() and \
          auth_widget_value == get_auth_port() and \
          iface_widget_value == get_preferred_iface():
            self.port_button.content_widget.set_sensitive(False)
            return

        if (main_widget_value == auth_widget_value):
            self.port_button.content_widget.set_sensitive(False)
            return

        self.port_button.content_widget.set_sensitive(True)

    def apply_net_settings(self, widget, data=None):
        self.settings.delay()

        self.settings.set_int(PORT_KEY, self.main_port.content_widget.get_value())
        self.settings.set_int(REG_PORT_KEY, self.auth_port.content_widget.get_value())

        iface_widget_value = None
        tree_iter = self.iface_combo.content_widget.get_active_iter()
        if tree_iter != None:
            iface_widget_value = self.iface_combo.model[tree_iter][0]

        if iface_widget_value == None:
            iface_widget_value = "auto"

            self.iface_combo.content_widget.disconnect(self.iface_combo_id)
            self.iface_combo.content_widget.set_active_iter(self.iface_combo.option_map[get_preferred_iface()])
            self.iface_combo_id = self.iface_combo.content_widget.connect("changed", self.net_values_changed)

        self.settings.set_string(NET_IFACE, iface_widget_value)

        self.port_button.content_widget.set_sensitive(False)

        self.settings.apply()

    @util._async
    def run_port_script(self, port, auth_port):
        command = os.path.join(config.libexecdir, "firewall", "ufw-modify")
        subprocess.run(["pkexec", command, str(port), str(auth_port)])

        GLib.timeout_add_seconds(1, lambda: Gio.Application.get_default().firewall_script_finished())

class PortSpinButton(SpinButton):
    def __init__(self, *args, **kargs):
        button_size_group = kargs.pop("button_size_group")
        entry_size_group = kargs.pop("entry_size_group")

        super(PortSpinButton, self).__init__(*args, **kargs)

        entry_size_group.add_widget(self.content_widget)

    def get_range(self):
        return None

    def set_value(self, value):
        pass

    def get_value(self):
        pass

    def apply_later(self, *args):
        pass

class GroupCodeEntry(Entry):
    def __init__(self, *args, **kargs):
        button_size_group = kargs.pop("button_size_group")
        entry_size_group = kargs.pop("entry_size_group")

        super(GroupCodeEntry, self).__init__(*args, **kargs)

        self.code = auth.get_singleton().get_group_code()
        self.content_widget.set_text(self.code)

        entry_size_group.add_widget(self.content_widget)
        self.content_widget.connect("changed", self.text_changed)

        self.set_child_packing(self.content_widget, False, False, 0, Gtk.PackType.END)
        self.set_spacing(6)

        self.accept_button = Gtk.Button(label=_("Set code"))
        self.accept_button.show()
        self.accept_button.set_sensitive(False)
        self.accept_button.get_style_context().add_class("suggested-action")
        self.accept_button.connect("clicked", self.apply_clicked)
        button_size_group.add_widget(self.accept_button)

        self.pack_end(self.accept_button, False, False, 0)
        self.reorder_child(self.accept_button, 1)

    def text_changed(self, widget, data=None):
        text = self.content_widget.get_text()

        if text == "":
            widget.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "dialog-error-symbolic")
            widget.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, _("A group code is required."))
            self.accept_button.set_sensitive(False)
            return

        if len(text) < 8:
            widget.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, "dialog-warning-symbolic")
            widget.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, _("The group code should be longer if possible."))
        else:
            widget.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, None)

        self.accept_button.set_sensitive(self.content_widget.get_text() != self.code)

    def apply_clicked(self, widget, data=None):
        self.code = self.content_widget.get_text()
        self.accept_button.set_sensitive(False)
        auth.get_singleton().update_group_code(self.code)


