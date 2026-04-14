from pydantic import BaseModel, Field

'''
echarts 图表响应类
'''
class EchartsResponseSchema(BaseModel):
    json: str = Field(..., description="json 数据")
    code: int = Field(..., description="状态码")
    msg: str = Field(..., description="返回消息")
