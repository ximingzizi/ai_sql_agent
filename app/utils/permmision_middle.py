from langchain.agents.middleware import before_agent
from langchain.agents import AgentState
from langgraph.runtime import Runtime
from app.utils.Logger import Logger
from app.utils.permmision_role import permmision_role
logger = Logger.get_logger(__name__)



@before_agent
def before_agent_middleware(state:AgentState,runtime:Runtime):
    print(state)
    user_id = state['messages'][-1].user_id
    logger.info(f"用户{user_id}开始执行任务")
    role = permmision_role(user_id)
    if role==None:
        raise Exception("用户不存在")
    if role !="总经理":
        raise Exception("用户无权限执行任务")
    # 不做处理
    return None
