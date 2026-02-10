"""HTB-like lab integration package for Open edX."""

__all__ = ["HTBLabXBlock"]


def __getattr__(name):
    if name == "HTBLabXBlock":
        from .xblock import HTBLabXBlock

        return HTBLabXBlock
    raise AttributeError(name)
