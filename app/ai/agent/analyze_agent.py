import asyncio
import os

from app.utils.Logger import Logger
from app.ai.model.model import MyModel
from app.ai.tool.mysql_tool import mysql_tool
from langchain.agents import create_agent  
from langgraph.checkpoint.postgres import PostgresSaver # postgres 记忆
from app.utils.permmision_middle import before_agent_middleware
from langchain.messages import HumanMessage
from app.ai.schema.analyze_response import  AnalyzeResponse

from dotenv import load_dotenv
load_dotenv()
logger = Logger.get_logger(__name__)

"""
数据智能分析智能体
"""
class AnalyzeAgent:
    def __init__(self):
        logger.info("初始化智能分析智能体")
        self.model = MyModel.get_model()
        self.tools = self.__init_tools()

    def __init_tools(self):
        self.tools = [mysql_tool]
        return self.tools
    def answer(self, question: str, user_id: str):
        prompt = """
        一、你是一个数据分析智能体，你有一个工具：mysql_tool。
        二、工作流程：严格按照一下的步骤进行：
            1. 使用mysql_tool工具进行数据查询，结果以表格格式存入。
            2. 根据问题做出分析。按照以下的格式进行，分析结果存入分析结果：
                一、详细分析
                    1 XXXX：
                        XXXX
                        XXXX
                二、结论部分
                    1. XXXX：
                        XXXX
                        XXXX
            3. 绘制echarts图表，图表数据json格式必须是以下要求，把数据存入echarts图表中。
                1 如果返回的JSON数据，请返回状态码200，提示：生成成功
                2 如果未返回JSON数据，请返回状态码500，提示：生成失败
                3 返回的数据必须是一个可执行的json格式，其它的文本信息不需要
                4 返回的图表必须有保存功能      
        三：重要规则
                1. **SQL生成规范**:
                    - 只能使用SELECT查询，禁止使用INSERT/UPDATE/DELETE等修改操作
                2. **查询原则**:
                    - 涉及排名或TOP N时，必须使用ORDER BY和LIMIT
                    - 多表查询时使用正确的JOIN关系
                    - 只查询前10条记录
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
                                 response_format=AnalyzeResponse, # 返回数据格式
                                 middleware=[before_agent_middleware]) # 中间件
            try:
                res = agent.invoke({"messages":[msg]},
                                    {"configurable":{"thread_id":user_id}}
                                    )
                data = res["structured_response"].model_dump()
                if data is None:
                    raise ValueError("structured_response missing")

                logger.info(data)
                return data
            except Exception as e:
                logger.error(e)
                return e
            
            
if __name__ == "__main__":
    agent = AnalyzeAgent()
    res = agent.answer("请使用mysql_tool工具查询3月销售数据，并返回echarts图表数据，并返回分析结果。", "2953903954@qq.com")
    print(res)