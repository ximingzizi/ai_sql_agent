from langchain.tools import tool
from app.ai.schema.mysqlSchema import MysqlSchema
from dotenv import load_dotenv
import os
import pymysql
from app.utils.Logger import Logger
logger = Logger.get_logger(__name__)
#加载环境变量
load_dotenv()
@tool("mysql_tool", args_schema=MysqlSchema)
def mysql_tool(sql:str)-> str:
    """
一、数据库表结构
数据库包含以下数据表：

1. customer（客户信息表）
字段：
user_id BIGINT 用户ID
username TEXT 用户名
registration_date TEXT 注册日期
country TEXT 国家
age BIGINT 年龄
gender TEXT 性别
total_spent DOUBLE 总消费金额
order_count BIGINT 订单数量

2. customer_behavior（用户行为表）
字段：
user_id BIGINT 用户ID
product_id BIGINT 商品ID
action TEXT 行为类型（浏览、点击、购买等）
action_date TEXT 行为日期
device TEXT 设备类型

3. orders（订单表）
字段：
order_id BIGINT 订单ID
user_id BIGINT 用户ID
order_date TEXT 订单日期
product_id BIGINT 商品ID
quantity BIGINT 购买数量
total_amount DOUBLE 订单金额
payment_method TEXT 支付方式
order_status TEXT 订单状态

4. products（商品表）
字段：
product_id BIGINT 商品ID
product_name TEXT 商品名称
category TEXT 商品分类
price DOUBLE 商品价格
stock BIGINT 库存
sales_volume BIGINT 销量
average_rating DOUBLE 平均评分

5. sales（销售统计表）
字段：
year TEXT 年份
total_sales DOUBLE 总销售额
total_orders BIGINT 总订单数
total_quantity_sold BIGINT 总销量
category TEXT 商品分类
average_order_value DOUBLE 平均订单金额

6. user_info（用户信息表）
字段
user_id int 用户ID
user_name varchar 用户名
email varchar 邮箱
role varchar 角色

------------------------------------------------
二、表关系
customer.user_id = orders.user_id
orders.product_id = products.product_id
customer.user_id = customer_behavior.user_id
customer_behavior.product_id = products.product_id
    """
    
    try:
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
       #执行sql
       cursor.execute(sql)
       #获取结果
       result = cursor.fetchall()
       logger.info(f"查询结果: {result}")
       return str(result)
    except Exception as e:
        logger.debug(f"查询失败: {e}")
        return "查询失败"
    
    
