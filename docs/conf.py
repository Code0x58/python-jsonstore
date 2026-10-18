import os
from importlib import metadata

project = "jsonstore"
author = "Oliver Bristow"
copyright = "2016, Oliver Bristow"
release = metadata.version("python-jsonstore")
version = release

extensions = ["sphinx.ext.autodoc", "sphinx.ext.intersphinx"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "sphinx_rtd_theme"
html_title = "jsonstore"
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "")
html_theme_options = {"collapse_navigation": False, "navigation_depth": 3}

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
