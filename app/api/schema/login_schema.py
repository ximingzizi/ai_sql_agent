from pydantic import BaseModel,Field
"""登录接口的参数验证"""
class SendSchema(BaseModel):
    email: str = Field(..., description="邮箱")
    
class LoginSchema(BaseModel):
    email: str = Field(..., description="邮箱")
    code: str = Field(..., description="验证码")