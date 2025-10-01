from __future__ import annotations

def test_import_owner_home_page_headless():
    from ui.owner_home_page import OwnerHomePage  # noqa: F401
    assert OwnerHomePage is not None

