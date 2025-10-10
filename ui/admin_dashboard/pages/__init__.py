"""Page scaffolding for the modular admin dashboard."""
from .base import DashboardPage
from .home import AdminHomePage
from .draft import DraftPage
from .league import LeaguePage
from .teams import TeamsPage
from .users import UsersPage
from .utilities import UtilitiesPage

__all__ = [
    "AdminHomePage",
    "DashboardPage",
    "DraftPage",
    "LeaguePage",
    "TeamsPage",
    "UsersPage",
    "UtilitiesPage",
]
