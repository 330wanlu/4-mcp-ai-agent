PORT = 8103
TOOLS = ["create_ticket", "update_ticket", "create_document_draft"]


def describe() -> dict[str, object]:
    return {"name": "business", "port": PORT, "tools": TOOLS, "phase": 0, "status": "skeleton"}


def main() -> None:
    print(f"[business-mcp] placeholder port={PORT}")


if __name__ == "__main__":
    main()
