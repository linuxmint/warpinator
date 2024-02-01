#!/usr/bin/python3

import sys
import os
import argparse
import subprocess
from pathlib import Path

from gi.repository import Gio, GLib

# Don't let warpinator run as root
if os.getuid() == 0:
    print("Warpinator should not be run as root. Please run it in user mode.")
    sys.exit(1)

try:
    src = os.environ["WARPINATOR_PATH"]
except KeyError:
    print("WARPINATOR_PATH missing from environment, exiting")
    exit(1)

sys.path.insert(0, src)
warpinator_path = os.path.join(src, "warpinator.py")
GLib.setenv("PYTHONPATH", ";".join(sys.path), True)

mode_help="""
Modes:

Warpinator can isolate the incoming folder so that files being received will be unable
to 'escape' (for instance, using relative symbolic links).

landlock: only available with kernel >= 5.13, and only if enabled. Warpinator will run like normal,
but individual transfers will be locked inside the incoming folder. You can see if it's enabled on your
system by running `cat /sys/kernel/security/lsm | grep landlock`.

bubblewrap: requires the bwrap command. This is usually in a package called 'bubblewrap' but that may
vary. Warpinator will run in a sandbox (similar to Flatpaks). Only the incoming folder will be writable.
Other locations will be read-only, including the user's home. Changing the incoming folder location will
require a program restart. This mode is not available in the Flatpak version

legacy: Warpinator will run without any sort of protection, though some effort will still be made to
detect relative links.

Warpinator ordinarily will choose which mode to use automatically, depending on what's available. It
will always prefer landlock over bubblewrap, with legacy as a last resort.

Flatpak users: If you can't use Landlock, you'll have to manage hardening yourself by adjusting runtime
permissions. See https://github.com/linuxmint/warp/blob/master/README.md#folder-isolation for information
on how to accomplish this.

"""

parser = argparse.ArgumentParser(description="Send and Receive Files across the Network",
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=mode_help)
parser.add_argument("-d", "--debug", help="Print debugging information.",
                    action="store_true")
parser.add_argument("-a", "--autostart", help="Exit if (dconf) org.x.warpinator.preferences 'autostart' is false.",
                    action="store_true")
parser.add_argument("-m", "--mode", help="Specify a sandbox method instead of letting Warpinator decide.",
                    action="store", choices=("legacy", "bubblewrap", "landlock"))
args = parser.parse_args()

if args.debug:
    os.environ["WARPINATOR_DEBUG"] = "1"

# Secure mode enforcement
import prefs
enforcer = prefs.SecureModePrefsBlocker()

if args.autostart:
    if not prefs.get_should_autostart():
        sys.exit(0)
del sys.argv[1:]

###########################
# See what mode we'll run in
import config

supported_modes = ["legacy"]

if not config.FLATPAK_BUILD:
    if GLib.find_program_in_path("bwrap"):
        supported_modes.insert(0, "bubblewrap")
    else:
        if args.debug:
            print("Bubblewrap (bwrap) not found")
try:
    import landlock
    landlock.landlock_abi_version()
    supported_modes.insert(0, "landlock")
except ModuleNotFoundError as e:
    if args.debug:
        print("Landlock support unavailable - landlock python module not found (https://github.com/Edward-Knight/landlock)")
except landlock.SyscallError as e:
    if args.debug:
        print("Landlock support unavailable: %s" % str(e))

if args.mode:
    if args.mode in supported_modes:
        sandbox_mode = args.mode
    else:
        print("'%s' mode is not available, see `warpinator --help` for more information" % args.mode)
        sys.exit(1)
else:
    sandbox_mode = supported_modes[0]

os.environ["WARPINATOR_SANDBOX_MODE"] = sandbox_mode
############################

############################
# Run Warpinator

# Keep using this process for landlock or legacy modes.
if sandbox_mode in ("legacy, landlock"):
    if sandbox_mode == "landlock":
        print("Using landlock for incoming file isolation")
    else:
        print("Running without incoming file isolation")

    try:
        import warpinator
        sys.exit(warpinator.main())
    except Exception as e:
        print(e)
        sys.exit(1)
# Otherwise bubblewrap will be a new process.
else:
    print("Using bubblewrap for incoming file isolation. Write access for the application will be limited to the save directory only.")
    import misc

    try:
        rundir = os.environ["XDG_RUNTIME_DIR"]
    except KeyError:
        rundir = "/run/user/%d" % os.getuid()

    launch_args = []

    launch_args += ["/usr/bin/bwrap"]
    launch_args += ["--ro-bind",         "/",                                               "/"]
    launch_args += ["--dev",             "/dev"]
    launch_args += ["--bind",            rundir + "/dconf",                                 rundir + "/dconf"]
    launch_args += ["--bind-try",        rundir + "/gvfsd",                                 rundir + "/gvfsd"]
    launch_args += ["--tmpfs",           "/tmp"]
    # The following two items aren't necessary if org.freedesktop.FileManager1 works properly - in that case,
    # the file manager is launched outside of the sandbox. If that fails, and the file manager isn't already running,
    # it will spawn inside the sandbox and be restricted the same as Warpinator.
    # For thumbnails mainly - they're fairly small, and nemo complains if a cache isn't there and writable
    cache = GLib.get_user_cache_dir()
    launch_args += ["--bind-try",        cache,                                             cache]
    # caja requires ~/.config/caja be r/w or else it won't start.
    caja_conf = os.path.join(GLib.get_user_config_dir(), "caja")
    launch_args += ["--bind-try",        caja_conf,                                         caja_conf]
    # Use a placeholder for the save location. This will be resolved inside the run loop below.
    launch_args += ["--bind",            "#save_path#",                                     "#save_path#"]

    launch_args += ["--die-with-parent"]

    # launch_args += ["/bin/sh"]
    launch_args += ["/usr/bin/python3",      warpinator_path]

    ret = 0

    while True:
        # We wait to set the actual save path until inside the restart loop, so it can be updated
        # and warpinator re-launched.
        real_args = [arg.replace("#save_path#", prefs.get_save_path()) for arg in launch_args]
        if args.debug:
            print()
            print(" ".join(real_args[:-2]).replace("--", "\n--"))
            print(" ".join(real_args[-2:]))

        try:
            ret = subprocess.run(real_args).returncode

            # Special code for restarting so the save path can be updated..
            if ret != misc.EXIT_CODE_RESTART_BWRAP:
                break
        except subprocess.CalledProcessError as e:
            print("Error launching warpinator: %s", str(e))
            ret = e.returncode
            break
        except KeyboardInterrupt:
            break
    sys.exit(ret)

