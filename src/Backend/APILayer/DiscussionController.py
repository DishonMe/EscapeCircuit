from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.ServiceLayer.DiscussionService import DiscussionService
from Backend.ServiceLayer.ReplyService import ReplyService
from Backend.APILayer.auth_utils import verify_token


class CreateDiscussionReq(BaseModel):
    title: str
    body: str
    category: str = "general"
    puzzle_id: Optional[int] = None


class UpdateDiscussionReq(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    category: Optional[str] = None


class CreateReplyReq(BaseModel):
    body: str
    parent_reply_id: Optional[int] = None


class UpdateReplyReq(BaseModel):
    body: str


class VoteReq(BaseModel):
    value: int  # +1 or -1


class ReactionReq(BaseModel):
    reaction_type: str


class ReportReq(BaseModel):
    reason: str
    details: str = ""


class UpdateReportStatusReq(BaseModel):
    status: str


def build_discussion_router(
    discussion_service: DiscussionService,
    reply_service: ReplyService,
) -> APIRouter:
    router = APIRouter(prefix="/discussions", tags=["discussions"])

    # ---- Discussion CRUD ----

    @router.get("")
    def list_discussions(
        limit: int = 20,
        offset: int = 0,
        category: Optional[str] = None,
        puzzle_id: Optional[int] = None,
        author_id: Optional[int] = None,
        sort: str = "newest",
        search: Optional[str] = None,
        token: str = Depends(verify_token),
    ):
        try:
            return discussion_service.list_discussions(
                token,
                limit=limit,
                offset=offset,
                category=category,
                puzzle_id=puzzle_id,
                author_id=author_id,
                sort_by=sort,
                search=search,
            )
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("")
    def create_discussion(req: CreateDiscussionReq, token: str = Depends(verify_token)):
        try:
            return discussion_service.create_discussion(token, req.model_dump())
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/{discussion_id}")
    def get_discussion(discussion_id: int, token: str = Depends(verify_token)):
        try:
            return discussion_service.get_discussion(token, discussion_id)
        except ValidationError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.patch("/{discussion_id}")
    def update_discussion(
        discussion_id: int,
        req: UpdateDiscussionReq,
        token: str = Depends(verify_token),
    ):
        try:
            payload = {k: v for k, v in req.model_dump().items() if v is not None}
            return discussion_service.update_discussion(token, discussion_id, payload)
        except ValidationError as e:
            code = 403 if "not allowed" in str(e).lower() else 400
            raise HTTPException(status_code=code, detail=str(e))

    @router.delete("/{discussion_id}")
    def delete_discussion(discussion_id: int, token: str = Depends(verify_token)):
        try:
            return discussion_service.delete_discussion(token, discussion_id)
        except ValidationError as e:
            code = 403 if "not allowed" in str(e).lower() else 404
            raise HTTPException(status_code=code, detail=str(e))

    @router.post("/{discussion_id}/pin")
    def pin_discussion(discussion_id: int, token: str = Depends(verify_token)):
        try:
            return discussion_service.pin_discussion(token, discussion_id)
        except ValidationError as e:
            code = 403 if "admin" in str(e).lower() else 404
            raise HTTPException(status_code=code, detail=str(e))

    @router.post("/{discussion_id}/lock")
    def lock_discussion(discussion_id: int, token: str = Depends(verify_token)):
        try:
            return discussion_service.lock_discussion(token, discussion_id)
        except ValidationError as e:
            code = 403 if "admin" in str(e).lower() else 404
            raise HTTPException(status_code=code, detail=str(e))

    # ---- Engagement: Discussion ----

    @router.post("/{discussion_id}/vote")
    def vote_discussion(discussion_id: int, req: VoteReq, token: str = Depends(verify_token)):
        try:
            return discussion_service.vote_discussion(token, discussion_id, req.value)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/{discussion_id}/react")
    def react_to_discussion(discussion_id: int, req: ReactionReq, token: str = Depends(verify_token)):
        try:
            return discussion_service.react_to_discussion(token, discussion_id, req.reaction_type)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/{discussion_id}/follow")
    def follow_discussion(discussion_id: int, token: str = Depends(verify_token)):
        try:
            return discussion_service.follow_discussion(token, discussion_id)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.post("/{discussion_id}/bookmark")
    def bookmark_discussion(discussion_id: int, token: str = Depends(verify_token)):
        try:
            return discussion_service.bookmark_discussion(token, discussion_id)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # ---- Reports: Discussion ----

    @router.post("/{discussion_id}/report")
    def report_discussion(discussion_id: int, req: ReportReq, token: str = Depends(verify_token)):
        try:
            return discussion_service.report_discussion(token, discussion_id, req.reason, req.details)
        except ValidationError as e:
            code = 400
            if "already reported" in str(e).lower():
                code = 409
            raise HTTPException(status_code=code, detail=str(e))

    # ---- Replies ----

    @router.get("/{discussion_id}/replies")
    def get_replies(
        discussion_id: int,
        limit: int = 100,
        offset: int = 0,
        token: str = Depends(verify_token),
    ):
        try:
            return reply_service.get_replies(token, discussion_id, limit=limit, offset=offset)
        except ValidationError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.post("/{discussion_id}/replies")
    def create_reply(
        discussion_id: int,
        req: CreateReplyReq,
        token: str = Depends(verify_token),
    ):
        try:
            return reply_service.create_reply(token, discussion_id, req.model_dump())
        except ValidationError as e:
            code = 403 if "locked" in str(e).lower() else 400
            raise HTTPException(status_code=code, detail=str(e))

    # Reply-level endpoints (outside /discussions prefix)
    reply_router = APIRouter(prefix="/replies", tags=["replies"])

    @reply_router.patch("/{reply_id}")
    def update_reply(reply_id: int, req: UpdateReplyReq, token: str = Depends(verify_token)):
        try:
            return reply_service.update_reply(token, reply_id, req.model_dump())
        except ValidationError as e:
            code = 403 if "not allowed" in str(e).lower() else 400
            raise HTTPException(status_code=code, detail=str(e))

    @reply_router.delete("/{reply_id}")
    def delete_reply(reply_id: int, token: str = Depends(verify_token)):
        try:
            return reply_service.delete_reply(token, reply_id)
        except ValidationError as e:
            code = 403 if "not allowed" in str(e).lower() else 404
            raise HTTPException(status_code=code, detail=str(e))

    @reply_router.post("/{reply_id}/accept")
    def accept_reply(reply_id: int, token: str = Depends(verify_token)):
        try:
            return reply_service.accept_reply(token, reply_id)
        except ValidationError as e:
            code = 403 if "not allowed" in str(e).lower() or "only" in str(e).lower() else 404
            raise HTTPException(status_code=code, detail=str(e))

    # ---- Engagement: Reply ----

    @reply_router.post("/{reply_id}/vote")
    def vote_reply(reply_id: int, req: VoteReq, token: str = Depends(verify_token)):
        try:
            return reply_service.vote_reply(token, reply_id, req.value)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @reply_router.post("/{reply_id}/react")
    def react_to_reply(reply_id: int, req: ReactionReq, token: str = Depends(verify_token)):
        try:
            return reply_service.react_to_reply(token, reply_id, req.reaction_type)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @reply_router.post("/{reply_id}/report")
    def report_reply(reply_id: int, req: ReportReq, token: str = Depends(verify_token)):
        try:
            return discussion_service.report_reply(token, reply_id, req.reason, req.details)
        except ValidationError as e:
            code = 409 if "already reported" in str(e).lower() else 400
            raise HTTPException(status_code=code, detail=str(e))

    # ---- Reports: Admin ----
    report_router = APIRouter(prefix="/reports", tags=["reports"])

    @report_router.get("")
    def list_reports(
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        token: str = Depends(verify_token),
    ):
        try:
            return discussion_service.list_reports(token, status=status, limit=limit, offset=offset)
        except ValidationError as e:
            code = 403 if "admin" in str(e).lower() else 400
            raise HTTPException(status_code=code, detail=str(e))

    @report_router.patch("/{report_id}")
    def update_report(report_id: int, req: UpdateReportStatusReq, token: str = Depends(verify_token)):
        try:
            return discussion_service.update_report_status(token, report_id, req.status)
        except ValidationError as e:
            code = 403 if "admin" in str(e).lower() else 400
            raise HTTPException(status_code=code, detail=str(e))

    @report_router.post("/{report_id}/warn")
    def warn_report_author(report_id: int, token: str = Depends(verify_token)):
        try:
            return discussion_service.warn_user_for_report(token, report_id)
        except ValidationError as e:
            code = 403 if "admin" in str(e).lower() else 400
            raise HTTPException(status_code=code, detail=str(e))

    @report_router.post("/{report_id}/ban")
    def ban_report_author(report_id: int, token: str = Depends(verify_token)):
        try:
            return discussion_service.ban_user_for_report(token, report_id)
        except ValidationError as e:
            code = 403 if "admin" in str(e).lower() else 400
            raise HTTPException(status_code=code, detail=str(e))

    @report_router.post("/{report_id}/delete-content")
    def delete_reported_content(report_id: int, token: str = Depends(verify_token)):
        try:
            return discussion_service.delete_reported_content(token, report_id)
        except ValidationError as e:
            code = 403 if "admin" in str(e).lower() else 400
            raise HTTPException(status_code=code, detail=str(e))

    @report_router.post("/{report_id}/lock")
    def lock_reported_discussion(report_id: int, token: str = Depends(verify_token)):
        try:
            return discussion_service.lock_reported_discussion(token, report_id)
        except ValidationError as e:
            code = 403 if "admin" in str(e).lower() else 400
            raise HTTPException(status_code=code, detail=str(e))

    # Puzzle discussions endpoint
    puzzle_router = APIRouter(prefix="/puzzles", tags=["puzzles"])

    @puzzle_router.get("/{puzzle_id}/discussions")
    def get_puzzle_discussions(
        puzzle_id: int,
        limit: int = 20,
        offset: int = 0,
        token: str = Depends(verify_token),
    ):
        try:
            return discussion_service.list_discussions(
                token, limit=limit, offset=offset, puzzle_id=puzzle_id
            )
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Return all routers - they'll be included separately
    return router, reply_router, puzzle_router, report_router
