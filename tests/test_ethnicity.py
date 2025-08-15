from utils import infer_ethnicity


def test_infer_ethnicity_lookup():
    assert infer_ethnicity("John", "Smith") == "caucasian"
    assert infer_ethnicity("Hiro", "Tanaka") == "asian"
    assert infer_ethnicity("Unknown", "Name") == "unknown"
