import sys
import types

pil_stub = types.ModuleType("PIL")
pil_stub.Image = object
sys.modules.setdefault("PIL", pil_stub)

from utils.avatar_generator import _infer_ethnicity, _select_template


def test_infer_ethnicity_known_pairs():
    assert _infer_ethnicity("Frederick Sullivan") == "Anglo"
    assert _infer_ethnicity("Jim Thompson") == "Anglo"


def test_select_template_path_resolution():
    path = _select_template("Asian", "goatee")
    assert "Template/Asian/goatee.png" in str(path)
    clean = _select_template("Hispanic", "clean_shaven")
    assert clean.name == "clean.png"
