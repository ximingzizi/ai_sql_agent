import asyncio
from langchain.tools import tool
from app.utils.Logger import Logger
from app.ai.model.model import MyModel
from app.ai.tool.mysql_tool import mysql_tool
from app.ai.tool.send_email_tool import send_email
from app.ai.schema.emailResponse import EmailResponseSchema
from langchain.agents import create_agent  
from langgraph.checkpoint.memory import InMemorySaver # 内存记忆

logger = Logger.get_logger(__name__)

"""
sql 问答智能体
"""
class SqlQuestion:
    def __init__(self):
        self.model = MyModel.get_model()
        self.tools = self.__init_tools()
        self.agent = self.__my_agent()

    def __init_tools(self):
        self.tools = [mysql_tool]
        return self.tools
    
    # 创建智能体
    def __my_agent(self):  # 记得避免与库重名
        prompt = """
        一、你是一个SQL问答助手，你有一个工具mysql_tool，
        二、你的任务是根据问题给出一个SQL语句，然后调用mysql_tool函数，获取结果后给出回答
        """
        
        agent = create_agent(  # 创建智能体
            model=self.model,
            system_prompt=prompt,
            tools=self.tools,
            checkpointer=InMemorySaver(),  # 使用内存记忆
            # debug=True
        )
        return agent
    
    # 问答
    # question 问题    
    # #user_id 用户id

    async def answer(self, question: str, user_id: str):
        """
        你是一个SQL问答助手
        Args:
            question (str): 问题
            user_id (str): 用户id
        """

        res = self.agent.astream(
            {"messages": [{"role": "user", "content": question}]},
            {"configurable": {"thread_id": user_id}},
            stream_mode="messages"
        )

        async for msg, metadata in res:
            if not hasattr(msg,"tool_call_id"):
                yield msg.content
            
            
if __name__ == "__main__":
    print("测试智能体")
    newagent = SqlQuestion()
    async def main():
        async for c in newagent.answer("李四多少岁,在哪里","1"):
            print(c,end='')
    asyncio.run(main())
        























