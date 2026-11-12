import os
import re
import secrets
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent.loop import run_react_agent_loop
from database import get_db_pool, init_db
from seed_data import seed
from study import earliest_ta_reply, get_assignment, study_now, submit_attempt, valid_attempt

app = FastAPI(title="Study Mode · T2 Giáo dục")
OWNER_COOKIE = "study_session"
WEB_ROOT = Path(__file__).resolve().parent / "web"
app.mount("/assets", StaticFiles(directory=WEB_ROOT), name="study-assets")


class ChatRequest(BaseModel):
    message: str = Field(max_length=4000)
    history: list[dict] | None = Field(default_factory=list)


class AttemptRequest(BaseModel):
    first: str = Field(max_length=24)
    second: str = Field(max_length=24)


class TicketRequest(BaseModel):
    question: str = Field(max_length=4000)
    request_id: UUID
    assignment: bool = False


class ApprovalRequest(BaseModel):
    answer: str = Field(max_length=6000)
    reviewed: bool = False


@app.middleware("http")
async def attach_student_session(request: Request, call_next):
    owner = request.cookies.get(OWNER_COOKIE, "")
    fresh = not re.fullmatch(r"[0-9a-f]{48}", owner)
    request.state.owner = secrets.token_hex(24) if fresh else owner
    response = await call_next(request)
    if fresh and not request.url.path.startswith("/assets/"):
        response.set_cookie(
            OWNER_COOKIE, request.state.owner, httponly=True, samesite="strict",
            secure=request.url.scheme == "https", max_age=60 * 60 * 24 * 30,
        )
    return response


def require_ta(key: Annotated[str | None, Header(alias="X-TA-Key")] = None):
    expected = os.getenv("STUDY_TA_KEY", "")
    if not expected:
        raise HTTPException(503, "Chưa cấu hình mã truy cập trợ giảng.")
    if key is None or not secrets.compare_digest(key.encode(), expected.encode()):
        raise HTTPException(403, "Mã truy cập trợ giảng không hợp lệ.")


TA_ONLY = [Depends(require_ta)]


@app.on_event("startup")
async def startup_event():
    try:
        await init_db()
        await seed()
    except Exception as exc:
        print(f"FastAPI startup warning: {exc}")


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "study-mode-agent-t2"}


@app.post("/seed")
async def trigger_seed():
    await seed()
    return {"status": "success", "message": "Database seeded successfully"}


@app.post("/chat")
async def chat_endpoint(req: ChatRequest, request: Request):
    message = req.message.strip()
    if not message:
        raise HTTPException(400, "Tin nhắn không được để trống")
    return await run_react_agent_loop(message, req.history, owner=request.state.owner)


@app.get("/study/assignment")
async def assignment(request: Request):
    return await get_assignment(request.state.owner)


@app.post("/study/assignment/attempt")
async def assignment_attempt(req: AttemptRequest, request: Request):
    if not valid_attempt(req.first, req.second):
        raise HTTPException(422, "Nhập hai giá trị em tìm được trước khi mở bước 2.")
    return await submit_attempt(request.state.owner)


@app.get("/study/records")
async def student_records(request: Request):
    owner = request.state.owner
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        drafts = await conn.fetch("""
            SELECT id, question, suggested_answer, source_section, source_quote, status
            FROM faq_drafts WHERE owner_id = $1 ORDER BY id DESC LIMIT 20
        """, owner)
        tickets = await conn.fetch("""
            SELECT id, question, expected_reply_at, status
            FROM ta_tickets WHERE owner_id = $1 ORDER BY id DESC LIMIT 20
        """, owner)
        published = await conn.fetch("""
            SELECT id, question, suggested_answer, source_section
            FROM faq_drafts WHERE status = 'PUBLISHED' ORDER BY id DESC LIMIT 20
        """)
    return {
        "drafts": [dict(row) for row in drafts],
        "tickets": [dict(row) for row in tickets],
        "published": [dict(row) for row in published],
        "ta_reply": earliest_ta_reply(study_now()),
    }


@app.post("/study/tickets")
async def create_ticket(req: TicketRequest, request: Request):
    question = req.question.strip()
    if not question:
        raise HTTPException(422, "Nhập nội dung cần chuyển trước khi xác nhận.")
    pool = await get_db_pool()
    now = study_now()
    context = "Học viên xác nhận gửi"
    if req.assignment:
        state = await get_assignment(request.state.owner)
        timing = f"còn {state['minutes_left']} phút" if state["open"] else "đã hết hạn"
        context = f"Bài tập 3 · gửi lúc {now:%H:%M %d/%m} · {timing} · đã xem gợi ý đến bước {state['step']}"
    row = await pool.fetchrow("""
        INSERT INTO ta_tickets (owner_id, request_id, student_id, question, context, expected_reply_at)
        VALUES ($1, $2, 'HV_DEMO', $3, $4, $5)
        ON CONFLICT (owner_id, request_id) DO UPDATE SET owner_id = EXCLUDED.owner_id
        RETURNING id, question, status, expected_reply_at
    """, request.state.owner, req.request_id, question, context, earliest_ta_reply(now))
    return dict(row)


