from utils import openai_client


def test_read_api_key_handles_raw_section(tmp_path, monkeypatch):
    config = tmp_path / "config.ini"
    config.write_text("[OpenAIkey]\nline1\nline2\n")
    fake_module_path = tmp_path / "utils" / "openai_client.py"
    fake_module_path.parent.mkdir()
    fake_module_path.touch()
    monkeypatch.setattr(openai_client, "__file__", str(fake_module_path))
    assert openai_client._read_api_key() == "line1line2"

