import asyncio
from threading import Thread

from app.utils.Logger import Logger
from app.ai.model.model import MyModel
from app.ai.tool.docx_read_tool import file_read_tool
from app.ai.tool.docx_write_tool import file_write_tool
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
        self.tools = [file_read_tool, file_write_tool]
        return self.tools
    
    # question问题格式: 上传文件成功: test.docx

    async def answer(self, question: str,file_path: str,user_id: str=None):
        """
        智能文件分析
        输入：
        question: 问题
        user_id: 用户id
        """
        # ===== 旧提示词（保留对照）=====
        # prompt = """
        # 一、你是一个文件分析助手，你有两个工具：
        #     1. docx_read_tool: 读取docx文件
        #     2. docx_write_tool: 写入docx文件，返回处理后文件地址
        # 二、你的任务是：
        #     1. 读取用户上传的docx文件，文件路径是:{path}
        #     2 请分析一下文件内容，查看是否有数据缺失和数据重复，如果有，填充缺失值，缺失值填充：None，删除数据重复
        #     3 调用 docx_write_tool 工具 将分析后的数据写入到文档中，返回处理后文件的地址
        # 三、反馈信息
        #     1. 请将分析的结果反馈给用户
        # """
        #
        # 旧提示词里的工具名和真实注册名不一致，模型会优先尝试调用不存在的 docx_read_tool / docx_write_tool，
        # 这正是文件分析场景里工具调用经常失败的原因之一。
        prompt = """
        一、你是一个文件分析助手，你只能使用下面两个真实工具名：
            1. file_read_tool: 读取用户上传文件的内容
            2. file_write_tool: 将处理后的结果写入新文件并返回下载地址
        二、你的任务是：
            1. 先调用 file_read_tool 读取文件，文件路径是：{path}
            2. 分析文件内容，检查是否存在缺失数据或重复数据
            3. 如果发现缺失数据，使用 None 明确标记；如果发现重复数据，删除重复项
            4. 将清洗结果和分析结论整理成可读文本
            5. 调用 file_write_tool 生成一个 docx 文件，file_type 必须传 docx
        三、输出要求：
            1. 先简要说明你做了什么清洗/检查
            2. 再返回 file_write_tool 生成的文件地址
            3. 不要伪造工具结果，所有文件内容都必须来自 file_read_tool
        """

        path = file_path
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

    def answer_sync(self, question: str, file_path: str, user_id: str = None) -> str:
        """
        把文件分析子智能体包装成同步调用，便于主智能体按工具方式编排。
        """
        result = {
            "content": "",
            "error": "",
        }

        async def collect():
            prompt = """
            一、你是一个文件分析助手，你只能使用下面两个真实工具名：
                1. file_read_tool: 读取用户上传文件的内容
                2. file_write_tool: 将处理后的结果写入新文件并返回下载地址
            二、你的任务是：
                1. 先调用 file_read_tool 读取文件，文件路径是：{path}
                2. 分析文件内容，检查是否存在缺失数据或重复数据
                3. 如果发现缺失数据，使用 None 明确标记；如果发现重复数据，删除重复项
                4. 将清洗结果和分析结论整理成可读文本
                5. 调用 file_write_tool 生成一个 docx 文件，file_type 必须传 docx
            三、输出要求：
                1. 先简要说明你做了什么清洗/检查
                2. 再返回 file_write_tool 生成的文件地址
                3. 不要伪造工具结果，所有文件内容都必须来自 file_read_tool
            """
            prompt = PromptTemplate.from_template(prompt).format(path=file_path)
            msg = HumanMessage(content=question)
            agent = create_agent(model=self.model, system_prompt=prompt, tools=self.tools)
            parts = []
            async for c, m in agent.astream({"messages": [msg]}, stream_mode="messages"):
                if not hasattr(c, "tool_call_id"):
                    text = "" if c.content is None else str(c.content)
                    if text:
                        parts.append(text)
            result["content"] = "".join(parts).strip()

        def runner():
            try:
                asyncio.run(collect())
            except Exception as exc:
                result["error"] = str(exc)

        thread = Thread(target=runner, daemon=True)
        thread.start()
        thread.join()

        if result["error"]:
            raise RuntimeError(result["error"])

        return {
            "content": result["content"],
        }
                
if __name__ == "__main__":
    agent = File_Analyze_Agent()
    async def main():
        async for c in agent.answer("告诉我文件的内容","app\\static\\upload\\bc93b020-8ffc-46bd-9eaf-fbf4fbdf0f5a"):
            print(c)
    asyncio.run(main())
