from pydantic import BaseModel, Field

class DashboardResponse(BaseModel):
    code: int = Field(..., description="状态码")
    data: str = Field(..., description="图表数据")
    message: str = Field(..., description="分析结果")