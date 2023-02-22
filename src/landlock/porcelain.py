import ctypes
import dataclasses
import os
from typing import Optional

from landlock import LandlockError
from landlock.plumbing import (
    PR_SET_NO_NEW_PRIVS,
    FSAccess,
    PathBeneathAttr,
    RulesetAttr,
    get_add_rule,
    get_create_ruleset,
    get_prctl,
    get_restrict_self,
)


@dataclasses.dataclass(frozen=True)
class Ruleset:
    restrict_rules: FSAccess = dataclasses.field(default_factory=FSAccess.all)
    _fd: int = dataclasses.field(init=False)

    def __post_init__(self):
        ruleset_attr = RulesetAttr(self.restrict_rules)
        fd = get_create_ruleset()(
            ctypes.byref(ruleset_attr),
            ctypes.sizeof(ruleset_attr),
            0,
        )
        object.__setattr__(self, "_fd", fd)

    def allow(self, *paths, rules: Optional[FSAccess] = None):
        if rules is None:
            rules = self.restrict_rules

        for path in paths:
            fd = os.open(path, flags=os.O_PATH)
            try:
                rule_attr = PathBeneathAttr(rules, fd)
                get_add_rule()(self._fd, 1, ctypes.byref(rule_attr), 0)
            finally:
                os.close(fd)

    def apply(self):
        # restrict thread from gaining privileges
        try:
            prctl = get_prctl()
        except Exception as e:
            raise LandlockError("Cannot find prctl libc function") from e
        prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)

        # turn on Landlock restrictions
        get_restrict_self()(self._fd, 0)
