import hashlib
import pytest

pytest.importorskip("PIL")

from images.auto_logo import TeamSpec, generate_logo


def test_logo_determinism_same_mascot():
    spec1 = TeamSpec(location="Test City", mascot="Cobras", template="auto")
    spec2 = TeamSpec(location="Test City", mascot="Cobras", template="auto")
    img1 = generate_logo(spec1, size=64)
    img2 = generate_logo(spec2, size=64)
    h1 = hashlib.sha256(img1.tobytes()).hexdigest()
    h2 = hashlib.sha256(img2.tobytes()).hexdigest()
    assert h1 == h2
