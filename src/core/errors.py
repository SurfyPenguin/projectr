"""Errors shared by the application core and its adapters."""

from __future__ import annotations


class FrameSourceError(Exception):
    """A FrameSource could not deliver a readable frame."""
