from contextlib import asynccontextmanager
import sys
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from app.utils.Logger import Logger
import uvicorn
from app.ai.agent.system_agent import SystemAgent
from app.ai.agent.sql_question_agent import SqlQuestion
from app.ai.agent.sql_question_agent_pg import SqlQuestionPg
from app.ai.agent.echarts_agent import EchartsAgent
from app.ai.agent.analyze_agent import AnalyzeAgent
from app.ai.agent.file_analyze_agent import  File_Analyze_Agent
from app.ai.agent.dashboard_agent import  DashboardAgent

from fastapi.middleware.cors import CORSMiddleware
from app.api.system.system_router import  router
from app.api.chat.chat_router import  chat_router

#创建日志实例
logger = Logger.get_logger(__name__)


#完成智能体的在服务器启动时候就创建
@asynccontextmanager
async def creat_agent_instance(app:FastAPI):
     app.state.agent = SystemAgent()
     app.state.sql_question_agent = SqlQuestion()
     app.state.sql_question_agent_pg = SqlQuestionPg()
     app.state.echarts_agent = EchartsAgent()
     app.state.analyze_agent = AnalyzeAgent()
     app.state.file_analyze_agent = File_Analyze_Agent()
     app.state.dashboard_agent = DashboardAgent()
     
     
     logger.info("创建系统/sql/pg/echarts/analyze/file/dashboard智能体实例成功")
     yield
     logger.info("系统/sql/pg/echarts/analyze/file/dashboard智能体实例销毁成功")

#创建FastAPI实例
app = FastAPI(lifespan=creat_agent_instance)
# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # 前端应用地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


#测试接口
# @app.get("/")
# def test():
#     info = "你好"
#     logger.info(f"测试接口:{info}")
#     return {"message": "Hello World"}
app.include_router(router)
app.include_router(chat_router)

if __name__ == "__main__":
    # uvicorn.run(app, host="localhost", port=8000)
    
    # chat error: Psycopg cannot use the 'ProactorEventLoop' to run in async mode. Please use a compatible event loop, for instance by running 'asyncio.run(..., loop_factory=asyncio.SelectorEventLoop(selectors.SelectSelector()))'
    cmd = [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--loop", "asyncio"]
    import subprocess
    subprocess.run(cmd)