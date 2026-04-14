from langchain_openai import  ChatOpenAI
from dotenv import load_dotenv

import os
#读取环境变量
load_dotenv()
#用面向对象思想封装一个自定义的模型类
class MyModel:
    #设置聊天模型的私有属性
    _model = None

    #获取聊天模型，采用懒加载或者单例模型模式
    @staticmethod
    def get_model():
       if MyModel._model is None:
           model_name = os.getenv("MODEL_NAME")
           MyModel._model = ChatOpenAI(model=model_name,streaming=True)
       return MyModel._model
