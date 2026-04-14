import os

from langchain.tools import tool
from pydantic import BaseModel, Field

from app.utils.Logger import Logger
from docx import Document
import time

from pathlib import Path

# 定义一个邮件工具的参数
class Args(BaseModel):
    content: str = Field(..., description="内容")
logger = Logger.get_logger(__name__)

@tool("docx_write_tool", args_schema=Args)
def docx_write_tool(content:str)-> str:
    """
    写入docx文件
    """
    doc = Document()
    # 写入标题
    doc.add_heading('分析报告', level=1)

    # 写入段落
    doc.add_paragraph(content)
    #用当前时间命名文件
    file_name =time.strftime("%Y%m%d%H%M%S", time.localtime())
    # app/
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    log_dir = BASE_DIR / "static\\download"
    log_dir.mkdir(exist_ok=True)

    #定义文件保存路径,web服务器路径写法
    file_path =log_dir / f"{file_name}.docx"
    #main 方法测试
    # file_path = os.getcwd() + f"\\{file_name}.docx"
    # 保存文档
    doc.save(file_path)
    #返回文件下载路径
    down_path =f"http://localhost:8000/static/download/{file_name}.docx"
    return f"下载路径:{down_path}"

if __name__ == "__main__":
    from docx import Document

    # 创建Word对象
    doc = Document()

    # 写入标题
    doc.add_heading('AI项目报告', level=1)

    # 写入段落
    doc.add_paragraph("本项目是一个基于大模型的智能问答系统。")

    doc.add_paragraph("系统采用 LangChain + Agent 架构。")

    # 保存文件
    doc.save("report.docx")