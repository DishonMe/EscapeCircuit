import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from Backend import settings
from Backend.APILayer.middleware import ContentionMonitorMiddleware
from pathlib import Path

# Persistence
from Backend.PersistantLayer._db import connect
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


def create_app() -> FastAPI:
    # 1. Database Connection
    # Determine DB path relative to this file
    # This file is in src/Backend, so parent is Backend, parent.parent is src.
    # We want DB in src root (or project root, let's keep it in src root for consistency with previous setup)
    # Wait, previous was "parent.parent / db" from "src/main.py".
    # src/main.py -> parent=src, parent.parent=root.
    # So DB was in Project Root.
    # New: src/Backend/main.py -> parent=Backend, parent.parent=src, parent.parent.parent=root.
    db_path = Path(__file__).parent.parent.parent / "escape_circuit.db"
    # print(f"Connecting to database at: {db_path}")
    conn = connect(str(db_path))

    # 2. Repositories
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

    # 3. Services
    # logic engine (stateless)
    logic_engine = logicEngineService()

    # XP Service (depends on UserRepo)
    xp_service = XPService(user_repo)

    # Auth Service (depends on UserRepo)
    auth_service = AuthService(user_repo)

    # Notification Service
    notification_service = NotificationService(notification_repo, auth_service)

    # User Service
    user_service = UserService(
        user_repo,
        auth_service,
        xp_service,
        audit_log_repo=audit_log_repo,
    )

    # Circuit Service
    circuit_service = CircuitService(
        circuit_repo, 
        user_repo, 
        auth_service, 
        logic_engine, 
        xp_service
    )

    # Arsenal Service
    arsenal_service = ArsenalService(
        circuit_repo, 
        user_repo, 
        auth_service, 
        logic_engine, 
        xp_service
    )

    # Solving Service
    # Note: SolvingService takes 'conn' as first arg for transaction handling in tests/production
    solving_service = SolvingService(
        conn,
        solve_repo,
        puzzle_repo,
        circuit_repo,
        auth_service,
        logic_engine,
        xp_service,
        user_repo,
        notification_service,
        clues_repo=clues_repo,
    )

    # Clues Service
    clues_service = CluesService(
        conn=conn,
        clues_repo=clues_repo,
        puzzle_repo=puzzle_repo,
        solve_repo=solve_repo,
        auth=auth_service,
    )

    # Puzzle Service
    # Note: depends on solve_repo optionally, but we pass it for completeness checks
    puzzle_service = PuzzleService(
        puzzle_repo,
        user_repo,
        auth_service,
        solve_repo,
        arsenal_service
    )

    # Rating Service
    rating_service = RatingService(
        rating_repo,
        puzzle_repo,
        solve_repo,
        auth_service,
        xp_service,
        notification_service,
    )

    # Discussion Service
    discussion_service = DiscussionService(
        discussion_repo=discussion_repo,
        reply_repo=reply_repo,
        user_repo=user_repo,
        auth_service=auth_service,
        xp_service=xp_service,
        engagement_repo=engagement_repo,
        report_repo=report_repo,
        notification_repo=notification_repo,
    )

    # Reply Service
    reply_service = ReplyService(
        reply_repo=reply_repo,
        discussion_repo=discussion_repo,
        user_repo=user_repo,
        auth_service=auth_service,
        xp_service=xp_service,
        engagement_repo=engagement_repo,
    )

    # Admin Service
    admin_service = AdminService(
        user_repo=user_repo,
        puzzle_repo=puzzle_repo,
        solve_repo=solve_repo,
        rating_repo=rating_repo,
        audit_log_repo=audit_log_repo,
        notification_repo=notification_repo,
        auth_service=auth_service,
    )

    # 4. FastAPI App
    app = FastAPI(title="EscapeCircuit Backend")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # DB contention monitoring (logs warnings when requests stall on write-lock)
    app.add_middleware(ContentionMonitorMiddleware)

    # Catch-all handler so unhandled exceptions return a JSON 500 with CORS headers
    # (without this, exceptions that escape route handlers bypass CORSMiddleware and
    # the browser sees a network-level failure instead of a readable HTTP error)
    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

    # 5. Routers
    app.include_router(build_user_router(user_service, notification_service))
    app.include_router(build_circuit_router(circuit_service))
    app.include_router(build_arsenal_router(arsenal_service, solving_service))
    app.include_router(build_puzzle_router(puzzle_service, solving_service, rating_service, admin_service, clues_service=clues_service))
    app.include_router(build_rating_router(rating_service))
    app.include_router(build_admin_router(admin_service))
    app.include_router(build_debugger_router(logic_engine, circuit_repo))

    # Discussion & Reply routers
    disc_router, reply_router, puzzle_disc_router, report_router = build_discussion_router(
        discussion_service, reply_service
    )
    app.include_router(disc_router)
    app.include_router(reply_router)
    app.include_router(puzzle_disc_router)
    app.include_router(report_router)

    @app.get("/")
    def root():
        return {"message": "EscapeCircuit API is running"}

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run("Backend.main:app", host="127.0.0.1", port=8080, reload=True, app_dir="src")
