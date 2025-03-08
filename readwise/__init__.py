"""Readwise API client for Python."""

from readwise.api import ReadwiseReader
from readwise.version import __version__

__all__: list[str] = ["ReadwiseReader", "__version__"]
