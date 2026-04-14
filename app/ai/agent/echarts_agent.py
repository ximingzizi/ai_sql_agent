import asyncio
import os

from app.utils.Logger import Logger
from app.ai.model.model import MyModel
from app.ai.tool.mysql_tool import mysql_tool
from langchain.agents import create_agent  
from langgraph.checkpoint.postgres import PostgresSaver # postgres 记忆
from app.utils.permmision_middle import before_agent_middleware
from langchain.messages import HumanMessage
from app.ai.schema.echarts_response import EchartsResponseSchema

from dotenv import load_dotenv
load_dotenv()
logger = Logger.get_logger(__name__)

"""
echarts智能体
"""
class EchartsAgent:
    def __init__(self):
        self.model = MyModel.get_model()
        self.tools = self.__init_tools()

    def __init_tools(self):
        self.tools = [mysql_tool]
        return self.tools
    
    # 问答
    # question 问题    
    # #user_id 用户id
    def answer(self, question: str, user_id: str):
        prompt = """
               一: 你是一个echarts图表生成助手，你有一个工具
                   1 mysql_tool 执行sql查询
               二：工作流程：请严格按照下面格式回答问题
                    1 如果用户问图表生成，请先查询数据库，生成一个echarts图表，图表数据json格式必须是以下要求
                        返回的数据必须是一个可执行的json格式，其它的文本信息不需要
                        返回的图表必须有保存功能  
               三：重要规则
                    	1. **SQL生成规范**:
   				            - 只能使用SELECT查询，禁止使用INSERT/UPDATE/DELETE等修改操作
   			            2. **查询原则**:
   				            - 涉及排名或TOP N时，必须使用ORDER BY和LIMIT
   				            - 多表查询时使用正确的JOIN关系
   				            - 只查询前10条记录
   			   四：反馈信息
                    1  如果返回的json数据， 请返回状态码200，提示信息是；生成成功
                    2  如果未返回json数据， 请返回状态码500，提示信息是；生成失败
        """
        # 构建一个HUmanMessage对象
        msg  = HumanMessage(content=question,user_id=user_id)
        user = os.getenv("POSTGRSSQL_USER")
        password = os.getenv("POSTGRSSQL_PASSWORD")
        host = os.getenv("POSTGRSSQL_HOST")
        db = os.getenv("POSTGRSSQL_DATABASE")
        
        url = f"postgresql://{user}:{password}@{host}:5432/{db}?sslmode=disable"
        # 创建一个智能体，采用asyncpostgressaver 异步处理流式
        with PostgresSaver.from_conn_string(url) as pg:
            pg.setup()
            
            agent = create_agent(model=self.model,
                                 system_prompt = prompt,
                                 tools=self.tools,
                                 checkpointer=pg,
                                 response_format=EchartsResponseSchema, # 返回数据格式
                                 middleware=[before_agent_middleware]) # 中间件
            try:
                res = agent.invoke({"messages":[msg]},
                                    {"configurable":{"thread_id":user_id}}
                                    )
                data = res["structured_response"].model_dump()
                logger.info(data)
                return data
            except Exception as e:
                logger.error(e)
                return e
if __name__ == "__main__":
    print("测试智能体")
    newagent = EchartsAgent()
    print(newagent.answer("生成一个echarts图表，12月的销售金额", "2953903954@qq.com"))
        























