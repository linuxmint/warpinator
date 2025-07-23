"""
Must be included after 'sphinx.ext.autodoc'. Fixes unwanted 'alias of' behavior.
"""

# pylint: disable=import-error
from sphinx.application import Sphinx


def skip_member(app, what, name, obj, skip: bool, options) -> bool:  # type: ignore[no-untyped-def]
    return (
        skip
        or getattr(obj, "__doc__", None) is None
        or getattr(obj, "__private__", False) is True
        or getattr(getattr(obj, "__func__", None), "__private__", False) is True
    )


def setup(app: Sphinx) -> None:
    app.connect("autodoc-skip-member", skip_member)
