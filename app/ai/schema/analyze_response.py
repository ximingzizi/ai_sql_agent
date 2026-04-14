from pydantic import BaseModel, Field

"""
 表格响应类
"""
class TableResponse(BaseModel):
    column_name: list = Field(..., description="英文列名")
    data: list[dict[str,str]] = Field(..., description="数据")


"""
数据分析响应类
"""
class AnalyzeResponse(BaseModel):
    code: int = Field(..., description="状态码")
    table: TableResponse = Field(..., description="表格数据")
    result: str = Field(..., description="分析结果")
    json: str = Field(..., description="图表数据")
