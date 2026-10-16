"""시계 손: 장면 0에서 "지금 몇 시야?"를 뒤집는 가장 작은 손."""
from datetime import datetime

from hands import hand


@hand("🕒")
def get_time() -> str:
    """Get the current local date and time."""
    now = datetime.now()
    return f"{now:%Y-%m-%d %H:%M} ({'월화수목금토일'[now.weekday()]}요일)"
