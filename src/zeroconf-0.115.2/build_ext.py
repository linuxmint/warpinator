"""Build optional cython modules."""

import os
from distutils.command.build_ext import build_ext
from typing import Any


class BuildExt(build_ext):
    def build_extensions(self) -> None:
        try:
            super().build_extensions()
        except Exception:
            pass


def build(setup_kwargs: Any) -> None:
    if os.environ.get("SKIP_CYTHON", False):
        return
    try:
        from Cython.Build import cythonize

        setup_kwargs.update(
            dict(
                ext_modules=cythonize(
                    [
                        "src/zeroconf/_dns.py",
                        "src/zeroconf/_cache.py",
                        "src/zeroconf/_history.py",
                        "src/zeroconf/_listener.py",
                        "src/zeroconf/_protocol/incoming.py",
                        "src/zeroconf/_protocol/outgoing.py",
                        "src/zeroconf/_handlers/answers.py",
                        "src/zeroconf/_handlers/record_manager.py",
                        "src/zeroconf/_handlers/multicast_outgoing_queue.py",
                        "src/zeroconf/_handlers/query_handler.py",
                        "src/zeroconf/_services/browser.py",
                        "src/zeroconf/_services/info.py",
                        "src/zeroconf/_services/registry.py",
                        "src/zeroconf/_updates.py",
                        "src/zeroconf/_utils/time.py",
                    ],
                    compiler_directives={"language_level": "3"},  # Python 3
                ),
                cmdclass=dict(build_ext=BuildExt),
            )
        )
    except Exception:
        if os.environ.get("REQUIRE_CYTHON"):
            raise
        pass
