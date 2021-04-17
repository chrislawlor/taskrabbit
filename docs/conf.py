# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

PATH = os.path.dirname(os.path.abspath("."))
print("PATH=%s" % PATH)
sys.path.insert(0, PATH)


# -- Project information -----------------------------------------------------

project = "Taskrabbit"
copyright = "2020, Chris Lawlor"
author = "Chris Lawlor"

# The full version, including alpha/beta/rc tags
release = "0.1a"


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.githubpages",
    "sphinx.ext.graphviz",
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "alabaster"

html_theme_options = {
    "fixed_sidebar": True,
    "github_user": "chrislawlor",
    "github_repo": "taskrabbit",
    "github_banner": True,
    "github_button": True,
    "github_count": False,
    "logo": "taskrabbit.png",
    "logo_name": True,
    "page_width": "1030px",
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

html_sidebars = {
    "**": [
        "about.html",
        "navigation.html",
        "relations.html",
        "searchbox.html",
        # 'donate.html',
    ]
}

extra_nav_links = {
    "Logo by eucalyp": "https://creativemarket.com/eucalyp",
}
