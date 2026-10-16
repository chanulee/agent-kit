"""시계 도구. "지금 몇 시야?"처럼 말만으로는 알 수 없는 것을 확인하는 가장 작은 도구."""
from datetime import datetime

from tools import tool


@tool("🕒", group="기타")
def get_time() -> str:
    """Get the current local date and time."""
    now = datetime.now()
    return f"{now:%Y-%m-%d %H:%M} ({'월화수목금토일'[now.weekday()]}요일)"