@app.post("/study/tickets/{ticket_id}/cancel")
async def cancel_ticket(ticket_id: int, request: Request):
    pool = await get_db_pool()
    row = await pool.fetchrow("""
        UPDATE ta_tickets SET status = 'CANCELLED'
        WHERE id = $1 AND owner_id = $2 AND status = 'PENDING_REVIEW'
        RETURNING id
    """, ticket_id, request.state.owner)
    if row is None:
        raise HTTPException(409, "Yêu cầu đã đổi trạng thái. Hãy tải lại để kiểm tra.")
    return {"status": "CANCELLED"}


@app.post("/study/faq/{faq_id}/cancel")
async def cancel_faq(faq_id: int, request: Request):
    pool = await get_db_pool()
    row = await pool.fetchrow("""
        UPDATE faq_drafts SET status = 'CANCELLED'
        WHERE id = $1 AND owner_id = $2 AND status = 'DRAFT'
        RETURNING id
    """, faq_id, request.state.owner)
    if row is None:
        raise HTTPException(409, "Bản nháp đã đổi trạng thái. Hãy tải lại để kiểm tra.")
    return {"status": "CANCELLED"}


@app.get("/tickets", dependencies=TA_ONLY)
async def get_tickets():
    pool = await get_db_pool()
    rows = await pool.fetch("""
        SELECT id, student_id, question, context, expected_reply_at, status
        FROM ta_tickets WHERE status <> 'CANCELLED' ORDER BY id DESC LIMIT 50
    """)
    return [dict(row) for row in rows]


async def transition_ticket(ticket_id, before, after):
    pool = await get_db_pool()
    row = await pool.fetchrow("""
        UPDATE ta_tickets SET status = $3 WHERE id = $1 AND status = $2 RETURNING id
    """, ticket_id, before, after)
    if row is None:
        raise HTTPException(409, "Ticket đã đổi trạng thái. Hãy làm mới danh sách.")
    return {"status": after}


@app.post("/tickets/{ticket_id}/open", dependencies=TA_ONLY)
async def open_ticket(ticket_id: int):
    return await transition_ticket(ticket_id, "PENDING_REVIEW", "IN_REVIEW")


@app.post("/tickets/{ticket_id}/resolve", dependencies=TA_ONLY)
async def resolve_ticket(ticket_id: int):
    return await transition_ticket(ticket_id, "IN_REVIEW", "RESOLVED")


@app.get("/faq", dependencies=TA_ONLY)
async def get_faq_drafts():
    pool = await get_db_pool()
    rows = await pool.fetch("""
        SELECT d.id, d.question, d.suggested_answer, d.source_section, d.source_quote, d.status,
               (SELECT count(*) FROM source_interest AS i WHERE i.section_code = d.source_section) AS interested_count
        FROM faq_drafts AS d WHERE d.status <> 'CANCELLED' ORDER BY d.id DESC LIMIT 50
    """)
    return [dict(row) for row in rows]


@app.post("/faq/{faq_id}/approve", dependencies=TA_ONLY)
async def approve_faq(faq_id: int, req: ApprovalRequest):
    answer = req.answer.strip()
    if not answer:
        raise HTTPException(422, "Nhập nội dung FAQ trước khi đăng.")
    pool = await get_db_pool()
    row = await pool.fetchrow("""
        UPDATE faq_drafts SET status = 'PUBLISHED', suggested_answer = $2
        WHERE id = $1 AND status = 'DRAFT' AND (source_quote IS NULL OR $3)
        RETURNING id
    """, faq_id, answer, req.reviewed)
    if row is None:
        raise HTTPException(409, "Cần xác nhận đã kiểm tra nguồn và bản nháp còn chờ duyệt.")
    return {"status": "PUBLISHED"}


@app.post("/faq/{faq_id}/reject", dependencies=TA_ONLY)
async def reject_faq(faq_id: int):
    pool = await get_db_pool()
    row = await pool.fetchrow("""
        UPDATE faq_drafts SET status = 'REJECTED' WHERE id = $1 AND status = 'DRAFT' RETURNING id
    """, faq_id)
    if row is None:
        raise HTTPException(409, "Bản nháp đã đổi trạng thái. Hãy làm mới danh sách.")
    return {"status": "REJECTED"}


@app.get("/sources", dependencies=TA_ONLY)
async def get_source_flags():
    pool = await get_db_pool()
    rows = await pool.fetch("""
        SELECT section_code, quote, example FROM source_flags
        WHERE NOT dismissed ORDER BY section_code
    """)
    return [dict(row) for row in rows]


@app.post("/sources/{section_code}/dismiss", dependencies=TA_ONLY)
async def dismiss_source(section_code: str):
    pool = await get_db_pool()
    row = await pool.fetchrow("""
        UPDATE source_flags SET dismissed = TRUE WHERE section_code = $1 AND NOT dismissed
        RETURNING section_code
    """, section_code)
    if row is None:
        raise HTTPException(409, "Đoạn tài liệu đã đổi trạng thái. Hãy làm mới danh sách.")
    return {"status": "DISMISSED"}


@app.get("/", response_class=FileResponse)
async def serve_ui():
    return FileResponse(WEB_ROOT / "index.html", media_type="text/html")
