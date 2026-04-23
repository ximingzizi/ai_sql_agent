import asyncio
import json
import os
import re
import uuid
from typing import Any, AsyncGenerator, Optional

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import StreamingResponse
from langchain.agents import create_agent
from langchain.tools import tool
from pydantic import BaseModel, Field

from app.ai.model.model import MyModel
from app.utils.Logger import Logger

logger = Logger.get_logger(__name__)
chat_router = APIRouter()
model = MyModel.get_model()


class SpecialistTaskInput(BaseModel):
    task: str = Field(..., description="需要交给专业子智能体处理的完整任务描述。")


SUPERVISOR_PROMPT = """
你是一个主智能体（supervisor），负责拆解任务、调用多个专业子智能体，并把最终结果返回给用户。

你有 5 个子智能体工具：
1. sql_specialist：数据库问答、SQL 查询、结构化文本回答
2. chart_specialist：生成单图表 ECharts 配置
3. analyze_specialist：生成表格 + 分析结论 + 图表
4. dashboard_specialist：生成多图表仪表盘链接
5. file_specialist：分析上传文件并输出处理后的文件地址

严格规则：
- 你必须优先通过子智能体工具完成任务，而不是自己直接编造结果。
- 如果一个任务需要多步，你可以连续调用多个子智能体。
- 每个子智能体工具都会返回一个 JSON 字符串，格式是 {"type": "...", "payload": {...}}。
- 如果某个工具已经完整解决了问题，你可以直接复用它的结果。
- 如果你调用了多个工具，你必须综合多个工具结果，输出一个最终 JSON。
- 如果用户有上传文件路径，且任务涉及文件内容、清洗、提取、总结、导出，优先使用 file_specialist。
- 如果任务需要图表和分析同时给出，优先返回 analyze 类型；如果是多图表看板，返回 dashboard 类型。
- 如果只是普通问答或综合说明，返回 text 类型。

你的最终输出必须是一个合法 JSON 对象，且只能输出这个 JSON，不能输出额外解释、Markdown、代码块或前后缀。

最终 JSON 格式固定为：
{"type": "text|chart|analyze|dashboard|file", "payload": {...}}

其中：
- text.payload = {"content": "..."}
- chart.payload = {"chartJson": "...", "msg": "..."}
- analyze.payload = {"table": {...}, "result": "...", "chartJson": "..."}
- dashboard.payload = {"url": "...", "message": "..."}
- file.payload = {"summary": "...", "downloadUrl": "..."}
"""

# SSE 输出
def _to_sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

# JSON 输出
def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)

# 提取下载链接
def _extract_download_url(text: str) -> str:
    match = re.search(r"https?://[^\s]+", text or "")
    return match.group(0) if match else ""

# 安全 JSON 加载
def _safe_json_loads(raw: Any) -> Any:
    if isinstance(raw, (dict, list)):
        return raw
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw

# JSON 对象提取
def _extract_json_object(text: str) -> Optional[dict]:
    if not text:
        return None

    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    last_dict = None
    index = 0
    while index < len(cleaned):
        brace_index = cleaned.find("{", index)
        if brace_index == -1:
            break
        try:
            parsed, end_index = decoder.raw_decode(cleaned[brace_index:])
            if isinstance(parsed, dict):
                last_dict = parsed
            index = brace_index + max(end_index, 1)
        except json.JSONDecodeError:
            index = brace_index + 1

    return last_dict

# 适配 dashboard_tool
def _normalize_dashboard_tool_result(raw: dict) -> dict:
    dashboard_data = _safe_json_loads(raw.get("data"))
    url = ""
    if isinstance(dashboard_data, dict):
        url = dashboard_data.get("url", "")
    elif isinstance(dashboard_data, str):
        url = dashboard_data

    return {
        "type": "dashboard",
        "payload": {
            "url": url,
            "message": raw.get("message", raw.get("msg", "仪表盘已生成")),
        },
    }


def _normalize_text_tool_result(content: str) -> dict:
    return {
        "type": "text",
        "payload": {
            "content": content,
        },
    }


