"""Knowledge MCP：hybrid_search / get_document_section / list_sources（阶段 1）。"""

PORT = 8101
TOOLS = ["hybrid_search", "get_document_section", "list_sources"]


def describe() -> dict[str, object]:
    return {
        "name": "knowledge",
        "port": PORT,
        "tools": TOOLS,
        "phase": 0,
        "status": "skeleton",
    }


def main() -> None:
    info = describe()
    print(f"[knowledge-mcp] phase={info['phase']} tools={info['tools']} port={info['port']}")
    print("阶段 1 将启动真实 MCP Server；当前仅为占位入口。")


if __name__ == "__main__":
    main()
