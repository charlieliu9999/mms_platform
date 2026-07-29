"""
medical-match-client — 匹配服务 Python SDK

Usage:
    from match_client import MatchClient

    client = MatchClient("http://localhost:9100")

    # 单条匹配
    result = await client.match("CT头部平扫", "CT")

    # 批量匹配
    results = await client.batch_match([
        {"key": "1", "name": "CT头部平扫", "modality": "CT"},
        {"key": "2", "name": "MR腰椎平扫", "modality": "MR"},
    ])

    # 同步版本（非 async 项目使用）
    sync_client = MatchClientSync("http://localhost:9100")
    result = sync_client.match("CT头部平扫", "CT")
"""
from .client import MatchClient, MatchClientSync

__all__ = ["MatchClient", "MatchClientSync"]
__version__ = "1.0.0"
