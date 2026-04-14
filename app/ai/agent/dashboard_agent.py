import asyncio
import os

from app.utils.Logger import Logger
from app.ai.model.model import MyModel
from app.ai.tool.mysql_tool import mysql_tool
from app.ai.tool.dashboard_tool import dashboard_tool
from langchain.agents import create_agent  
from langgraph.checkpoint.postgres import PostgresSaver # postgres 记忆
from app.utils.permmision_middle import before_agent_middleware
from langchain.messages import HumanMessage
from app.ai.schema.dashboardResponse import  DashboardResponse

from dotenv import load_dotenv
load_dotenv()
logger = Logger.get_logger(__name__)

"""
多图表数据分析智能体
"""
class DashboardAgent():
    def __init__(self):
        self.model = MyModel.get_model()
        self.tools = self.__init_tools()

    def __init_tools(self):
        self.tools = [mysql_tool,dashboard_tool]
        return self.tools
    def answer(self, question: str, user_id: str):
        prompt = """
            你是一个专业的数据分析智能体，负责生成“多图表仪表盘”。

            你拥有两个工具：
            1. mysql_tool：用于查询数据库数据
            2. dashboard_tool：用于生成仪表盘HTML页面

            ------------------------
            【任务目标】
            根据用户需求，生成一个包含多个图表的仪表盘页面。

            ------------------------
            【执行流程】

            步骤1：分析用户需求
            - 判断需要哪些图表（趋势、占比、排名等）

            步骤2：调用 mysql_tool 获取数据
            - 必须先调用 mysql_tool
            - 严禁编造数据
            - 所有数据必须来自数据库

            步骤3：整理数据为标准JSON

            {
            "title": "仪表盘标题",
            "charts": [
                {
                "type": "line",
                "title": "销售额趋势",
                "x": [],
                "y": []
                },
                {
                "type": "pie",
                "title": "渠道占比",
                "data": [
                    {"name": "", "value": 0}
                ]
                },
                {
                "type": "bar",
                "title": "Top商品",
                "x": [],
                "y": []
                }
            ]
            }
            【字段规则】
            - line/bar：必须包含 x 和 y
            - pie：必须包含 data
            - x 和 y 长度必须一致
            - 所有字段不能为空
            - 数据必须真实有效

            步骤4：调用 dashboard_tool
            - 将 JSON 作为参数传入
            - 由 dashboard_tool 生成HTML页面

            ------------------------
            【图表选择规则】

            - 时间趋势 → line
            - 占比分析 → pie
            - 排名/Top → bar
            - 分类对比 → bar

            ------------------------
            【严格限制】
            你绝对不能：
            生成 HTML 代码
            输出 <html>、<script>、<div> 等标签
            编写 ECharts 配置代码
            修改或描述前端页面结构
            跳过 mysql_tool
            编造数据
            如果你生成了HTML代码，视为任务失败。
            ------------------------
            【唯一允许的输出】

            你最终只能输出：
            dashboard_tool 的调用结果

            不能输出任何解释、文本或代码
            ------------------------
            【示例】
            用户：
            创建一个销售分析仪表盘
            你的行为：
            1. 调用 mysql_tool
            2. 整理 JSON
            3. 调用 dashboard_tool
            4. 返回页面链接

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
                                 response_format=DashboardResponse, # 返回数据格式
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
    
    agent = DashboardAgent()
    res = agent.answer("请使用mysql_tool工具查询2023年9月份销售数据，做一个仪表盘分析。", "2953903954@qq.com")
    print(res)