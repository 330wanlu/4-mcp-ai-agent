PORT = 8102
TOOLS = ["get_session_summary", "upsert_user_preference"]


def describe() -> dict[str, object]:
    return {"name": "memory", "port": PORT, "tools": TOOLS, "phase": 0, "status": "skeleton"}


def main() -> None:
    print(f"[memory-mcp] placeholder port={PORT}")


if __name__ == "__main__":
    main()
