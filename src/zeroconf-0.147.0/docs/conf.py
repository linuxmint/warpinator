# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import sys
from collections.abc import Sequence
from pathlib import Path

# If your extensions are in another directory, add it here. If the directory
# is relative to the documentation root, use Path.absolute to make it absolute.
sys.path.append(str(Path(__file__).parent / "_ext"))
sys.path.insert(0, str(Path(__file__).parent.parent))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "python-zeroconf"
project_copyright = "python-zeroconf authors"
author = "python-zeroconf authors"

try:
    import zeroconf

    # The short X.Y version.
    version = zeroconf.__version__
    # The full version, including alpha/beta/rc tags.
    release = version
except ImportError:
    version = ""
    release = ""

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.todo",  # Allow todo comments.
    "sphinx.ext.viewcode",  # Link to source code.
    "sphinx.ext.autodoc",
    "zeroconfautodocfix",  # Must be after "sphinx.ext.autodoc"
    "sphinx.ext.intersphinx",
    "sphinx.ext.coverage",  # Enable the overage report.
    "sphinx.ext.duration",  # Show build duration at the end.
    "sphinx_rtd_theme",  # Required for theme.
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Custom sidebar templates, maps document names to template names.
html_sidebars: dict[str, Sequence[str]] = {
    "index": ("sidebar.html", "sourcelink.html", "searchbox.html"),
    "**": ("localtoc.html", "relations.html", "sourcelink.html", "searchbox.html"),
}

# -- Options for RTD theme ---------------------------------------------------
# https://sphinx-rtd-theme.readthedocs.io/en/stable/configuring.html

# html_theme_options = {}

# -- Options for HTML help output --------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-help-output

htmlhelp_basename = "zeroconfdoc"

# -- Options for intersphinx extension ---------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html#configuration

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
