import asyncio
import os
from pathlib import Path

from app.utils.Logger import Logger
from app.ai.model.model import MyModel
from app.ai.tool.docx_read_tool import docx_read_tool
from app.ai.tool.docx_write_tool import docx_write_tool
from langchain.agents import create_agent  
from langchain.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
load_dotenv()
logger = Logger.get_logger(__name__)

"""
文件分析智能体
"""
class File_Analyze_Agent():
    def __init__(self):
        logger.info("初始化智能分析智能体")
        self.model = MyModel.get_model()
        self.tools = self.__init_tools()

    def __init_tools(self):
        self.tools = [docx_read_tool, docx_write_tool]
        return self.tools
    
    # question问题格式: 上传文件成功: test.docx
    async def answer(self, question: str,user_id: str):
        prompt = """
        一、你是一个文件分析助手，你有两个工具：
            1. docx_read_tool: 读取docx文件
            2. docx_write_tool: 写入docx文件，返回处理后文件地址
        二、你的任务是：
            1. 读取用户上传的docx文件，文件路径是:{path}
            2 请分析一下文件内容，查看是否有数据缺失和数据重复，如果有，填充缺失值，缺失值填充：None，删除数据重复
            3 调用 docx_write_tool 工具 将分析后的数据写入到文档中，返回处理后文件的地址
        三、反馈信息
            1. 请将分析的结果反馈给用户
        """
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
        # 上传目录路径
        upload_dir = BASE_DIR / "static\\upload"
        # 获取文件路径
        path = os.path.join(upload_dir, question.split(":")[1].strip())
        logger.info(f"文件路径：{path}")
        # 模板化提示词
        prompt_template = PromptTemplate.from_template(prompt)
        prompt = prompt_template.format(path=path)
        
        # 构建一个HUmanMessage对象
        msg  = HumanMessage(content=question)
        agent = create_agent(model=self.model,
                                system_prompt = prompt,
                                tools=self.tools,)
        async for c,m in agent.astream({"messages":[msg]},stream_mode="messages"):
            if not hasattr(c,"tool_call_id"): 
                yield c.content
                
if __name__ == "__main__":
    agent = File_Analyze_Agent()
    async def main():
        async for c in agent.answer("文件上传成功: test_table.docx"):
            print(c)
    asyncio.run(main())
