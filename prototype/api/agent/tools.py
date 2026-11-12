from database import get_db_pool, get_embedding
from typing import Dict, Any
from study import SOURCE_SECTION, earliest_ta_reply, flag_source, get_assignment, save_faq, study_now

async def tool_tra_cuu_tai_lieu(query: str, section_code: str = None) -> Dict[str, Any]:
    """Tìm trong tài liệu buổi học và đề cương, trả đoạn văn bản kèm mã mục cụ thể."""
    pool = await get_db_pool()
    embedding = None if section_code else await get_embedding(query)

    async with pool.acquire() as conn:
        if section_code:
            clean_sec = section_code.replace("§", "").strip()
            rows = await conn.fetch("""
                SELECT section_code, title, content, is_active_assignment
                FROM course_documents
                WHERE section_code ILIKE '%' || $1 || '%' OR title ILIKE '%' || $1 || '%';
            """, clean_sec)
        else:
            # Vector search using cosine distance (<=>)
            rows = await conn.fetch("""
                SELECT section_code, title, content, is_active_assignment,
                       (embedding <=> $1) as distance
                FROM course_documents
                ORDER BY embedding <=> $1
                LIMIT 3;
            """, embedding)

        results = []
        for r in rows:
            results.append({
                "section_code": r["section_code"],
                "title": r["title"],
                "content": r["content"],
                "is_active_assignment": r["is_active_assignment"]
            })

        return {
            "status": "success",
            "query": query,
            "total_matches": len(results),
            "documents": results
        }

async def tool_goi_y_bai_tap(exercise_code: str, *, owner: str | None) -> Dict[str, Any]:
    code = exercise_code.strip().upper()
    if code == "BT2":
        return {
            "status": "success",
            "exercise": "Bài tập 2",
            "open": False,
            "official_answer": "Trung bình cộng của 4, 8, 6, 5, 7 là 6 (tổng 30 chia 5).",
        }
    if code != "BT3":
        return {"status": "unknown_exercise", "message": "Chỉ hỗ trợ BT2 và BT3."}
    if not owner:
        return {"error": "Cần phiên học viên để xem tiến độ Bài tập 3."}

    assignment = await get_assignment(owner)
    return {
        "status": "success",
        "exercise": "Bài tập 3",
        "deadline": "23:59 ngày 13/11/2026",
        "open": assignment["open"],
        "step": assignment["step"],
        "available_hint": assignment["hint_two"] or assignment["hint_one"],
        "official_answer": assignment["solution"],
        "_ui": {"assignment": assignment},
    }


async def tool_soan_FAQ(suggested_answer: str, *, owner: str | None) -> Dict[str, Any]:
    if not owner:
        return {"error": "Cần phiên học viên để lưu bản nháp."}
    answer = suggested_answer.strip()
    if not answer or len(answer) > 6000:
        return {"error": "Câu trả lời dự thảo phải có từ 1 đến 6000 ký tự."}
    await flag_source(owner)
    draft = await save_faq(owner, answer)
    return {
        "status": "DRAFT",
        "draft_id": draft["id"],
        "source_section": SOURCE_SECTION,
        "_ui": {"faq_draft": draft},
    }


async def tool_de_xuat_chuyen_TA(
    section_code: str | None = None, *, owner: str | None, user_message: str
) -> Dict[str, Any]:
    if not owner:
        return {"error": "Cần phiên học viên để đề xuất chuyển TA."}
    if section_code == SOURCE_SECTION:
        await flag_source(owner)
    eta = earliest_ta_reply(study_now())
    return {
        "status": "awaiting_student_confirmation",
        "expected_reply_at": eta,
        "_ui": {"ta_offer": {"question": user_message, "expected_reply_at": eta}},
    }


TOOL_REGISTRY = {
    "tra_cuu_tai_lieu": tool_tra_cuu_tai_lieu,
    "goi_y_bai_tap": tool_goi_y_bai_tap,
    "soan_FAQ": tool_soan_FAQ,
    "de_xuat_chuyen_TA": tool_de_xuat_chuyen_TA,
}

GEMINI_TOOLS_DECLARATION = [{
    "function_declarations": [
        {
            "name": "tra_cuu_tai_lieu",
            "description": "Tra tài liệu khóa học và lấy mã mục để dẫn nguồn.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "query": {"type": "STRING", "description": "Nội dung cần tra."},
                    "section_code": {"type": "STRING", "description": "Mã mục nếu biết, ví dụ §3.2, §3.3 hoặc SYLLABUS."},
                },
                "required": ["query"],
            },
        },
        {
            "name": "goi_y_bai_tap",
            "description": "Mở thẻ bài tập, lấy hạn nộp, trạng thái và gợi ý được phép. Bắt buộc dùng cho yêu cầu về BT3, kể cả xin đáp số hay hỏi bước tiếp theo.",
            "parameters": {
                "type": "OBJECT",
                "properties": {"exercise_code": {"type": "STRING", "enum": ["BT2", "BT3"]}},
                "required": ["exercise_code"],
            },
        },
        {
            "name": "soan_FAQ",
            "description": "Lưu câu trả lời về phương sai và độ lệch chuẩn ở §3.3 thành bản nháp chờ TA. Chỉ dùng khi học viên đề nghị chia sẻ cho lớp.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "suggested_answer": {
                        "type": "STRING",
                        "description": "Câu trả lời FAQ tiếng Việt, dẫn §3.3 và có phản ví dụ kiểm tra được.",
                    },
                },
                "required": ["suggested_answer"],
            },
        },
        {
            "name": "de_xuat_chuyen_TA",
            "description": "Mở xem trước nội dung học viên có thể xác nhận gửi TA. Không tạo ticket. Với mâu thuẫn đã biết ở §3.3, đồng thời đánh dấu nguồn.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "section_code": {"type": "STRING", "description": "Truyền §3.3 khi báo mâu thuẫn ở mục này; bỏ trống khi hỏi TA về chủ đề khác."},
                },
            },
        },
    ],
}]
