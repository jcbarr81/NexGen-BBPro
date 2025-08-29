import sys
import types

pil_stub = types.ModuleType("PIL")
pil_stub.Image = object
sys.modules.setdefault("PIL", pil_stub)

from utils.avatar_generator import _infer_ethnicity


def test_infer_ethnicity_known_pairs():
    assert _infer_ethnicity("Frederick Sullivan") == "Anglo"
    assert _infer_ethnicity("Jim Thompson") == "Anglo"
