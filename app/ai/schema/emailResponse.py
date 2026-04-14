from pydantic import BaseModel, Field

class EmailResponseSchema(BaseModel):
    data: str = Field(..., description="验证码")
    code: str = Field(..., description="状态码 200成功 500失败")
    msg: str = Field(..., description="返回消息")