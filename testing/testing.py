import random

from gi.repository import GLib, Gio
import machines
import ops
import util
import transfers
from util import RemoteStatus, OpStatus, FileType


TEST_REMOTES = [
# display_name,dscvry_name,user_name,  hostname,       ip address,   port,    status,  num_ops
["Han Solo", "test1", "nerfherder69", "falcon-mint", "100.100.100.1", "42000", RemoteStatus.ONLINE, 0],
["Luke Skywalker", "test2", "womprat", "mintbox", "100.100.100.3", "42000", RemoteStatus.ONLINE, 0],
["Darth Vader", "test3", "darkside", "darths-pc", "100.100.100.5", "42000", RemoteStatus.OFFLINE, 0],
["", "test4", "", "sciencepc", "100.100.100.7", "42000", RemoteStatus.UNREACHABLE, 0],
["Buzz Lightyear", "test11", "zergsux", "starpatrol-1", "100.100.100.7", "42000", RemoteStatus.UNREACHABLE, 0],
["Jim Kirk", "test5", "khansucks", "enterprise", "100.100.100.9", "42000", RemoteStatus.INIT_CONNECTING, 0],
["Montgomery Scott", "test6", "my.bairns", "engineering-station", "100.100.100.11", "42000", RemoteStatus.OFFLINE, 0],
["Hikaru Sulu", "test7", "tiny", "helm-console", "100.100.100.13", "42000", RemoteStatus.ONLINE, 0],
["Jean Luc Picard", "test9", "locutus", "borg-cube", "100.100.100.17", "42000", RemoteStatus.ONLINE, 0],
]

TEST_OPS = [
#type, "sender","status", timestamp, size, count,sender_disp_name, receiver_disp_name, name_if_single, special_condition
["send", "test2", "test1", OpStatus.CALCULATING, 108, 2000000, 5, "Luke Skywalker", "Han Solo", None, None],
["receive", "test3", "test2", OpStatus.WAITING_PERMISSION, 102, 5000000, 1, "Darth Vader", "Luke Skywalker", "home-movies.mpg", None],
["receive", "test3", "test2", OpStatus.WAITING_PERMISSION, 102444, 5000000, 1, "Montgomery Scott", "Luke Skywalker", "engine-care.mpg", "nospace"],
["receive", "test3", "test2", OpStatus.WAITING_PERMISSION, 1024494, 5000000, 1, "Jim Kirk", "Luke Skywalker", "pickup_lines.txt", "overwrite"],
["send", "test2", "test11", OpStatus.WAITING_PERMISSION, 1002, 50000000, 5, "Luke Skywalker", "Buzz Lightyear", None, None],
["receive", "test1", "test2", OpStatus.CANCELLED_PERMISSION_BY_RECEIVER, 103, 2000000, 5, "Han Solo", "Luke Skywalker", None, None],
["receive", "test1", "test2", OpStatus.CANCELLED_PERMISSION_BY_SENDER, 1030, 2000000, 5, "Han Solo", "Luke Skywalker", None, None],
["send", "test2", "test1", OpStatus.CANCELLED_PERMISSION_BY_SENDER, 100, 2000000, 5, "Luke Skywalker", "Han Solo", None, None],
["send", "test2", "test1", OpStatus.CANCELLED_PERMISSION_BY_RECEIVER, 1001, 2000000, 5, "Luke Skywalker", "Han Solo", None, None],
["send", "test2", "test7", OpStatus.FILE_NOT_FOUND, 1005, 50000000, 5, "Luke Skywalker", "Hikaru Sulu", None, None],
["receive", "test9", "test2", OpStatus.TRANSFERRING, 1040, 100000000, 20, "Jean Luc Picard", "Luke Skywalker", None, None],
["send", "test9", "test2", OpStatus.TRANSFERRING, 10403, 100000000, 20, "Luke Skywalker", "Dark Vader", None, None],
["receive", "test11", "test2", OpStatus.STOPPED_BY_RECEIVER, 1050, 200000000, 1, "Buzz Lightyear", "Luke Skywalker", "flying-tips.pdf", None],
["send", "test2", "test1", OpStatus.STOPPED_BY_SENDER, 1003, 50000000, 5, "Luke Skywalker", "Han Solo", None, None],
["send", "test2", "test1", OpStatus.STOPPED_BY_RECEIVER, 10113, 50000000, 5, "Luke Skywalker", "Han Solo", None, None],
["receive", "test11", "test2", OpStatus.STOPPED_BY_SENDER, 105, 200000000, 1, "Buzz Lightyear", "Luke Skywalker", "baby-yoda.jpg", None],
["receive", "test7", "test2", OpStatus.FAILED, 106, 1000, 2, "Hikaru Sulu", "Luke Skywalker", None, None],
["send", "test2", "test11", OpStatus.FAILED, 1004, 50000000, 5, "Luke Skywalker", "Buzz Lightyear", None, None],
["receive", "test1", "test2", OpStatus.FINISHED, 107, 200000, 5, "Han Solo", "Luke Skywalker", None, None],
["send", "test2", "test3", OpStatus.FINISHED, 1006, 50000000, 1, "Luke Skywalker", "Darth Vader", "kittens.mpg", None],
]

