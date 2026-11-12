import asyncio
import logging
from typing import Any

import httpx

from agent.prompts import SYSTEM_PROMPT
from agent.tools import GEMINI_TOOLS_DECLARATION, TOOL_REGISTRY
from config import settings

logger = logging.getLogger(__name__)


async def execute_tool_call(name: str, args: dict, owner: str | None, user_message: str) -> dict:
    tool = TOOL_REGISTRY.get(name)
    if tool is None:
        return {"error": f"Không tìm thấy công cụ {name}."}

    try:
        if name == "tra_cuu_tai_lieu":
            return await tool(query=args["query"], section_code=args.get("section_code"))
        if name == "goi_y_bai_tap":
            return await tool(exercise_code=args["exercise_code"], owner=owner)
        if name == "soan_FAQ":
            return await tool(suggested_answer=args["suggested_answer"], owner=owner)
        return await tool(section_code=args.get("section_code"), owner=owner, user_message=user_message)
    except Exception:
        logger.warning("Study tool failed: %s", name, exc_info=True)
        return {"error": f"Chưa thực hiện được công cụ {name}."}


def workflow_message(ui: dict) -> str:
    messages = []
    if assignment := ui.get("assignment"):
        if assignment["open"]:
            messages.append(
                "Bài tập 3 còn hạn đến 23:59 ngày 13/11. Em có thể mở thẻ để xem gợi ý theo **§3.2** và **§3.5**."
            )
        else:
            messages.append("Bài tập 3 đã hết hạn. Em có thể mở thẻ để xem lời giải.")
    if "faq_draft" in ui:
        messages.append("Bản nháp FAQ về **§3.3** đã được lưu và đang chờ trợ giảng duyệt.")
    if "ta_offer" in ui:
        messages.append("Em có thể xem trước nội dung rồi xác nhận nếu muốn gửi TA.")
    return "\n\n".join(messages)


async def run_react_agent_loop(
    user_message: str,
    history: list[dict[str, Any]] | None = None,
    max_turns: int = 5,
    *,
    owner: str | None = None,
) -> dict[str, Any]:
    key = settings.GEMINI_API_KEY.strip()
    if key in ("", "your_gemini_api_key_here"):
        return {
            "response": "Study Mode chưa có khóa Gemini. Hãy cấu hình GEMINI_API_KEY trong .env để dùng trợ lý.",
            "mode": "unconfigured",
            "tools_called": [],
            "turns": 0,
        }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent"
    contents = []
    for turn in (history or [])[-10:]:
        text = turn.get("content")
        if isinstance(text, str) and text.strip():
            role = "model" if turn.get("role") in ("model", "assistant", "ai") else "user"
            contents.append({"role": role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    tools_called = []
    ui = {}
    final_text = ""
    error = "Lỗi trong quá trình chạy ReAct Agent Loop: Chưa nhận được câu trả lời."
    current_turn = 0
    async with httpx.AsyncClient(timeout=30.0, headers={"x-goog-api-key": key}) as client:
        for current_turn in range(1, max_turns + 1):
            payload = {
                "contents": contents,
                "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
                "tools": GEMINI_TOOLS_DECLARATION,
                "tool_config": {
                    "function_calling_config": {
                        "mode": "NONE" if current_turn == max_turns and tools_called else "AUTO"
                    }
                },
            }
            try:
                response = await client.post(url, json=payload)
                if not response.is_success:
                    logger.warning("Gemini returned HTTP %s", response.status_code)
                    error = f"Lỗi kết nối Gemini API (HTTP {response.status_code})."
                    break
                candidates = response.json().get("candidates", [])
                content = candidates[0].get("content", {}) if candidates else {}
            except (httpx.HTTPError, ValueError):
                logger.warning("Gemini response unavailable", exc_info=True)
                break

            parts = content.get("parts", [])
            calls = [part["functionCall"] for part in parts if "functionCall" in part]
            if not calls:
                final_text = "".join(part.get("text", "") for part in parts if not part.get("thought")).strip()
                break

            # Keep the full model turn, including any Gemini thought signatures.
            contents.append(content)
            results = await asyncio.gather(*(
                execute_tool_call(call["name"], call.get("args", {}), owner, user_message)
                for call in calls
            ))
            tool_parts = []
            for call, result in zip(calls, results):
                ui.update(result.pop("_ui", {}))
                name = call["name"]
                tools_called.append({
                    "turn": current_turn, "tool": name, "arguments": call.get("args", {}), "output": result
                })
                function_response = {"name": name, "response": {"output": result}}
                if "id" in call:
                    function_response["id"] = call["id"]
                tool_parts.append({"functionResponse": function_response})
            contents.append({"role": "function", "parts": tool_parts})

    # Open assignments render the authorized guidance. A successful write is
    # still visible if Gemini fails to summarize the tool result afterward.
    if ui.get("assignment", {}).get("open") or (not final_text and ui):
        final_text = workflow_message(ui)
    elif "assignment" not in ui and any(
        call["tool"] == "goi_y_bai_tap" and call["arguments"].get("exercise_code") == "BT3"
        for call in tools_called
    ):
        final_text = "Chưa tải được trạng thái Bài tập 3. Em hãy mở thẻ bài tập trong tài liệu hoặc thử lại."
    return {
        "response": final_text or error,
        "mode": "gemini",
        "tools_called": tools_called,
        "turns": current_turn,
        **ui,
    }
