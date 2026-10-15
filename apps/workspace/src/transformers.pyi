"""Typing-only surface of the optional pinned CW-006 Transformers Whisper loader.

Narrow contract only: real versions and local snapshot identity remain runtime-validated.
"""

__version__: str

class _Tensor:
    def to(self, device: str) -> _Tensor: ...

class WhisperProcessor:
    @classmethod
    def from_pretrained(
        cls, path: str, *, local_files_only: bool, trust_remote_code: bool
    ) -> WhisperProcessor: ...
    def __call__(
        self, waveform: list[float], *, sampling_rate: int, return_tensors: str
    ) -> dict[str, _Tensor]: ...
    def batch_decode(self, generated: object, *, skip_special_tokens: bool) -> list[str]: ...

class WhisperForConditionalGeneration:
    @classmethod
    def from_pretrained(
        cls, path: str, *, local_files_only: bool, trust_remote_code: bool, torch_dtype: object
    ) -> WhisperForConditionalGeneration: ...
    def to(self, device: str) -> object: ...
    def eval(self) -> object: ...
    def generate(self, features: _Tensor) -> object: ...
