"""Compatibility shim so `pip install -e` works on older pip/setuptools too.

Real metadata lives in pyproject.toml; this just enables legacy editable installs.
"""

from setuptools import setup

setup()
