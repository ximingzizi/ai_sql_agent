from langchain.tools import tool
from app.ai.schema.mysqlSchema import MysqlSchema
from dotenv import load_dotenv
import os
import pymysql
from app.utils.Logger import Logger

logger = Logger.get_logger(__name__)
#加载环境变量
load_dotenv()
def permmision_role(user_id:str)-> bool:
    """
    权限控制函数，判断用户是否有权限执行SQL
    目前简单实现为只有user_id为1的用户有权限执行SQL
    后续可以根据实际需求进行扩展，比如根据用户角色、SQL类型等进行权限控制
    """
    sql = f"SELECT role FROM user_info WHERE email = '{user_id}'"
    #创建链接
    con = pymysql.connect(
           host=os.getenv("MYSQL_HOST"),
           port=int(os.getenv("MYSQL_PORT")),
           user=os.getenv("MYSQL_USER"),
           password=os.getenv("MYSQL_PASSWORD"),
           database=os.getenv("MYSQL_DB")
       )
    #创建游标
    cursor = con.cursor()
    try:    
       #执行sql
       cursor.execute(sql)
       #获取结果
       result = cursor.fetchall()
       if len(result) > 0:
           return result[0][0]
       else:
           return None
    except Exception as e:
        logger.debug(f"查询失败: {e}")
        return "查询失败"
    finally:
        #关闭游标
        cursor.close()
        #关闭链接
        con.close()
if __name__ == "__main__":
    re = permmision_role("2953903954@qq.com")
    print(re)