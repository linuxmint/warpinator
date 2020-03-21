import gettext

from gi.repository import Gio, GLib

import util
from util import OpStatus
import prefs

_ = gettext.gettext


class NewOpUserNotification():
    def __init__(self, op):
        self.op = op

        self.send_notification()

    @util._idle
    def send_notification(self):
        if prefs.get_show_notifications():
            notification = Gio.Notification.new(_("New incoming files"))

            if prefs.require_permission_for_transfer():
                # John Johnson would like to send you 1 file (foobar.txt)
                # John Johnson would like to send you 5 files
                body =gettext.ngettext(
                    _("%s would like to send you %d file (%s)."),
                    _("%s would like to send you %d files%s"),self.op.total_count) \
                        % (self.op.sender_name,
                           self.op.total_count,
                           self.op.top_dir_basenames[0] if self.op.total_count == 1 else "")

                notification.set_body(body)
                notification.set_icon(Gio.ThemedIcon(name="mail-send-symbolic"))

                notification.add_button(_("Accept"), "app.notification-response::accept")
                notification.add_button(_("Decline"), "app.notification-response::decline")
                notification.set_default_action("app.notification-response::focus")

                notification.set_priority(Gio.NotificationPriority.URGENT)

                app = Gio.Application.get_default()
                app.lookup_action("notification-response").connect("activate", self._notification_response, self.op)

                self.op.connect("status-changed", \
                   lambda op: app.withdraw_notification(op.sender) if self.op.status != OpStatus.WAITING_PERMISSION else None)
            else:
                # John Johnson is sending you 1 file (foobar.txt)
                # John Johnson is sending you 5 files
                body =gettext.ngettext(
                    _("%s is sending you %d file (%s)."),
                    _("%s is sending you %d files%s"), self.op.total_count) \
                        % (self.op.sender_name,
                           self.op.total_count,
                           self.op.top_dir_basenames[0] if self.op.total_count == 1 else "")

                notification.set_body(body)
                notification.set_icon(Gio.ThemedIcon(name="mail-send-symbolic"))

        Gio.Application.get_default().send_notification(self.op.sender, notification)

    def _notification_response(self, action, variant, op):
        response = variant.unpack()

        if response == "accept":
            op.accept_transfer()
        elif response == "decline":
            op.decline_transfer_request()
        else:
            op.focus()

        app = Gio.Application.get_default()
        app.lookup_action("notification-response").disconnect_by_func(self._notification_response)

class TransferCompleteNotification():
    def __init__(self, op, sender=True):
        self.op = op
        self.sender = sender

        self.send_notification()

    @util._idle
    def send_notification(self):
        if prefs.get_show_notifications():
            notification = Gio.Notification.new(_("Transfer complete"))
            if self.sender:
                body = (_("The transfer to %s has finished successfully") % self.op.receiver_name)
            else:
                body = (_("The transfer from %s has finished successfully") % self.op.sender_name)

            notification.set_body(body)
            notification.set_icon(Gio.ThemedIcon(name="emblem-ok-symbolic"))
            notification.set_default_action("app.notification-response::focus")

            notification.set_priority(Gio.NotificationPriority.NORMAL)

            app = Gio.Application.get_default()
            app.lookup_action("notification-response").connect("activate", self._notification_response, self.op)

            app.get_default().send_notification(self.op.sender, notification)

    def _notification_response(self, action, variant, op):
        op.focus()

        app = Gio.Application.get_default()
        app.lookup_action("notification-response").disconnect_by_func(self._notification_response)

class TransferFailedNotification():
    def __init__(self, op, sender=True):
        self.op = op
        self.sender = sender

        self.send_notification()

    @util._idle
    def send_notification(self):
        if prefs.get_show_notifications():
            notification = Gio.Notification.new(_("Transfer failed"))

            if self.sender:
                body = (_("Something went wrong with the transfer to %s") % self.op.receiver_name)
            else:
                body = (_("Something went wrong with the transfer from %s") % self.op.sender_name)

            notification.set_body(body)
            notification.set_icon(Gio.ThemedIcon(name="dialog-error-symbolic"))
            notification.set_default_action("app.notification-response::focus")

            notification.set_priority(Gio.NotificationPriority.NORMAL)

            app = Gio.Application.get_default()
            app.lookup_action("notification-response").connect("activate", self._notification_response, self.op)

            app.get_default().send_notification(self.op.sender, notification)

    def _notification_response(self, action, variant, op):
        op.focus()

        app = Gio.Application.get_default()
        app.lookup_action("notification-response").disconnect_by_func(self._notification_response)
