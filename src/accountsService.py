#!/usr/bin/python3

import gi
gi.require_version('AccountsService', '1.0')
from gi.repository import GObject, AccountsService, GLib
import os

class AccountsServiceClient(GObject.Object):
    """
    Singleton for working with the AccountsService, which we use
    to retrieve the user's face image and their real name.
    """
    __gsignals__ = {
        'account-loaded': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        super(AccountsServiceClient, self).__init__()

        self.is_loaded = False

        self.service = AccountsService.UserManager.get_default().get_user(GLib.get_user_name())
        self.loaded_id = self.service.connect("notify::is-loaded",
                                              self.on_accounts_service_loaded)

    def on_accounts_service_loaded(self, service, param):
        self.is_loaded = True
        print("acccounts loaded: ", self.service.get_real_name())
        self.emit("account-loaded")
        self.service.disconnect(self.loaded_id)

    def get_real_name(self):
        return self.service.get_real_name()

    def get_face_path(self):
        face_path = None
        home_path = self.service.get_home_dir()
        if home_path is None:
            home_path = os.path.expanduser('~')

        for path in [os.path.join(home_path, ".face"),
                     self.service.get_icon_file()]:
            if os.path.exists(path):
                face_path = path
                break

        return face_path
