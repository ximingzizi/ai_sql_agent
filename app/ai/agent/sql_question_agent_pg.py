import asyncio
import os

from app.utils.Logger import Logger
from app.ai.model.model import MyModel
from app.ai.tool.mysql_tool import mysql_tool
from langchain.agents import create_agent  
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver # postgres 记忆
from app.utils.permmision_middle import before_agent_middleware
from langchain.messages import HumanMessage

from dotenv import load_dotenv
load_dotenv()

logger = Logger.get_logger(__name__)

"""
sql (生产级)问答智能体
"""
class SqlQuestionPg:
    def __init__(self):
        self.model = MyModel.get_model()
        self.tools = self.__init_tools()

    def __init_tools(self):
        self.tools = [mysql_tool]
        return self.tools
    
    
    # 问答
    # question 问题    
    # #user_id 用户id
    async def answer(self, question: str, user_id: str):
        prompt = """
        一、你是一个SQL问答助手，你有一个工具mysql_tool，
        二、你的任务是根据问题给出一个SQL语句，然后调用mysql_tool函数，获取结果后给出回答
        重要规则：
            1. SQL生成规范:
   				- 只能使用SELECT查询，禁止使用INSERT/UPDATE/DELETE等修改操作
   			2. 查询原则:
   				- 涉及排名或TOP N时，必须使用ORDER BY和LIMIT
   				- 多表查询时使用正确的JOIN关系
        """
        user = os.getenv("POSTGRSSQL_USER")
        password = os.getenv("POSTGRSSQL_PASSWORD")
        host = os.getenv("POSTGRSSQL_HOST")
        db = os.getenv("POSTGRSSQL_DATABASE")
        
        url = f"postgresql://{user}:{password}@{host}:5432/{db}?sslmode=disable"
        # 创建一个智能体，采用asyncpostgressaver 异步处理流式
        async with AsyncPostgresSaver.from_conn_string(url) as pg:
            # 安装数据库和表
            await pg.setup()
            
            agent = create_agent(model=self.model,system_prompt = prompt,tools=self.tools,checkpointer=pg,middleware=[before_agent_middleware])
            # 构建一个HUmanMessage对象
            msg  = HumanMessage(content=question,user_id=user_id)
            try:
                res = agent.astream(
                    {"messages": [msg]},
                    {"configurable": {"thread_id": user_id}},
                    stream_mode="messages"
                )

                async for msg, metadata in res:
                    if not hasattr(msg,"tool_call_id"):
                        yield msg.content
            except Exception as e:
                logger.error(e)
                yield e 
            
if __name__ == "__main__":
    import asyncio
    import sys 
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    print("测试智能体")
    newagent = SqlQuestionPg()
    async def main():
        async for c in newagent.answer("李四多少岁,在哪里","2953903954@qq.com"):
            print(c,end='')
    asyncio.run(main())
        























