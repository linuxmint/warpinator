import locale
import gettext

from xapp.GSettingsWidgets import *
from xapp.SettingsWidgets import SettingsWidget
from gi.repository import Gtk, Gio

import config
import util

_ = gettext.gettext

PREFS_SCHEMA = "com.linuxmint.warp.preferences"

BROADCAST_NAME_KEY = "broadcast-name"
FOLDER_NAME_KEY = "receiving-folder"
START_WITH_WINDOW_KEY = "start-with-window"
START_PINNED_KEY = "default-pinned"
AUTOSTART_KEY = "autostart"
ASK_PERMISSION_KEY = "ask-for-send-permission"
NO_OVERWRITE_KEY = "no-overwrite"
PORT_KEY = "port"
FAVORITES_KEY = "favorites"

prefs_settings = Gio.Settings(schema_id=PREFS_SCHEMA)

def get_nick():
    return prefs_settings.get_string(BROADCAST_NAME_KEY)

def get_port():
    return prefs_settings.get_int(PORT_KEY)

def get_server_port():
    return prefs_settings.get_int(PORT_KEY) + 1

def get_save_path():
    uri = prefs_settings.get_string(FOLDER_NAME_KEY)

    if uri == "":
        return GLib.get_home_dir()

    return Gio.File.new_for_uri(uri).get_path()

def get_start_with_window():
    return prefs_settings.get_boolean(START_WITH_WINDOW_KEY)

def get_start_pinned():
    return prefs_settings.get_boolean(START_PINNED_KEY)

def require_permission_for_transfer():
    return prefs_settings.get_boolean(ASK_PERMISSION_KEY)

def prevent_overwriting():
    return prefs_settings.get_boolean(NO_OVERWRITE_KEY)

def get_is_favorite(hostname):
    return hostname in prefs_settings.get_strv(FAVORITES_KEY)

def toggle_favorite(hostname):
    faves = prefs_settings.get_strv(FAVORITES_KEY)

    if hostname in faves:
        faves.remove(hostname)
    else:
        faves.append(hostname)

    prefs_settings.set_strv(FAVORITES_KEY, faves)

class Preferences(Gtk.Window):
    def __init__(self):
        super(Preferences, self).__init__(modal=True, title=_("Warp Preferences"))

        size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)

        page = SettingsPage()
        self.add(page)
        section = page.add_section(_("General"))

        widget = GSettingsEntry(_("Display name"),
                                PREFS_SCHEMA, BROADCAST_NAME_KEY,
                                size_group=size_group)
        section.add_row(widget)

        widget = GSettingsSwitch(_("Start with main window open"),
                                 PREFS_SCHEMA, START_WITH_WINDOW_KEY)
        section.add_row(widget)

        widget = GSettingsSwitch(_("Pin the window by default"),
                                 PREFS_SCHEMA, START_PINNED_KEY)
        section.add_row(widget)

        widget = GSettingsSwitch(_("Start automatically"),
                                 PREFS_SCHEMA, AUTOSTART_KEY)
        section.add_row(widget)

        section = page.add_section(_("File Transfers"))

        widget = GSettingsFileChooser(_("Location for received files"),
                                      PREFS_SCHEMA, FOLDER_NAME_KEY,
                                      size_group=size_group, dir_select=True)
        section.add_row(widget)

        widget = GSettingsSwitch(_("Require approval before accepting files"),
                                 PREFS_SCHEMA, ASK_PERMISSION_KEY)
        section.add_row(widget)

        section = page.add_section(_("Network"))

        widget = GSettingsSpinButton(_("Port to use for traffic (program restart required)."),
                                     PREFS_SCHEMA, PORT_KEY, mini=1024, maxi=49151, step=1, page=10, size_group=size_group)

        section.add_row(widget)

        widget = SettingsWidget()

        label = Gtk.Label(use_markup=True, label=_("""\
<b>Note on port numbers</b>: Any port number will work for the application, but using the same port for all computers
can make it simpler to add firewall exceptions if necessary."""))
        widget.add(label)

        section.add_row(widget)

        self.show_all()