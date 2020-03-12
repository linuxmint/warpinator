TEST_REMOTES = [
["Han Solo", "test1", "nerfherder69", "falcon-mint", "100.100.100.1", "42000", "online", 0],
["Luke Skywalker", "test2", "womprat", "mintbox", "100.100.100.3", "42000", "online", 0],
["Darth Vader", "test3", "darkside", "darths-pc", "100.100.100.5", "42000", "offline", 0],
["", "test4", "", "sciencepc", "100.100.100.7", "42000", "unreachable", 0],
["Buzz Lightyear", "test11", "zergsux", "starpatrol-1", "100.100.100.7", "42000", "unreachable", 0],
["Jim Kirk", "test5", "khansucks", "enterprise", "100.100.100.9", "42000", "connecting", 0],
["Montgomery Scott", "test6", "my.bairns", "engineering-station", "100.100.100.11", "42000", "offline", 0],
["Hikaru Sulu", "test7", "tiny", "helm-console", "100.100.100.13", "42000", "new_op", 1],
["Jean Luc Picard", "test9", "locutus", "borg-cube", "100.100.100.17", "42000", "new_op", 3],
]

from gi.repository import GLib
import machines
import ops
from util import RemoteStatus

def add_simulated_widgets(app):
    local_machine = app.server

    for entry in TEST_REMOTES:
        display_name, name, user_name, hostname, ip, port, status, num_ops = entry
        machine = machines.RemoteMachine(name, hostname, ip, port, local_machine.service_name)

        local_machine.remote_machines[name] = machine
        app.window.add_remote_button(machine, simulated=True)

        if status == "online":
            machine.display_name = display_name
            machine.user_name = user_name
            machine.emit("machine-info-changed")
            machine.set_remote_status(RemoteStatus.ONLINE)
        elif status == "offline":
            machine.display_name = display_name
            machine.user_name = user_name
            machine.emit("machine-info-changed")
            machine.set_remote_status(RemoteStatus.OFFLINE)
        elif status == "unreachable":
            machine.display_name = display_name
            machine.user_name = user_name
            machine.emit("machine-info-changed")
            machine.set_remote_status(RemoteStatus.UNREACHABLE)
        elif status == "connecting":
            machine.set_remote_status(RemoteStatus.INIT_CONNECTING)
        elif status == "new_op":
            machine.display_name = display_name
            machine.user_name = user_name
            machine.set_remote_status(RemoteStatus.ONLINE)
            machine.emit("machine-info-changed")
            for i in range(num_ops):
                op = ops.ReceiveOp(name)
                op.receiver_name = GLib.get_real_name()
                GLib.timeout_add_seconds(2, emit_new_op, (machine, op))

def emit_new_op(data):
    machine, op = data
    machine.emit("new-incoming-op", op)
    return False

