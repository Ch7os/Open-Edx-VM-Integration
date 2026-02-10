"""HTB-like lab integration package for Open edX."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .xblock import HTBLabXBlock

__all__ = ["HTBLabXBlock"]


def __getattr__(name):
    if name == "HTBLabXBlock":
        from .xblock import HTBLabXBlock

        return HTBLabXBlock
    raise AttributeError(name)