def _normalize_chart_tool_result(raw: dict) -> dict:
    return {
        "type": "chart",
        "payload": {
            "chartJson": raw.get("json", ""),
            "msg": raw.get("msg", ""),
        },
    }


def _normalize_analyze_tool_result(raw: dict) -> dict:
    return {
        "type": "analyze",
        "payload": {
            "table": raw.get("table", {}),
            "result": raw.get("result", ""),
            "chartJson": raw.get("json", ""),
        },
    }


def _normalize_file_tool_result(summary: str) -> dict:
    return {
        "type": "file",
        "payload": {
            "summary": summary,
            "downloadUrl": _extract_download_url(summary),
        },
    }


def _build_observability(telemetry: dict) -> dict:
    return {
        "agentCalls": telemetry.get("agent_calls", []),
    }

# 构建最终结果
def _build_final_envelope(result: dict, telemetry: Optional[dict] = None) -> dict:
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "type": result.get("type", "text"),
            "payload": result.get("payload", {"content": ""}),
            "meta": _build_observability(telemetry or {"agent_calls": []}),
        },
    }


def _fallback_text_result(text: str) -> dict:
    return _normalize_text_tool_result(text.strip())


def _build_supervisor_agent(request: Request, user_id: str, file_path: Optional[str]):
    telemetry = {
        "agent_calls": [],
    }

    def record_specialist(tool_name: str):
        telemetry["agent_calls"].append(tool_name)

    async def run_sync_tool(callable_obj, *args):
        """
        子智能体统一走同步执行；这里仅做 async 桥接，避免阻塞 FastAPI 主事件循环。
        """
        return await asyncio.to_thread(callable_obj, *args)

    @tool("sql_specialist", args_schema=SpecialistTaskInput)
    async def sql_specialist(task: str) -> str:
        """处理数据库问答、SQL 查询、结构化文本回答。"""
        result = await run_sync_tool(request.app.state.sql_question_agent_pg.answer_sync, task, user_id)
        record_specialist("sql_specialist")
        return _json_dumps(_normalize_text_tool_result(result.get("content", "")))

    @tool("chart_specialist", args_schema=SpecialistTaskInput)
    async def chart_specialist(task: str) -> str:
        """处理单图表请求，返回 ECharts 配置。"""
        result = await run_sync_tool(request.app.state.echarts_agent.answer_sync, task, user_id)
        record_specialist("chart_specialist")
        return _json_dumps(_normalize_chart_tool_result(result.get("content", {})))

    @tool("analyze_specialist", args_schema=SpecialistTaskInput)
    async def analyze_specialist(task: str) -> str:
        """处理表格、结论、图表一体化分析。"""
        result = await run_sync_tool(request.app.state.analyze_agent.answer_sync, task, user_id)
        record_specialist("analyze_specialist")
        return _json_dumps(_normalize_analyze_tool_result(result.get("content", {})))

    @tool("dashboard_specialist", args_schema=SpecialistTaskInput)
    async def dashboard_specialist(task: str) -> str:
        """处理多图表仪表盘请求，返回仪表盘访问地址。"""
        result = await run_sync_tool(request.app.state.dashboard_agent.answer_sync, task, user_id)
        record_specialist("dashboard_specialist")
        return _json_dumps(_normalize_dashboard_tool_result(result.get("content", {})))

    @tool("file_specialist", args_schema=SpecialistTaskInput)
    async def file_specialist(task: str) -> str:
        """处理上传文件分析、清洗、导出新文件。"""
        if not file_path:
            record_specialist("file_specialist")
            return _json_dumps({
                "type": "file",
                "payload": {
                    "summary": "当前没有可用的上传文件路径，无法执行文件分析。",
                    "downloadUrl": "",
                },
            })
        result = await run_sync_tool(request.app.state.file_analyze_agent.answer_sync, task, file_path, user_id)
        record_specialist("file_specialist")
        return _json_dumps(_normalize_file_tool_result(result.get("content", "")))

    agent = create_agent(
        model=model,
        tools=[
            sql_specialist,
            chart_specialist,
            analyze_specialist,
            dashboard_specialist,
            file_specialist,
        ],
        system_prompt=SUPERVISOR_PROMPT,
    )
    return agent, telemetry


