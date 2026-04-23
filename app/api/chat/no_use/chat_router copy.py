import json
import uuid

from fastapi import APIRouter
from typing import AsyncGenerator, Optional
from pydantic import BaseModel, Field
import json
from app.utils.Logger import Logger
from app.ai.model.model import MyModel
from app.utils.Logger import Logger
from fastapi import Request
from fastapi.responses import StreamingResponse
from langchain.agents import create_agent
from langchain.tools import tool
model = MyModel.get_model()

logger  = Logger.get_logger(__name__)
chat_router = APIRouter()

# 创建聊天接口
@chat_router.get("/chat")
async def chat(request: Request, question: str, user_id: str,):
    
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
    async def generator(agent,question, user_id):
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
    return StreamingResponse(generator(agent), media_type="text/event-stream")


from fastapi import  UploadFile, File,Form
import os
@chat_router.post("/upload")
async def upload(user_id: str = Form(...),file: UploadFile = File(...)):
    # 上传目录
    UPLOAD_DIR = r"app\static\upload"
    # 创建上传目录
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    # 生成唯一文件ID
    file_uuid = str(uuid.uuid4())
    # 获取文件扩展名
    ext = os.path.splitext(file.filename)[1]
    save_name = f"{file_uuid}{ext}"
    # 创建文件路径
    file_path = os.path.join(UPLOAD_DIR, save_name)
    logger.info(f"上传文件：{file_path}")
    # 保存文件
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
        print("文件保存成功")
    return {
        "code": 200,
        "data": {
            "file_path": file_path,
            "file_name": file.filename,
            "file_id": file_uuid  
        },
        "msg": "success"
    }