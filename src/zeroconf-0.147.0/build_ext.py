"""Build optional cython modules."""

import logging
import os
from distutils.command.build_ext import build_ext
from typing import Any

try:
    from setuptools import Extension
except ImportError:
    from distutils.core import Extension

_LOGGER = logging.getLogger(__name__)

TO_CYTHONIZE = [
    "src/zeroconf/_dns.py",
    "src/zeroconf/_cache.py",
    "src/zeroconf/_history.py",
    "src/zeroconf/_record_update.py",
    "src/zeroconf/_listener.py",
    "src/zeroconf/_protocol/incoming.py",
    "src/zeroconf/_protocol/outgoing.py",
    "src/zeroconf/_handlers/answers.py",
    "src/zeroconf/_handlers/record_manager.py",
    "src/zeroconf/_handlers/multicast_outgoing_queue.py",
    "src/zeroconf/_handlers/query_handler.py",
    "src/zeroconf/_services/__init__.py",
    "src/zeroconf/_services/browser.py",
    "src/zeroconf/_services/info.py",
    "src/zeroconf/_services/registry.py",
    "src/zeroconf/_updates.py",
    "src/zeroconf/_utils/ipaddress.py",
    "src/zeroconf/_utils/time.py",
]

EXTENSIONS = [
    Extension(
        ext.removeprefix("src/").removesuffix(".py").replace("/", "."),
        [ext],
        language="c",
        extra_compile_args=["-O3", "-g0"],
    )
    for ext in TO_CYTHONIZE
]


class BuildExt(build_ext):
    def build_extensions(self) -> None:
        try:
            super().build_extensions()
        except Exception:
            _LOGGER.info("Failed to build cython extensions")


def build(setup_kwargs: Any) -> None:
    if os.environ.get("SKIP_CYTHON"):
        return
    try:
        from Cython.Build import cythonize

        setup_kwargs.update(
            {
                "ext_modules": cythonize(
                    EXTENSIONS,
                    compiler_directives={"language_level": "3"},  # Python 3
                ),
                "cmdclass": {"build_ext": BuildExt},
            }
        )
        setup_kwargs["exclude_package_data"] = {pkg: ["*.c"] for pkg in setup_kwargs["packages"]}
    except Exception:
        if os.environ.get("REQUIRE_CYTHON"):
            raise
