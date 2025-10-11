import pytest

np = pytest.importorskip("numpy")

from utils.avatar_generator import _recolor_by_hex


def test_recolor_preserves_alpha():
    img = np.zeros((2, 2, 4), dtype=np.uint8)
    img[:, :, :3] = 0
    img[:, :, 3] = 255
    recolored = _recolor_by_hex(img, "#000000", "#ffffff")
    assert recolored.shape == (2, 2, 4)
    assert np.all(recolored[:, :, 3] == 255)
