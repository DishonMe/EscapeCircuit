"""
Shared fixtures for integration tests.

Creates a fully wired FastAPI application backed by an in-memory SQLite
database so that every test exercises the real request → controller →
service → repo → DB path.
"""
import sqlite3
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Repositories
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.PersistantLayer.CircuitRepo import CircuitRepo
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.RatingRepo import RatingRepo
from Backend.PersistantLayer.SolveRepo import SolveRepo
from Backend.PersistantLayer.CluesRepo import CluesRepo
from Backend.PersistantLayer.NotificationRepo import NotificationRepo
from Backend.PersistantLayer.AuditLogRepo import AuditLogRepo
from Backend.PersistantLayer.DiscussionRepo import DiscussionRepo
from Backend.PersistantLayer.ReplyRepo import ReplyRepo
from Backend.PersistantLayer.EngagementRepo import EngagementRepo
from Backend.PersistantLayer.ReportRepo import ReportRepo

# Services
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.XPService import XPService
from Backend.ServiceLayer.UserService import UserService
from Backend.ServiceLayer.CircuitService import CircuitService
from Backend.ServiceLayer.ArsenalService import ArsenalService
from Backend.ServiceLayer.PuzzleService import PuzzleService
from Backend.ServiceLayer.SolvingService import SolvingService
from Backend.ServiceLayer.CluesService import CluesService
from Backend.ServiceLayer.RatingService import RatingService
from Backend.ServiceLayer.logicEngineService import logicEngineService
from Backend.ServiceLayer.NotificationService import NotificationService
from Backend.ServiceLayer.AdminService import AdminService
from Backend.ServiceLayer.DiscussionService import DiscussionService
from Backend.ServiceLayer.ReplyService import ReplyService

# Controllers
from Backend.APILayer.UserController import build_user_router
from Backend.APILayer.CircuitController import build_circuit_router
from Backend.APILayer.ArsenalController import build_arsenal_router
from Backend.APILayer.PuzzleController import build_puzzle_router
from Backend.APILayer.RatingController import build_rating_router
from Backend.APILayer.AdminController import build_admin_router
from Backend.APILayer.DebuggerController import build_debugger_router
from Backend.APILayer.DiscussionController import build_discussion_router


def _build_test_app(conn: sqlite3.Connection) -> FastAPI:
    """Wire up the full app stack using the given connection."""
    # Repos
    user_repo = UserRepo(conn)
    circuit_repo = CircuitRepo(conn)
    puzzle_repo = PuzzleRepo(conn)
    rating_repo = RatingRepo(conn)
    solve_repo = SolveRepo(conn)
    clues_repo = CluesRepo(conn)
    notification_repo = NotificationRepo(conn)
    audit_log_repo = AuditLogRepo(conn)
    discussion_repo = DiscussionRepo(conn)
    reply_repo = ReplyRepo(conn)
    engagement_repo = EngagementRepo(conn)
    report_repo = ReportRepo(conn)

    # Services
    logic_engine = logicEngineService()
    xp_service = XPService(user_repo)
    auth_service = AuthService(user_repo)
    notification_service = NotificationService(notification_repo, auth_service)
    user_service = UserService(
        user_repo,
        auth_service,
        xp_service,
        audit_log_repo=audit_log_repo,
    )
    circuit_service = CircuitService(circuit_repo, user_repo, auth_service, logic_engine, xp_service)
    arsenal_service = ArsenalService(circuit_repo, user_repo, auth_service, logic_engine, xp_service)
    solving_service = SolvingService(
        conn, solve_repo, puzzle_repo, circuit_repo,
        auth_service, logic_engine, xp_service, user_repo, notification_service,
        clues_repo=clues_repo,
    )
    clues_service = CluesService(
        conn=conn, clues_repo=clues_repo, puzzle_repo=puzzle_repo,
        solve_repo=solve_repo, auth=auth_service,
    )
    puzzle_service = PuzzleService(puzzle_repo, user_repo, auth_service, solve_repo, arsenal_service)
    rating_service = RatingService(rating_repo, puzzle_repo, solve_repo, auth_service, xp_service, notification_service)
    discussion_service = DiscussionService(
        discussion_repo=discussion_repo, reply_repo=reply_repo,
        user_repo=user_repo, auth_service=auth_service,
        xp_service=xp_service, engagement_repo=engagement_repo,
        report_repo=report_repo, notification_repo=notification_repo,
    )
    reply_service = ReplyService(
        reply_repo=reply_repo, discussion_repo=discussion_repo,
        user_repo=user_repo, auth_service=auth_service,
        xp_service=xp_service, engagement_repo=engagement_repo,
    )
    admin_service = AdminService(
        user_repo=user_repo, puzzle_repo=puzzle_repo,
        solve_repo=solve_repo, rating_repo=rating_repo,
        audit_log_repo=audit_log_repo, notification_repo=notification_repo,
        auth_service=auth_service,
    )

    # FastAPI app
    app = FastAPI(title="EscapeCircuit Test")

    # Routers
    app.include_router(build_user_router(user_service, notification_service))
    app.include_router(build_circuit_router(circuit_service))
    app.include_router(build_arsenal_router(arsenal_service, solving_service))
    app.include_router(build_puzzle_router(puzzle_service, solving_service, rating_service, admin_service, clues_service=clues_service))
    app.include_router(build_rating_router(rating_service))
    app.include_router(build_admin_router(admin_service))
    app.include_router(build_debugger_router(logic_engine))
    disc_router, reply_router, puzzle_disc_router, report_router = build_discussion_router(
        discussion_service, reply_service
    )
    app.include_router(disc_router)
    app.include_router(reply_router)
    app.include_router(puzzle_disc_router)
    app.include_router(report_router)

    return app


@pytest.fixture()
def conn():
    """In-memory SQLite connection shared by every fixture in a single test."""
    c = sqlite3.connect(":memory:", check_same_thread=False)
    c.row_factory = sqlite3.Row
    # Disable Python's implicit transaction handling so that the
    # explicit BEGIN IMMEDIATE in _db.transaction() works correctly.
    c.isolation_level = None
    c.execute("PRAGMA foreign_keys = ON;")
    yield c
    c.close()


@pytest.fixture()
def app(conn):
    return _build_test_app(conn)


@pytest.fixture()
def client(app):
    return TestClient(app)


# --------------- helper shortcuts --------------- #

def register_user(client: TestClient, username: str = "testuser", password: str = "pass123") -> dict:
    """Register a user and return the response JSON (contains token)."""
    resp = client.post("/users/register", json={
        "username": username,
        "password": password,
        "email": f"{username}@test.com",
        "avatar_name": "Dinosaur",
        "avatar_color": "#38bdf8",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()


def auth_header(token: str) -> dict:
    """Return an Authorization header dict for the given token."""
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client: TestClient, username: str = "testuser", password: str = "pass123") -> str:
    """Register + login, return token."""
    data = register_user(client, username, password)
    return data["token"]
