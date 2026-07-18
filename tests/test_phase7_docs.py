"""阶段 7：收尾文档与启动脚本就位检查（无 LLM）。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_has_start_and_demo_sections() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "start_local.ps1" in text
    assert "check_local_deps" in text
    assert "ARK_API_KEY" in text or "火山" in text
    assert "5173" in text and "8000" in text
    assert "demo-script.md" in text
    assert "architecture.md" in text
    assert "阶段 0–7" in text or "阶段 0-7" in text or "0–7" in text


def test_architecture_and_demo_script_exist() -> None:
    arch = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    demo = (ROOT / "docs" / "demo-script.md").read_text(encoding="utf-8")
    assert "PGVector" in arch or "PGVector" in arch
    assert "Chat Console" in arch or "chat-console" in arch.lower()
    assert "确认" in demo
    assert "试用期" in demo or "年假" in demo
    assert "demo_cli" in demo


def test_start_scripts_exist() -> None:
    scripts = ROOT / "scripts"
    for name in (
        "start_local.ps1",
        "dev_api.ps1",
        "dev_orchestrator.ps1",
        "dev_chat_console.ps1",
        "smoke_phase7.ps1",
        "demo_cli.py",
        "check_local_deps.py",
    ):
        path = scripts / name
        assert path.exists(), f"缺少脚本: {name}"
        assert path.stat().st_size > 20


def test_phase7_doc_exists() -> None:
    path = ROOT / "docs" / "阶段7-本地收尾与演示.md"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "阶段 7" in text
    assert "start_local" in text or "一键" in text
