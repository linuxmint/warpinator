"""Landlock constants and syscalls."""
import ctypes
import enum
import errno
import functools
import os
import platform
from typing import Callable, Optional, Tuple, TypeVar

import _ctypes

from landlock import SyscallError

CREATE_RULESET_VERSION = 1 << 0

SYSCALL_CREATE_RULESET = 444
SYSCALL_ADD_RULE = 445
SYSCALL_RESTRICT_SELF = 446
PR_SET_NO_NEW_PRIVS = 38

T = TypeVar("T")


class FSAccess(enum.IntFlag):
    """Flags representing types of file system actions.

    These flags enable one to restrict a sandboxed process
    to a set of actions on files and directories.

    Files or directories opened before the sandboxing
    are not subject to these restrictions.
    """

    # A file can only receive these access rights:
    EXECUTE = 1 << 0
    """Execute a file."""
    WRITE_FILE = 1 << 1
    """Open a file with write access."""
    READ_FILE = 1 << 2
    """Open a file with read access."""

    # A directory can receive access rights related to files or directories.
    # The following access right is applied to the directory itself,
    # and the directories beneath it:
    READ_DIR = 1 << 3
    """Open a directory or list its content."""

    # However, the following access rights only apply to the content of a directory,
    # not the directory itself:
    REMOVE_DIR = 1 << 4
    """Remove an empty directory or rename one."""
    REMOVE_FILE = 1 << 5
    """Unlink (or rename) a file."""
    MAKE_CHAR = 1 << 6
    """Create (or rename or link) a character device."""
    MAKE_DIR = 1 << 7
    """Create (or rename) a directory."""
    MAKE_REG = 1 << 8
    """Create (or rename or link) a regular file."""
    MAKE_SOCK = 1 << 9
    """Create (or rename or link) a UNIX domain socket."""
    MAKE_FIFO = 1 << 10
    """Create (or rename or link) a named pipe."""
    MAKE_BLOCK = 1 << 11
    """Create (or rename or link) a block device."""
    MAKE_SYM = 1 << 12
    """Create (or rename or link) a symbolic link."""
    REFER = 1 << 13
    """Link or rename a file from or to a different directory.

    I.e. reparent a file hierarchy.

    Only available if the ABI version >= 2.
    """

    @classmethod
    def all(cls):
        return cls.all_file() | cls.all_dir()

    @classmethod
    def all_file(cls):
        return cls.EXECUTE | cls.WRITE_FILE | cls.READ_FILE

    @classmethod
    def all_dir(cls):
        flags = (
            cls.READ_DIR
            | cls.REMOVE_DIR
            | cls.REMOVE_FILE
            | cls.MAKE_CHAR
            | cls.MAKE_DIR
            | cls.MAKE_REG
            | cls.MAKE_SOCK
            | cls.MAKE_FIFO
            | cls.MAKE_BLOCK
            | cls.MAKE_SYM
        )
        # REFER only available in version 2
        if landlock_abi_version() >= 2:
            flags |= cls.REFER
        return flags


class RulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class PathBeneathAttr(ctypes.Structure):
    _fields_ = [
        ("allowed_access", ctypes.c_uint64),
        ("parent_fd", ctypes.c_int32),
    ]


def find_generic_reason_from_platform() -> Optional[str]:
    # check OS
    system = platform.system()
    if system != "Linux":
        return (
            f"Landlock is a only available on Linux,"
            f" it looks like you're running {system}"
        )

    # check kernel version
    kernel_version = platform.release()
    kernel_version_tuple = tuple(map(int, kernel_version.split("-")[0].split(".")))
    if kernel_version_tuple < (5, 13):
        return (
            f"Landlock is only available in kernel 5.13 or newer,"
            f" it looks like you're running {kernel_version}"
        )

    return None


def find_generic_reason_from_errno(err: int) -> Optional[str]:
    errno_to_reason = {
        errno.ENOSYS: "Cannot find Landlock syscalls - perhaps the kernel was not built"
        " with 'CONFIG_SECURITY_LANDLOCK=y'",
        errno.EOPNOTSUPP: "Landlock has been disabled at boot time."
        " The CONFIG_LSM configuration item should list 'landlock',"
        " or, 'lsm=landlock' needs to be added the kernel's"
        " command-line arguments (usually via your bootloader).",
    }
    return errno_to_reason.get(err)


def syscall_errcheck(
    result: T, func: _ctypes.CFuncPtr, arguments: Tuple, reason: Optional[str] = None
) -> T:
    err = ctypes.get_errno()

    # return the result if there was no error
    if err == 0:
        return result

    # otherwise raise a SyscallError exception
    name = getattr(func, "name", func.__name__)
    reason = (
        find_generic_reason_from_platform()
        or find_generic_reason_from_errno(err)
        or reason
    )
    raise SyscallError(
        err,
        os.strerror(err),
        f"Error calling {name}: {func.__name__}{arguments} = {result}",
        reason=reason,
    )


