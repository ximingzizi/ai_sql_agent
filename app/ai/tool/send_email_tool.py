from langchain.tools import tool
import smtplib
from email.mime.text import MIMEText
from app.ai.schema.emailSchema import EmailSchema
from dotenv import load_dotenv
import os
load_dotenv()

from app.utils.Logger import Logger
logger = Logger.get_logger(__name__)

@tool("send_email", args_schema=EmailSchema)
def send_email(to_email: str, subject: str, content: str) -> str:
    """
    发送邮件
    """
    try:
        msg = MIMEText(content)
        msg["Subject"] = subject
        msg["From"] = os.getenv("EMAIL_USER")
        msg["To"] = to_email
        server = smtplib.SMTP_SSL("smtp.qq.com", 465)
        server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
        # 发送邮件
        # 参数1：发件人邮箱
        # 参数2：收件人邮箱
        # 参数3：邮件对象转字符串
        server.sendmail(msg["From"], to_email, msg.as_string())
        
        server.quit()
        logger.info("邮件发送成功")
        return "邮件发送成功"
    except Exception as e:
        logger.debug(f"邮件发送失败: {e}")
        return "邮件发送失败"