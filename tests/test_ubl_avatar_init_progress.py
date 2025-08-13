"""Tests for initialisation progress in SDXL avatar generation."""

import sys
import types

from utils.ubl_avatar_generator import INIT_STEPS, generate_player_avatars_sdxl


def test_init_progress_advances(monkeypatch, tmp_path):
    """Ensure progress callback advances during initialisation."""

    class DummyImage:
        def resize(self, size, resample=None):
            return self

        def save(self, path):
            return None

    # Provide stub modules for heavy dependencies
    pil_module = types.ModuleType("PIL")
    pil_image_module = types.ModuleType("PIL.Image")
    pil_image_module.open = lambda path: DummyImage()
    pil_image_module.LANCZOS = 0
    pil_module.Image = pil_image_module
    monkeypatch.setitem(sys.modules, "PIL", pil_module)
    monkeypatch.setitem(sys.modules, "PIL.Image", pil_image_module)

    class DummyCache:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            return None

        def set(self, *args, **kwargs):
            pass

        def close(self):
            pass

    diskcache_module = types.ModuleType("diskcache")
    diskcache_module.Cache = DummyCache
    monkeypatch.setitem(sys.modules, "diskcache", diskcache_module)

    class DummyPipe:
        @classmethod
        def from_pretrained(cls, *args, **kwargs):
            return cls()

        def to(self, device):
            return self

        def __call__(self, prompt):
            class R:
                images = [DummyImage()]

            return R()

    diffusers_module = types.ModuleType("diffusers")
    diffusers_module.StableDiffusionXLPipeline = DummyPipe
    monkeypatch.setitem(sys.modules, "diffusers", diffusers_module)

    torch_module = types.ModuleType("torch")
    torch_module.cuda = types.SimpleNamespace(is_available=lambda: False)
    torch_module.float16 = "float16"
    monkeypatch.setitem(sys.modules, "torch", torch_module)

    calls = []

    generate_player_avatars_sdxl(
        out_dir=str(tmp_path),
        players={},
        teams=[],
        progress_callback=lambda done, total: calls.append((done, total)),
    )

    assert calls[0] == (0, INIT_STEPS)
    # Final call reflects completed initialisation with no players processed
    assert calls[-1] == (INIT_STEPS, INIT_STEPS)
    assert len(calls) == INIT_STEPS + 1

