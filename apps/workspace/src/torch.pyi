"""Typing-only surface for the pinned optional CW-006 torch runtime.

No executable module is shipped; the workspace wheel packages medscale_workspace only.
"""

__version__: str
float32: object

class _NoGrad:
    def __enter__(self) -> object: ...
    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> bool | None: ...

def no_grad() -> _NoGrad: ...
