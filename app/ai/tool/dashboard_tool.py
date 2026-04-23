import json
from pathlib import Path
from langchain.tools import tool
import time
from app.utils.Logger import Logger

logger = Logger.get_logger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


@tool("dashboard_tool")
def dashboard_tool(data: dict) -> dict:
    """
    根据数据生成仪表盘HTML页面
    """
    try:
        if "charts" not in data or not isinstance(data["charts"], list):
            raise ValueError("data格式错误：缺少charts字段")

        template_path = BASE_DIR / "static" / "template" / "dashboard.html"
        save_dir = BASE_DIR / "static" / "dashboard"
        save_dir.mkdir(parents=True, exist_ok=True)

        with open(template_path, "r", encoding="utf-8") as f:
            html = f.read()

        # 统一改成模板占位，页面里再从 application/json 脚本节点读取。
        payload = json.dumps(data, ensure_ascii=False).replace("</script>", "<\\/script>")
        html = html.replace("{{dashboard_data_json}}", payload, 1)
        html = html.replace("{{dashboard_title}}", data.get("title", "数据仪表盘"), 1)

        file_name = f"dashboard_{int(time.time())}.html"
        file_path = save_dir / file_name

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html)

        url = f"http://localhost:8000/static/dashboard/{file_name}"

        return {
            "type": "dashboard",
            "url": url
        }

    except Exception as e:
        logger.error(f"生成仪表盘失败: {e}")
        return {"type": "error", "msg": str(e)}
