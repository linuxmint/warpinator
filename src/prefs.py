import locale
import gettext

from xapp.GSettingsWidgets import *
from gi.repository import Gtk, Gio

import config
import util

# i18n
locale.bindtextdomain(config.PACKAGE, config.localedir)
gettext.bindtextdomain(config.PACKAGE, config.localedir)
gettext.textdomain(config.PACKAGE)
_ = gettext.gettext

PREFS_SCHEMA = "com.linuxmint.warp.preferences"

BROADCAST_NAME_KEY = "broadcast-name"
FOLDER_NAME_KEY = "receiving-folder"
START_WITH_WINDOW_KEY = "start-with-window"
START_PINNED_KEY = "default-pinned"
AUTOSTART_KEY = "autostart"
ASK_PERMISSION_KEY = "ask-for-send-permission"

prefs_settings = Gio.Settings(schema_id=PREFS_SCHEMA)

def get_nick():
    return prefs_settings.get_string(BROADCAST_NAME_KEY)

def get_save_path():
    uri = prefs_settings.get_string(FOLDER_NAME_KEY)

    if uri == "":
        return GLib.get_home_dir()

    return Gio.File.new_for_uri(uri).get_path()

def get_start_with_window():
    return prefs_settings.get_boolean(START_WITH_WINDOW_KEY)

def get_start_pinned():
    return prefs_settings.get_boolean(START_PINNED_KEY)

def get_ask_permission():
    return prefs_settings.get_boolean(ASK_PERMISSION_KEY)

class Preferences(Gtk.Window):
    def __init__(self):
        super(Preferences, self).__init__(modal=True, title=_("Warp Preferences"))

        size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)

        page = SettingsPage()
        self.add(page)
        section = page.add_section(_("General"))

        widget = GSettingsEntry(_("Nickname"),
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

        widget = GSettingsSwitch(_("Ask for permission before starting a file transfer"),
                                 PREFS_SCHEMA, ASK_PERMISSION_KEY)
        section.add_row(widget)

        self.show_all()