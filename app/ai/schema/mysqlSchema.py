from pydantic import BaseModel, Field

class MysqlSchema(BaseModel):
    sql: str = Field(..., description="SQL语句")