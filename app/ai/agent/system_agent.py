from app.utils.Logger import Logger
from app.ai.model.model import MyModel
from app.ai.tool.mysql_tool import mysql_tool
from app.ai.tool.send_email_tool import send_email
from app.ai.schema.emailResponse import EmailResponseSchema
from langchain.agents import create_agent  
logger = Logger.get_logger(__name__)

"""
登录验证码智能体
"""
class SystemAgent:
    # 初始化智能体
    def __init__(self):
        logger.info("初始化登录验证码智能体")
        self.model = MyModel.get_model()
        self.tools = self.init_tools()
        self.agent = self.my_agent()
        
    # 初始化工具
    def init_tools(self):
        self.tools = [mysql_tool, send_email]
        return self.tools
    # 创建智能体
    def my_agent(self):  # 记得避免与库重名
        # 创建提示词
        prompt = """
        一、你是一个邮件发送助手，你有两个工具，一个是mysql_tool，一个是send_email_tool，
        mysql_tool是一个函数，接收一个参数sql，返回一个结果
        send_email_tool是一个函数，接收三个参数to_email,subject,content，返回一个结果
        二、你的任务是：
        1. 根据问题给出一个SQL语句，然后调用mysql_tool函数，验证邮箱是否存在。
        2. 生成一个4位数的完全随机的验证码，然后调用send_email_tool函数，发送到邮件中。
        3. 如果无法完成，请给出一个错误信息。
        三、请严格按照以下格式返回结果：
        如果mysql_tool查询失败，则返回：
        验证码 0 ,状态码 500，失败原因为邮箱未注册
        如果send_email_tool发送邮件失败，则返回：
        状态码 500，并说明失败原因
        如果send_email_tool发送邮件成功，则返回：
        状态码 200，并返回验证码
        
        """
        self.agent = create_agent(self.model, system_prompt=prompt,debug=True,tools=self.tools,response_format=EmailResponseSchema)
        return self.agent
    # 运行智能体
    def answer(self, question: str) -> str:
        res = self.agent.invoke({"messages": [{"role": "user", "content": question}]})
        answer= res["structured_response"].model_dump()
        logger.info(f"智能体返回结果: {answer}")
        return answer
    
if __name__ == "__main__":
    agent = SystemAgent()
    print(agent.answer("请发送一个验证码到2953903954@qq.com"))