def add_simulated_widgets(app):
    local_machine = app.server

    for entry in TEST_REMOTES:
        display_name, name, user_name, hostname, ip, port, status, num_ops = entry
        machine = machines.RemoteMachine(name, hostname, ip, port, local_machine.service_name)

        local_machine.remote_machines[name] = machine
        app.window.add_remote_button(machine, simulated=True)

        if status == RemoteStatus.ONLINE:
            machine.display_name = display_name
            machine.user_name = user_name
            machine.emit("machine-info-changed")
            machine.set_remote_status(RemoteStatus.ONLINE)

            if name == "test2":
                add_ops(machine)

        elif status == RemoteStatus.OFFLINE:
            machine.display_name = display_name
            machine.user_name = user_name
            machine.emit("machine-info-changed")
            machine.set_remote_status(RemoteStatus.OFFLINE)
        elif status == RemoteStatus.UNREACHABLE:
            machine.display_name = display_name
            machine.user_name = user_name
            machine.emit("machine-info-changed")
            machine.set_remote_status(RemoteStatus.UNREACHABLE)
        elif status == RemoteStatus.INIT_CONNECTING:
            machine.set_remote_status(RemoteStatus.INIT_CONNECTING)
            machine.emit("machine-info-changed")
        elif status == "new_op":
            machine.display_name = display_name
            machine.user_name = user_name
            machine.set_remote_status(RemoteStatus.ONLINE)
            machine.emit("machine-info-changed")
            for i in range(num_ops):
                op = ops.ReceiveOp(name)
                op.receiver_name = GLib.get_real_name()
                # GLib.timeout_add_seconds(2, emit_new_op, (machine, op))

def add_ops(machine):
    TEST_OPS.reverse()
    for entry in TEST_OPS:
        op_type, sender, receiver, status, time, size, count, sender_disp_name, receiver_disp_name, name_if_single, special_condition = entry

        if op_type == "send":
            op = ops.SendOp(sender=sender, receiver=receiver, receiver_name=receiver_disp_name, uris=[])
            machine.add_op(op)
            f = transfers.File("dummy", "fixme", "fixme", 50, FileType.REGULAR, None)

            op.top_dir_basenames = ["foo", "bar"]
            op.resolved_files = [f]
            op.total_size = size
            op.total_count = count
            op.name_if_single = name_if_single
            op.mime_if_single, uncertainty = Gio.content_type_guess (op.name_if_single, None)

            if status != OpStatus.CALCULATING:
                op.update_ui_info(True)
            idle_set_op_status((op, status))

        elif op_type == "receive":
            op = ops.ReceiveOp(sender=sender)
            op.start_time = GLib.get_monotonic_time()
            op.receiver = receiver
            op.sender_name = sender_disp_name
            op.receiver_name = receiver_disp_name
            op.total_size = size
            op.top_dir_basenames = ["foo", "bar"]
            op.total_count = count
            op.name_if_single = name_if_single
            op.mime_if_single, uncertainty = Gio.content_type_guess (op.name_if_single, None)
            machine.add_op(op)

            op.prepare_receive_info()
            if special_condition == "overwrite":
                op.existing = True
            elif special_condition == "nospace":
                op.have_space = False
            idle_set_op_status((op, status))


@util._idle
def idle_set_op_status(op_and_status):
    op, status = op_and_status
    op.set_status(status)

    if status == OpStatus.TRANSFERRING:
        progress = transfers.Progress(progress=random.random(),
                                      time_left_sec=int(random.random() * 7890),
                                      bytes_per_sec=int(random.random() * 15000000))
        op.progress_report(progress)


def emit_new_op(data):
    machine, op = data
    machine.emit("new-incoming-op", op)
    return False

