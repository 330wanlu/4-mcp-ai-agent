#!/usr/bin/env python3
"""检查本机 PostgreSQL（含 PGVector）与 Redis 是否可用。

用法:
  uv run python scripts/check_local_deps.py

期望输出含: postgres ok / vector ok / redis ok
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, unquote

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _parse_database_url(url: str) -> dict[str, str | int]:
    """解析 postgresql+psycopg:// 或 postgresql:// URL。"""
    normalized = url.replace("postgresql+psycopg://", "postgresql://", 1)
    normalized = normalized.replace("postgres+psycopg://", "postgresql://", 1)
    parsed = urlparse(normalized)
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise ValueError(f"DATABASE_URL scheme 不支持: {parsed.scheme}")
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "user": unquote(parsed.username or "postgres"),
        "password": unquote(parsed.password or ""),
        "dbname": (parsed.path or "/postgres").lstrip("/") or "postgres",
    }


def check_postgres(database_url: str) -> list[CheckResult]:
    results: list[CheckResult] = []
    try:
        import psycopg
    except ImportError as exc:
        return [CheckResult("postgres", False, f"未安装 psycopg: {exc}")]

    try:
        params = _parse_database_url(database_url)
    except Exception as exc:  # noqa: BLE001
        return [CheckResult("postgres", False, f"DATABASE_URL 解析失败: {exc}")]

    connect_kwargs = {
        "host": params["host"],
        "port": params["port"],
        "user": params["user"],
        "password": params["password"],
        "dbname": params["dbname"],
        "connect_timeout": 5,
    }

    # 1) 连通性（目标库可能尚未创建，先连 postgres 系统库再试目标库）
    try:
        try:
            conn = psycopg.connect(**connect_kwargs)
            connected_db = str(params["dbname"])
        except psycopg.OperationalError as target_err:
            # 数据库不存在时，退回连 postgres 验证账号与服务
            fallback = dict(connect_kwargs)
            fallback["dbname"] = "postgres"
            try:
                conn = psycopg.connect(**fallback)
                connected_db = "postgres"
                results.append(
                    CheckResult(
                        "postgres",
                        True,
                        f"服务可连（当前连到 postgres；目标库 {params['dbname']!r} 尚未创建: {target_err}）",
                    )
                )
            except Exception:
                raise target_err from None
        else:
            results.append(
                CheckResult(
                    "postgres",
                    True,
                    f"已连接 {params['user']}@{params['host']}:{params['port']}/{connected_db}",
                )
            )

        # 2) vector 扩展
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT installed_version, default_version "
                    "FROM pg_available_extensions WHERE name = 'vector'"
                )
                row = cur.fetchone()
                if row is None:
                    results.append(
                        CheckResult(
                            "vector",
                            False,
                            "未找到 vector 扩展（请安装 PGVector，并确保与本机 Postgres 版本匹配）",
                        )
                    )
                else:
                    installed, default_ver = row
                    if installed:
                        results.append(
                            CheckResult("vector", True, f"已启用 version={installed}")
                        )
                    else:
                        # 尝试 CREATE EXTENSION（需要权限）
                        try:
                            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                            conn.commit()
                            cur.execute(
                                "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
                            )
                            ver = cur.fetchone()
                            results.append(
                                CheckResult(
                                    "vector",
                                    True,
                                    f"已自动 CREATE EXTENSION vector version={ver[0] if ver else default_ver}",
                                )
                            )
                        except Exception as ext_err:  # noqa: BLE001
                            results.append(
                                CheckResult(
                                    "vector",
                                    False,
                                    f"扩展文件可用(default={default_ver})但 CREATE 失败: {ext_err}",
                                )
                            )
        conn.close()
    except Exception as exc:  # noqa: BLE001
        results.append(CheckResult("postgres", False, str(exc)))
        if not any(r.name == "vector" for r in results):
            results.append(CheckResult("vector", False, "因 postgres 连接失败跳过"))

    return results


def check_redis(redis_url: str) -> CheckResult:
    try:
        import redis
    except ImportError as exc:
        return CheckResult("redis", False, f"未安装 redis-py: {exc}")

    try:
        client = redis.Redis.from_url(redis_url, socket_connect_timeout=3)
        pong = client.ping()
        if pong:
            return CheckResult("redis", True, f"PING ok ({redis_url})")
        return CheckResult("redis", False, f"PING 返回异常: {pong!r}")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("redis", False, str(exc))


def _safe_text(text: str) -> str:
    """避免 Windows 控制台 GBK 打印异常字符导致脚本崩溃。"""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def main() -> int:
    # 尽量让 stdout 使用 UTF-8（Windows 终端仍可能是 GBK）
    try:
        sys.stdout.reconfigure(errors="replace")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass

    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/mcp_agent_db",
    )
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    print("=== check_local_deps ===")
    print(f"DATABASE_URL={database_url}")
    print(f"REDIS_URL={redis_url}")
    print()

    results: list[CheckResult] = []
    results.extend(check_postgres(database_url))
    results.append(check_redis(redis_url))

    all_ok = True
    for r in results:
        status = "ok" if r.ok else "FAIL"
        print(_safe_text(f"[{status}] {r.name}: {r.detail}"))
        all_ok = all_ok and r.ok

    print()
    if all_ok:
        print("结果: postgres ok / vector ok / redis ok")
        return 0

    print("结果: 存在失败项。请根据上方详情安装/启动服务，并检查 .env 中的账号密码。")
    print("提示:")
    print("  1) 复制 .env.example 为 .env，填入真实 Postgres 密码")
    print("  2) 确认目标库已创建（本机约定: mcp_agent_db）")
    print("  3) 安装并启动 Redis / Memurai（Windows 本机: E:\\AI\\Memurai，端口 6379）")
    print("  4) 安装 PGVector 扩展（归档可参考 E:\\AI\\PGVector_18）并 CREATE EXTENSION vector")
    return 1


if __name__ == "__main__":
    sys.exit(main())
