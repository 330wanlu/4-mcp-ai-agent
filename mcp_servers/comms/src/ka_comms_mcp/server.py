PORT = 8104
TOOLS = ["send_notification", "post_channel_message"]


def describe() -> dict[str, object]:
    return {"name": "comms", "port": PORT, "tools": TOOLS, "phase": "phase2+", "status": "placeholder"}


def main() -> None:
    print("[comms-mcp] 二期占位，当前不启动。")


if __name__ == "__main__":
    main()
