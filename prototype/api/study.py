import os
import re
from datetime import datetime, time, timedelta, timezone
from math import ceil

from database import get_db_pool

VIETNAM = timezone(timedelta(hours=7))
DEADLINE = datetime(2026, 11, 13, 23, 59, tzinfo=VIETNAM)
SOURCE_SECTION = "§3.3"
SOURCE_QUOTE = "Vì là căn bậc hai, độ lệch chuẩn luôn nhỏ hơn phương sai."
FAQ_QUESTION = "Độ lệch chuẩn có luôn nhỏ hơn phương sai không?"
FAQ_ANSWER = (
    "Độ lệch chuẩn bằng căn bậc hai của phương sai. Với phương sai 0,04, "
    "độ lệch chuẩn là 0,2, lớn hơn 0,04. Khi phương sai bằng 4, độ lệch chuẩn bằng 2. "
    "Vì vậy cần xem giá trị cụ thể thay vì kết luận độ lệch chuẩn luôn nhỏ hơn phương sai."
)
HINT_ONE = (
    "Theo **§3.2**, khi số phần tử chẵn, hãy chọn hai giá trị ở giữa dãy đã sắp xếp. "
    "Ví dụ, với dãy 2, 4, 6, 8, hai giá trị giữa là 4 và 6. Em thử áp dụng vào dãy ở **§3.5** nhé."
)
HINT_TWO = (
    "Theo **§3.2**, hãy cộng hai giá trị em đã chọn rồi chia cho 2 để tự tính trung vị. "
    "Dùng **§3.1** để tính trung bình của cả dãy, rồi đối chiếu hai kết quả với ảnh hưởng của giá trị ngoại lai ở **§3.4**."
)
SOLUTION = (
    "Theo **§3.1**, tổng là 122 nên trung bình là 122 ÷ 8 = 15,25 triệu đồng. "
    "Theo **§3.2**, hai giá trị ở giữa là 11 và 12 nên trung vị là 11,5 triệu đồng. "
    "Trung vị mô tả mức lương điển hình tốt hơn vì mức 45 triệu kéo trung bình lên (**§3.4**)."
)
ATTEMPT = re.compile(r"\s*[+-]?\d+(?:[.,]\d+)?\s*")


def study_now():
    demo = os.getenv("STUDY_DEMO_NOW", "").strip()
    if demo:
        value = datetime.fromisoformat(demo)
        return value.replace(tzinfo=VIETNAM) if value.tzinfo is None else value.astimezone(VIETNAM)
    return datetime.now(VIETNAM)


def next_shift(now):
    date = now.date() + timedelta(days=now.hour >= 22)
    return datetime.combine(date, time(8), tzinfo=VIETNAM)


def earliest_ta_reply(now):
    if 8 <= now.hour < 22:
        return "Trong giờ trực 08:00–22:00, theo hàng đợi của TA."
    return f"Sớm nhất 08:00 ngày {next_shift(now):%d/%m}, theo hàng đợi của TA."


def assignment_state(now, step=1):
    is_open = now < DEADLINE
    return {
        "open": is_open,
        "minutes_left": max(0, ceil((DEADLINE - now).total_seconds() / 60)),
        "step": step,
        "hint_one": HINT_ONE,
        "hint_two": HINT_TWO if step >= 2 else None,
        "solution": SOLUTION if not is_open else None,
        "ta_reply": earliest_ta_reply(now),
        "ta_after_deadline": is_open and next_shift(now) >= DEADLINE,
    }


def valid_attempt(first, second):
    return all(ATTEMPT.fullmatch(value) for value in (first, second))


async def get_assignment(owner):
    now = study_now()
    pool = await get_db_pool()
    step = await pool.fetchval("SELECT step FROM assignment_progress WHERE owner_id = $1", owner)
    return assignment_state(now, step or 1)


async def submit_attempt(owner):
    now = study_now()
    if now >= DEADLINE:
        return assignment_state(now)
    pool = await get_db_pool()
    await pool.execute("""
        INSERT INTO assignment_progress (owner_id, step) VALUES ($1, 2)
        ON CONFLICT (owner_id) DO NOTHING
    """, owner)
    return assignment_state(now, 2)


async def flag_source(owner):
    pool = await get_db_pool()
    async with pool.acquire() as conn, conn.transaction():
        await conn.execute("""
            INSERT INTO source_flags (section_code, quote, example) VALUES ($1, $2, $3)
            ON CONFLICT (section_code) DO NOTHING
        """, SOURCE_SECTION, SOURCE_QUOTE, FAQ_ANSWER)
        await conn.execute("""
            INSERT INTO source_interest (section_code, owner_id) VALUES ($1, $2)
            ON CONFLICT (section_code, owner_id) DO NOTHING
        """, SOURCE_SECTION, owner)


async def save_faq(owner, suggested_answer):
    pool = await get_db_pool()
    row = await pool.fetchrow("""
        INSERT INTO faq_drafts (owner_id, question, suggested_answer, source_section, source_quote)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (owner_id, source_section) WHERE status = 'DRAFT'
        DO UPDATE SET owner_id = EXCLUDED.owner_id
        RETURNING id, question, suggested_answer, source_section, source_quote, status
    """, owner, FAQ_QUESTION, suggested_answer, SOURCE_SECTION, SOURCE_QUOTE)
    return dict(row)
