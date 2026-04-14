import os

from langchain.tools import tool
from pydantic import BaseModel,Field
from app.utils.Logger import Logger
from docx import Document

class Args(BaseModel):
    path: str = Field(..., description="文件路径")

logger = Logger.get_logger(__name__)

@tool("docx_read_tool",args_schema=Args)
def docx_read_tool(path:str)-> str:
    """
    读取docx文件
    """
    doc = Document(path)
    data = []
    
    # 遍历表格
    for table in doc.tables:
        for row in table.rows:
            row_data = []
            for cell in row.cells:
                row_data.append(cell.text)
            data.append(row_data)
    return str(data)        

if __name__ == "__main__":
    print(os.path.exists(r"D:\PROJECT\AGENT_APP\app\static\upload\test.docx"))
    print(docx_read_tool.invoke({"path":r"D:\PROJECT\AGENT_APP\app\static\upload\test_table.docx"}))