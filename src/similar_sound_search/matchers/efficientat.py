"""Lazy optional CPU adapter with native deterministic EfficientAT evaluation frontend."""

import contextlib
import importlib.metadata
import math
import sys

import numpy as np

from ..storage import InputError
from .acoustic import checked, waveform


class EfficientAT:
    dimension = 384
    input_rate = 32000

    def __init__(self, path):
        if not path.is_file():
            raise InputError("EfficientAT weights missing: run explicit matchers acquire")
        try:
            with contextlib.redirect_stdout(sys.stderr):
                import torch
        except ImportError as exc:
            raise InputError(
                "EfficientAT optional CPU dependencies missing; run scripts/setup-models.ps1"
            ) from exc
        if importlib.metadata.version("torch") != "2.6.0+cpu":
            raise InputError("EfficientAT: pinned torch 2.6.0+cpu required")
        from .efficientat_model import MN04

        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        torch.use_deterministic_algorithms(True)
        self.torch = torch
        self.model = MN04()
        # CPU-only, restricted tensor unpickler, exact architecture; no hidden base model.
        self.model.load_state_dict(
            torch.load(path, map_location="cpu", weights_only=True), strict=True
        )
        self.model.eval()
        self.window = torch.hann_window(800, periodic=False)
        self.mel = native_mel(torch)

    def encode(self, samples, rate):
        torch = self.torch
        x = waveform(samples, rate, self.input_rate)
        x = np.pad(x, (0, max(0, 1024 - len(x))))
        with torch.inference_mode():
            x = torch.from_numpy(x.copy())[None, :]
            x = torch.nn.functional.conv1d(x[:, None, :], torch.tensor([[[-0.97, 1.0]]])).squeeze(1)
            power = (
                torch.stft(
                    x,
                    1024,
                    hop_length=320,
                    win_length=800,
                    window=self.window,
                    center=True,
                    pad_mode="reflect",
                    normalized=False,
                    return_complex=True,
                )
                .abs()
                .square()
            )
            mel = ((self.mel @ power + 0.00001).log() + 4.5) / 5
            result = self.model(mel[:, None, :, :])[0].numpy()
        return checked(result, self.dimension)


def native_mel(torch):
    """Kaldi warp=1 triangles, equivalent to TorchAudio 2.6 get_mel_banks.

    Use the public mel equations directly so importing the Windows audio extension
    is unnecessary. Float32 arithmetic and the zero Nyquist bin match native eval.
    """
    delta = 1127.0 * math.log(1.0 + 15000.0 / 700.0) / 129
    index = torch.arange(128).unsqueeze(1)
    left, center, right = index * delta, (index + 1.0) * delta, (index + 2.0) * delta
    frequencies = 32000.0 / 1024 * torch.arange(512)
    mel = (1127.0 * (1.0 + frequencies / 700.0).log()).unsqueeze(0)
    triangles = torch.maximum(
        torch.zeros(1),
        torch.minimum((mel - left) / (center - left), (right - mel) / (right - center)),
    )
    return torch.nn.functional.pad(triangles, (0, 1))
