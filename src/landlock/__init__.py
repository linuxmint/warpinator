"""Python interface to the Landlock Linux Security Module."""
from typing import Optional

__version__ = "1.0.0.dev4"


class LandlockError(Exception):
    """Generic exception for this module."""


class SyscallError(OSError, LandlockError):
    """Exception raised from a syscall."""

    def __init__(self, *args, reason: Optional[str] = None):
        """Augments an OSError with a "reason".

        This is similar to BaseException.add_note() from Python 3.11.
        """
        self.reason = reason
        super().__init__(*args)

    def __str__(self):
        super_str = super().__str__()
        if self.reason is not None:
            return super_str + f"\nNote: {self.reason}"
        return super_str

    def __repr__(self):
        return (
            f"{self.__class__.__name__}({', '.join(self.args)}, reason={self.reason})"
        )


from landlock.plumbing import FSAccess, landlock_abi_version  # noqa E402
from landlock.porcelain import Ruleset  # noqa E402

__all__ = [
    "FSAccess",
    "landlock_abi_version",
    "LandlockError",
    "Ruleset",
    "SyscallError",
]
