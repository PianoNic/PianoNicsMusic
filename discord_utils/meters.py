def bar(percent: int, step: int = 10, width: int = 10) -> str:
    filled = min(width, max(0, percent // step))
    return "█" * filled + "░" * (width - filled)