def create_ruleset_errcheck(result: T, func: _ctypes.CFuncPtr, arguments: Tuple) -> T:
    errno_to_reason = {
        errno.EINVAL: "Unknown 'flags', or unknown access, or too small 'size'",
        errno.E2BIG: "'attr' or 'size' inconsistencies",
        errno.EFAULT: "'attr' or 'size' inconsistencies",
        errno.ENOMSG: "Empty 'landlock_ruleset_attr.handled_access_fs'",
    }
    return syscall_errcheck(
        result, func, arguments, errno_to_reason.get(ctypes.get_errno())
    )


def add_rule_errcheck(result: T, func: _ctypes.CFuncPtr, arguments: Tuple) -> T:
    errno_to_reason = {
        errno.EINVAL: "'flags' is not 0, or inconsistent access in the rule"
        " (i.e. 'landlock_path_beneath_attr.allowed_access'"
        " is not a subset of the ruleset handled accesses)",
        errno.ENOMSG: "Empty accesses"
        " (e.g. 'landlock_path_beneath_attr.allowed_access')",
        errno.EBADF: "'ruleset_fd' is not a file descriptor for the current thread,"
        " or a member of 'rule_attr' is not a file descriptor as expected",
        errno.EBADFD: "'ruleset_fd' is not a ruleset file descriptor,"
        " or a member of 'rule_attr' is not the expected file descriptor type",
        errno.EPERM: "'ruleset_fd' has no write access to the underlying ruleset",
        errno.EFAULT: "'rule_attr' inconsistency",
    }
    return syscall_errcheck(
        result, func, arguments, errno_to_reason.get(ctypes.get_errno())
    )


def restrict_self_errcheck(result: T, func: _ctypes.CFuncPtr, arguments: Tuple) -> T:
    errno_to_reason = {
        errno.EINVAL: "'flags' is not 0",
        errno.EBADF: "'ruleset_fd' is not a file descriptor for the current thread",
        errno.EBADFD: "'ruleset_fd' is not a ruleset file descriptor",
        errno.EPERM: "'ruleset_fd' has no read access to the underlying ruleset,"
        " or the current thread is not running with no_new_privs,"
        " or it doesn’t have 'CAP_SYS_ADMIN' in its namespace",
        errno.E2BIG: "The maximum number of stacked rulesets (16)"
        " has been reached for the current thread",
    }
    return syscall_errcheck(
        result, func, arguments, errno_to_reason.get(ctypes.get_errno())
    )


@functools.lru_cache(1)
def get_libc() -> ctypes.CDLL:
    try:
        return ctypes.CDLL(None, use_errno=True)
    except TypeError as e:
        if platform.system() == "Windows":
            # on Windows we get a TypeError using name=None
            raise SyscallError(reason=find_generic_reason_from_platform()) from e
        raise


@functools.lru_cache(1)
def get_create_ruleset() -> Callable:
    libc = get_libc()

    create_ruleset = functools.partial(libc["syscall"], SYSCALL_CREATE_RULESET)
    create_ruleset.func.name = "landlock_create_ruleset"
    create_ruleset.func.argtypes = (
        ctypes.c_long,
        ctypes.POINTER(RulesetAttr),
        ctypes.c_size_t,
        ctypes.c_uint32,
    )
    create_ruleset.func.errcheck = create_ruleset_errcheck
    create_ruleset.func.restype = ctypes.c_long

    return create_ruleset


@functools.lru_cache(1)
def get_add_rule() -> Callable:
    libc = get_libc()

    add_rule = functools.partial(libc["syscall"], SYSCALL_ADD_RULE)
    add_rule.func.name = "landlock_add_rule"
    add_rule.func.argtypes = (
        ctypes.c_long,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.POINTER(PathBeneathAttr),
        ctypes.c_uint32,
    )
    add_rule.func.errcheck = add_rule_errcheck
    add_rule.func.restype = ctypes.c_long

    return add_rule


@functools.lru_cache(1)
def get_restrict_self() -> Callable:
    libc = get_libc()

    restrict_self = functools.partial(libc["syscall"], SYSCALL_RESTRICT_SELF)
    restrict_self.func.name = "landlock_restrict_self"
    restrict_self.func.argtypes = (
        ctypes.c_long,
        ctypes.c_int,
        ctypes.c_uint32,
    )
    restrict_self.func.errcheck = restrict_self_errcheck
    restrict_self.func.restype = ctypes.c_long

    return restrict_self


@functools.lru_cache(1)
def get_prctl() -> Callable:
    # https://man7.org/linux/man-pages/man2/prctl.2.html
    libc = get_libc()

    prctl = libc.prctl
    prctl.name = "prctl"
    prctl.argtypes = (
        ctypes.c_int,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
    )
    prctl.errcheck = syscall_errcheck
    prctl.restype = ctypes.c_int

    return libc.prctl


@functools.lru_cache(1)
def landlock_abi_version() -> int:
    return get_create_ruleset()(None, 0, CREATE_RULESET_VERSION)
