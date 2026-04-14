import json

from fastapi import APIRouter

from app.utils.Logger import Logger
from fastapi import Request
from fastapi.responses import StreamingResponse


logger  = Logger.get_logger(__name__)
chat_router = APIRouter()

# 创建聊天接口
@chat_router.get("/chat")
async def chat(request: Request, question: str, user_id: str):
    # 根据用户问题判断使用的智能体
    if "仪表盘" in question:
        agent = request.app.state.dashboard_agent
        return agent.answer(question, user_id)
    elif "图表" in question:
        agent = request.app.state.echarts_agent
        return agent.answer(question, user_id)
    elif "数据分析" in question:
        agent = request.app.state.analyze_agent
        data  = agent.answer(question, user_id)
        print("数据分析的数据：",data,type(data))
        return {"code":data.get("code", 500), "data":data, "msg":"未知错误"}
    else:
        if "文件上传成功" in question:
            agent = request.app.state.file_analyze_agent
        else:
            agent = request.app.state.sql_question_agent_pg

    # 创建一个迭代器
    async def generator():
        try:
            async for res in agent.answer(question, user_id):
                msg= {"content":res,"done":False}
                yield f"data:{json.dumps(msg)}\n\n"
            # 迭代结束
            msg = {"content":"","done":True}    
            yield f"data:{json.dumps(msg)}\n\n"
        except Exception as e:
            logger.warning(f"my_chaterror: {e}")
            msg = {"content":"聊天出错","done":True,"error":True}
            yield f"data:{json.dumps(msg)}\n\n"
    return StreamingResponse(generator(), media_type="text/event-stream")

from fastapi import  UploadFile, File
import os
@chat_router.post("/upload")
async def upload(file: UploadFile = File(...)):
    # 上传目录
    UPLOAD_DIR = "static/upload"
    # 创建上传目录
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    # 创建文件路径
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    logger.info(f"上传文件：{file_path}")
    # 保存文件
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    return {
        "code": 200,
        "filename": file.filename
    }