import os
import gettext

from xapp.GSettingsWidgets import GSettingsSwitch, GSettingsFileChooser
from xapp.SettingsWidgets import SettingsWidget, SettingsPage, SpinButton
from gi.repository import Gtk, Gio, GLib

import config

_ = gettext.gettext

PREFS_SCHEMA = "com.linuxmint.warp.preferences"

FOLDER_NAME_KEY = "receiving-folder"
START_WITH_WINDOW_KEY = "start-with-window"
# START_PINNED_KEY = "default-pinned"
AUTOSTART_KEY = "autostart"
ASK_PERMISSION_KEY = "ask-for-send-permission"
NO_OVERWRITE_KEY = "no-overwrite"
PORT_KEY = "port"
SHOW_NOTIFICATIONS_KEY = "show-notifications"
FAVORITES_KEY = "favorites"
TRAY_ICON_KEY = "use-tray-icon"

prefs_settings = Gio.Settings(schema_id=PREFS_SCHEMA)

def get_port():
    return prefs_settings.get_int(PORT_KEY)

def get_save_path():
    uri = prefs_settings.get_string(FOLDER_NAME_KEY)

    if uri == "":
        return GLib.get_home_dir()

    return Gio.File.new_for_uri(uri).get_path()

def use_tray_icon():
    return prefs_settings.get_boolean(TRAY_ICON_KEY)

def get_start_with_window():
    return prefs_settings.get_boolean(START_WITH_WINDOW_KEY)

# def get_start_pinned():
#     return prefs_settings.get_boolean(START_PINNED_KEY)

def require_permission_for_transfer():
    return prefs_settings.get_boolean(ASK_PERMISSION_KEY)

def prevent_overwriting():
    return prefs_settings.get_boolean(NO_OVERWRITE_KEY)

def get_show_notifications():
    return prefs_settings.get_boolean(SHOW_NOTIFICATIONS_KEY)

def get_is_favorite(hostname):
    return hostname in prefs_settings.get_strv(FAVORITES_KEY)

def toggle_favorite(hostname):
    faves = prefs_settings.get_strv(FAVORITES_KEY)

    if hostname in faves:
        faves.remove(hostname)
    else:
        faves.append(hostname)

    prefs_settings.set_strv(FAVORITES_KEY, faves)

class Preferences():
    def __init__(self, transient_for):
        self.builder = Gtk.Builder.new_from_file(os.path.join(config.pkgdatadir, "prefs-window.ui"))

        self.window = self.builder.get_object("prefs_window")
        self.content_box = self.builder.get_object("content_box")

        self.window.set_title(title=_("Warp Preferences"))
        self.window.set_icon_name("preferences-system")

        self.window.set_transient_for(transient_for)

        size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)

        page = SettingsPage()
        self.content_box.pack_start(page, True, True, 0)

        section = page.add_section(_("Desktop"))

        self.settings_widget = GSettingsSwitch(_("Show a Warpinator icon in the notification area"),
                                               PREFS_SCHEMA, TRAY_ICON_KEY)
        section.add_row(self.settings_widget)

        widget = GSettingsSwitch(_("Start with main window open"),
                                 PREFS_SCHEMA, START_WITH_WINDOW_KEY)

        section.add_reveal_row(widget, PREFS_SCHEMA, TRAY_ICON_KEY)

        # widget = GSettingsSwitch(_("Pin the window by default"),
        #                          PREFS_SCHEMA, START_PINNED_KEY)
        # section.add_row(widget)

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

        widget = GSettingsSwitch(_("Require approval when files would be overwritten"),
                                 PREFS_SCHEMA, NO_OVERWRITE_KEY)
        section.add_row(widget)

        widget = GSettingsSwitch(_("Display a notification when someone sends (or tries to send) you files"),
                                 PREFS_SCHEMA, SHOW_NOTIFICATIONS_KEY)
        section.add_row(widget)

        section = page.add_section(_("Network"))

        widget = PortSpinButton(_("Incoming port for transfers"),
                                mini=1024, maxi=49151, step=1, page=10, size_group=size_group)

        section.add_row(widget)

        widget = SettingsWidget()

        label = Gtk.Label(use_markup=True, label=_("""\
<b>Note on port numbers</b>: Any port number will work for the application, but using the same port for all computers
can make it simpler to add firewall exceptions if necessary."""))
        widget.add(label)

        section.add_row(widget)

        self.window.show_all()

class PortSpinButton(SpinButton):
    def __init__(self, *args, **kargs):
        super(PortSpinButton, self).__init__(*args, **kargs)

        self.old_port = get_port()
        self.my_settings = Gio.Settings(schema_id=PREFS_SCHEMA)
        self.set_spacing(6)

        self.accept_button = Gtk.Button(label=_("Change port"))
        self.accept_button.show()
        self.accept_button.set_sensitive(False)
        self.accept_button.get_style_context().add_class("suggested-action")
        self.accept_button.connect("clicked", self.apply_clicked)

        self.content_widget.set_value(get_port())

        self.pack_end(self.accept_button, False, False, 0)
        self.reorder_child(self.accept_button, 1)

    def get_range(self):
        return None

    def set_value(self, value):
        pass

    def get_value(self):
        pass

    def apply_later(self, *args):
        self.accept_button.set_sensitive(not (self.content_widget.get_value() == get_port()))

    def apply_clicked(self, widget, data=None):
        self.my_settings.set_int(PORT_KEY, int(self.content_widget.get_value()))
        self.accept_button.set_sensitive(False)