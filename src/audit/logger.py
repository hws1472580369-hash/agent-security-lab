from pathlib import Path
from datetime import datetime


def log_event(agent_id, tool_name, arguments, allowed, reason):

    log_dir = Path("data")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "audit.log"

    timestamp = datetime.now().isoformat()

    log_message = (
        f"[{timestamp}] "
        f"agent={agent_id} "
        f"tool={tool_name} "
        f"arguments={arguments} "
        f"allowed={allowed} "
        f"reason={reason}\n"
    )

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_message)

    print(log_message.strip())