def _build_supervisor_input(question: str, file_path: Optional[str]) -> str:
    if not file_path:
        return question
    return f"{question}\n\n已上传文件路径: {file_path}"

# 调用主代理
async def _invoke_supervisor_once(
    request: Request,
    question: str,
    user_id: str,
    file_path: Optional[str] = None,
) -> dict:
    supervisor, telemetry = _build_supervisor_agent(request, user_id, file_path)
    user_content = _build_supervisor_input(question, file_path)
    result = await supervisor.ainvoke(
        {"messages": [{"role": "user", "content": user_content}]}
    )

    try:
        final_content = result["messages"][-1].content
    except Exception:
        final_content = str(result)

    if isinstance(final_content, list):
        final_text = "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in final_content).strip()
    else:
        final_text = str(final_content).strip()

    parsed = _extract_json_object(final_text)
    if parsed is None:
        parsed = _fallback_text_result(final_text)

    return _build_final_envelope(parsed, telemetry)

# 智能体流式响应
async def _stream_supervisor_response(
    request: Request,
    question: str,
    user_id: str,
    file_path: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    supervisor, telemetry = _build_supervisor_agent(request, user_id, file_path)
    user_content = _build_supervisor_input(question, file_path)
    parts: list[str] = []

    try:
        stream = supervisor.astream(
            {"messages": [{"role": "user", "content": user_content}]},
            stream_mode="messages",
        )

        async for message, metadata in stream:
            if hasattr(message, "tool_call_id"):
                continue

            content = getattr(message, "content", "")
            if isinstance(content, list):
                text = "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in content)
            else:
                text = str(content or "")

            if not text.strip():
                continue

            parts.append(text)
            yield _to_sse({
                "event": "chunk",
                "type": "text",
                "content": text,
                "meta": _build_observability(telemetry),
            })

        final_text = "".join(parts).strip()
        parsed = _extract_json_object(final_text)
        if parsed is None:
            parsed = _fallback_text_result(final_text)

        yield _to_sse({
            "event": "final",
            "type": parsed.get("type", "text"),
            "payload": parsed.get("payload", {"content": ""}),
            "meta": _build_observability(telemetry),
            "done": True,
        })
    except Exception as exc:
        logger.exception(f"supervisor stream error: {exc}")
        yield _to_sse({
            "event": "error",
            "content": f"聊天出错: {exc}",
            "meta": _build_observability(telemetry),
            "done": True,
            "error": True,
        })


@chat_router.get("/chat")
async def chat(request: Request, question: str, user_id: str, file_path: str = None):
    """
    主智能体非流式回退接口：主智能体编排子智能体后返回最终 envelope。
    """
    try:
        return await _invoke_supervisor_once(request, question, user_id, file_path)
    except Exception as exc:
        logger.exception(f"chat error: {exc}")
        return {
            "code": 500,
            "msg": str(exc),
            "data": None,
        }


@chat_router.get("/chat/stream")
async def chat_stream(request: Request, question: str, user_id: str, file_path: str = None):
    """
    主智能体流式接口：由主智能体边规划边调用子智能体，并把主智能体输出流式返回给前端。
    """
    return StreamingResponse(
        _stream_supervisor_response(request, question, user_id, file_path),
        media_type="text/event-stream",
    )


@chat_router.post("/upload")
async def upload(user_id: str = Form(...), file: UploadFile = File(...)):
    upload_dir = r"app\static\upload"
    os.makedirs(upload_dir, exist_ok=True)

    file_uuid = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    save_name = f"{file_uuid}{ext}"
    file_path = os.path.join(upload_dir, save_name)
    logger.info(f"上传文件：{file_path}")

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        print("文件保存成功")

    return {
        "code": 200,
        "data": {
            "file_path": file_path,
            "file_name": file.filename,
            "file_id": file_uuid,
        },
        "msg": "success",
    }
