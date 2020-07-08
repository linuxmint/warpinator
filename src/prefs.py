import os
import gettext
import subprocess

from xapp.GSettingsWidgets import GSettingsSwitch, GSettingsFileChooser
from xapp.SettingsWidgets import SettingsWidget, SettingsPage, SpinButton, Entry
from gi.repository import Gtk, Gio, GLib

import config
import auth
import util

_ = gettext.gettext

PREFS_SCHEMA = "org.x.warpinator.preferences"

FOLDER_NAME_KEY = "receiving-folder"
START_WITH_WINDOW_KEY = "start-with-window"
AUTOSTART_KEY = "autostart"
ASK_PERMISSION_KEY = "ask-for-send-permission"
NO_OVERWRITE_KEY = "no-overwrite"
KEEP_PERMISSIONS_KEY = "keep-permissions"
PORT_KEY = "port"
SHOW_NOTIFICATIONS_KEY = "show-notifications"
FAVORITES_KEY = "favorites"
TRAY_ICON_KEY = "use-tray-icon"
SERVER_THREAD_POOL_SIZE_KEY = "server-thread-pool-size"
RPC_THREAD_POOL_SIZE_KEY = "rpc-thread-pool-size"

prefs_settings = Gio.Settings(schema_id=PREFS_SCHEMA)

if prefs_settings.get_string(FOLDER_NAME_KEY) == "":
    default = Gio.File.new_for_path(os.path.join(GLib.get_home_dir(), "Warpinator"))

    try:
        os.makedirs(default.get_path(), exist_ok=True)
    except:
        default = Gio.File.new_for_path(GLib.get_home_dir())

    prefs_settings.set_string(FOLDER_NAME_KEY, default.get_uri())

def get_port():
    return prefs_settings.get_int(PORT_KEY)

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

class Preferences():
    def __init__(self, transient_for):
        self.builder = Gtk.Builder.new_from_file(os.path.join(config.pkgdatadir, "prefs-window.ui"))

        self.window = self.builder.get_object("prefs_window")
        self.content_box = self.builder.get_object("content_box")

        self.window.set_title(title=_("Warpinator Preferences"))
        self.window.set_icon_name("preferences-system")

        self.window.set_transient_for(transient_for)

        size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)

        page = SettingsPage()
        self.content_box.pack_start(page, True, True, 0)

        section = page.add_section(_("Desktop"))

        self.settings_widget = GSettingsSwitch(_("Show an icon in the notification area"),
                                               PREFS_SCHEMA, TRAY_ICON_KEY)
        section.add_row(self.settings_widget)

        widget = GSettingsSwitch(_("Start with main window open"),
                                 PREFS_SCHEMA, START_WITH_WINDOW_KEY)

        section.add_reveal_row(widget, PREFS_SCHEMA, TRAY_ICON_KEY)

        widget = GSettingsSwitch(_("Start automatically"),
                                 PREFS_SCHEMA, AUTOSTART_KEY)
        section.add_row(widget)

        section = page.add_section(_("File Transfers"))

        widget = GSettingsFileChooser(_("Location for received files"),
                                      PREFS_SCHEMA, FOLDER_NAME_KEY,
                                      size_group=size_group, dir_select=True)
        section.add_row(widget)

        # widget = GSettingsSwitch(_("Preserve original file permissions"),
        #                          PREFS_SCHEMA, KEEP_PERMISSIONS_KEY)
        # section.add_row(widget)

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

        entry_size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.VERTICAL)
        button_size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.BOTH)

        widget = GroupCodeEntry(_("Group Code"),
                                tooltip=_("You cannot communicate with computers that do not use the same code."),
                                entry_size_group=entry_size_group,
                                button_size_group=button_size_group)

        section.add_row(widget)

        widget = PortSpinButton(_("Incoming port for transfers"),
                                mini=1024, maxi=49151, step=1, page=10,
                                size_group=size_group,
                                entry_size_group=entry_size_group,
                                button_size_group=button_size_group)

        section.add_row(widget)

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
Any port number will work for the application, but using the same port for all computers \
can make it simpler to add firewall exceptions if necessary."""))
        box.pack_start(label, False, False, 0)

        section.add_row(widget)

        self.window.show_all()

    def open_port(self, widget):
        settings = Gio.Settings(schema_id=PREFS_SCHEMA)

        self.run_port_script(settings.get_int(PORT_KEY))

    @util._async
    def run_port_script(self, port):
        command = os.path.join(config.libexecdir, "firewall", "ufw-modify")
        subprocess.run(["pkexec", command, str(port)])

        GLib.timeout_add_seconds(1, lambda: Gio.Application.get_default().firewall_script_finished())

class PortSpinButton(SpinButton):
    def __init__(self, *args, **kargs):
        button_size_group = kargs.pop("button_size_group")
        entry_size_group = kargs.pop("entry_size_group")

        super(PortSpinButton, self).__init__(*args, **kargs)

        self.old_port = get_port()
        self.my_settings = Gio.Settings(schema_id=PREFS_SCHEMA)
        self.set_spacing(6)

        self.accept_button = Gtk.Button(label=_("Change port"))
        self.accept_button.show()
        self.accept_button.set_sensitive(False)
        self.accept_button.get_style_context().add_class("suggested-action")
        self.accept_button.connect("clicked", self.apply_clicked)
        button_size_group.add_widget(self.accept_button)

        self.content_widget.set_value(get_port())
        entry_size_group.add_widget(self.content_widget)

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

class GroupCodeEntry(Entry):
    def __init__(self, *args, **kargs):
        button_size_group = kargs.pop("button_size_group")
        entry_size_group = kargs.pop("entry_size_group")

        super(GroupCodeEntry, self).__init__(*args, **kargs)

        self.code = auth.get_singleton().get_group_code().decode()
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
        auth.get_singleton().save_group_code(self.code)


