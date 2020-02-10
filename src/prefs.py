import locale
import gettext

from xapp.GSettingsWidgets import *
from gi.repository import Gtk

import config
import util

# i18n
locale.bindtextdomain(config.PACKAGE, config.localedir)
gettext.bindtextdomain(config.PACKAGE, config.localedir)
gettext.textdomain(config.PACKAGE)
_ = gettext.gettext

class Preferences(Gtk.Window):
    def __init__(self):
        super(Preferences, self).__init__(modal=True, title=_("Warp Preferences"))

        size_group = Gtk.SizeGroup.new(Gtk.SizeGroupMode.HORIZONTAL)

        page = SettingsPage()
        self.add(page)
        section = page.add_section(_("General"))

        widget = GSettingsEntry(_("Nickname: "),
                                util.PREFS_SCHEMA, util.BROADCAST_NAME_KEY,
                                size_group=size_group)
        section.add_row(widget)

        widget = GSettingsFileChooser(_("Location for received files:"),
                                      util.PREFS_SCHEMA, util.FOLDER_NAME_KEY,
                                      size_group=size_group, dir_select=True)
        section.add_row(widget)

        widget = GSettingsSwitch(_("Start with main window open"),
                                 util.PREFS_SCHEMA, util.START_WITH_WINDOW_KEY)
        section.add_row(widget)

        widget = GSettingsSwitch(_("Pin the window by default"),
                                 util.PREFS_SCHEMA, util.START_PINNED_KEY)

        section.add_row(widget)
        self.show_all()