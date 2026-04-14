from fastapi import APIRouter
from app.api.schema.login_schema import SendSchema,LoginSchema
from app.utils.Logger import Logger
from fastapi import Request
import redis

# 创建Redis连接
redis_client= redis.StrictRedis(host='localhost', port=6379, db=0)
# 创建APIRouter实例
router = APIRouter()

logger = Logger.get_logger(__name__)

@router.post("/send_email")
def send_email(request: Request, send_data: SendSchema):
    # 获取web服务创建的智能体实例对象
    agent= request.app.state.agent
    res = agent.answer(f"请发送一个验证码到{send_data.email}")
    # 存储验证码
    redis_client.set(f"{send_data.email}:code", res['data'], ex=60)  # 设置验证码过期时间为1分钟
    logger.info(f"用户{send_data.email}请求发送验证码，结果: {res}")
    return {"code": res["code"], "msg": res["msg"]}

@router.post("/login")
def login(args: LoginSchema):
    # 获取验证码
    logger.info(f"字节码：{redis_client.get(f'{args.email}:code')}")
    try:
        code = redis_client.get(f"{args.email}:code").decode()  # 获取字节码并解码为字符串
        if code == args.code:
            return {"code": "200", "msg": "登录成功"}
        return {"code": "500", "msg": "登录失败"}
    except Exception as e:
        logger.warning(f"验证码错误或未获取: {e}")
        return {"code": "500", "msg": "验证码错误或信息不完整，请重新获取"}