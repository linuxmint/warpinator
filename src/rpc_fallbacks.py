from gi.repository import Gtk

import transfers
import util

def default_avatar_iterator():
    theme = Gtk.IconTheme.get_default()

    s, w, h = Gtk.IconSize.lookup(Gtk.IconSize.DND)

    info = theme.lookup_icon_for_scale("avatar-default",
                                       w, util.get_global_scale_factor(),
                                       Gtk.IconLookupFlags.FORCE_SVG)

    path = info.get_filename()

    return transfers.load_file_in_chunks(path)
