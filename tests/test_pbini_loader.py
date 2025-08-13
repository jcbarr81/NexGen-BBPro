from pathlib import Path

from logic.pbini_loader import load_pbini


def test_load_pbini_parses_playbalance_section():
    config = load_pbini(Path('logic/PBINI.txt'))
    assert 'PlayBalance' in config
    play = config['PlayBalance']
    assert play['chargeChanceBaseFirst'] == 0
    assert play['chargeChanceBaseThird'] == -20
    assert play['holdChanceBase'] == 0


def test_inline_comments_are_ignored(tmp_path):
    ini_file = tmp_path / 'sample.ini'
    ini_file.write_text('[Test]\na=1 ; comment\nb=2;another\n; c=3\n')
    cfg = load_pbini(ini_file)
    assert cfg['Test']['a'] == 1
    assert cfg['Test']['b'] == 2
    assert 'c' not in cfg['Test']
