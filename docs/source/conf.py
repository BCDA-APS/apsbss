# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import pathlib
import sys
import tomllib
from importlib.metadata import version

sys.path.insert(0, str(pathlib.Path().absolute().parent.parent))
import apsbss  # noqa

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

root_path = pathlib.Path(__file__).parent.parent.parent

with open(root_path / "pyproject.toml", "rb") as fp:
    toml = tomllib.load(fp)
metadata = toml["project"]

gh_org = "BCDA-APS"
project = metadata["name"]
copyright = toml["tool"]["copyright"]["copyright"]
author = ", ".join([a["name"] for a in metadata["authors"]])
description = metadata["description"]
rst_prolog = f".. |author| replace:: {author}"
github_url = f"https://github.com/{gh_org}/{project}"

release = version(project)
version = ".".join(release.split(".")[:2])

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = """
    sphinx.ext.autodoc
    sphinx.ext.autosummary
    sphinx.ext.coverage
    sphinx.ext.githubpages
    sphinx.ext.mathjax
    sphinx.ext.todo
    sphinx.ext.viewcode
""".split()

templates_path = ["_templates"]
exclude_patterns = []

today_fmt = "%Y-%m-%d %H:%M"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_theme = "alabaster"
html_theme = "bizstyle"  # ok, looks industrial
html_title = f"{project} {version}"
html_static_path = ['_static']

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# http://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_mock_imports
# TODO: review
autodoc_mock_imports = [
    'h5py',
    'matplotlib',
    'networkx',
    'openpyxl',
    'pyRestTable',
    'snapshot',
    'xarray',
    ]
