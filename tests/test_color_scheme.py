import pytest
from types import SimpleNamespace

owner_dashboard = pytest.importorskip("ui.owner_dashboard")


def test_apply_color_scheme_updates_stylesheet():
    dash = owner_dashboard.OwnerDashboard.__new__(owner_dashboard.OwnerDashboard)
    dash.setStyleSheet = lambda s: setattr(dash, "_style", s)
    owner_dashboard.OwnerDashboard.apply_color_scheme(dash, "#111111", "#222222")
    assert "#111111" in dash._style
    assert "#222222" in dash._style


def test_apply_team_colors_uses_team_values():
    dash = owner_dashboard.OwnerDashboard.__new__(owner_dashboard.OwnerDashboard)
    dash.team = SimpleNamespace(primary_color="#333333", secondary_color="#444444")
    captured = {}

    def fake_apply(primary, secondary):
        captured["primary"] = primary
        captured["secondary"] = secondary

    dash.apply_color_scheme = fake_apply
    owner_dashboard.OwnerDashboard.apply_team_colors(dash)
    assert captured == {"primary": "#333333", "secondary": "#444444"}
