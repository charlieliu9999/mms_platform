"""
匹配服务客户端 — 异步 + 同步双模式

对外屏蔽 HTTP 细节，提供类型安全的匹配接口。
"""
from typing import List, Optional

import httpx


class MatchClient:
    """异步匹配客户端（适用于 FastAPI / asyncio 项目）"""

    def __init__(
        self,
        base_url: str = "http://localhost:9100",
        timeout: float = 300.0,
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._headers = {}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

    async def match(self, name: str, modality: str, version: str = "V3.8.2") -> dict:
        """单条匹配"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/match",
                json={"name": name, "modality": modality, "version": version},
                headers=self._headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("result", data)

    async def batch_match(
        self, items: List[dict], version: str = "V3.8.2"
    ) -> dict:
        """批量匹配

        Args:
            items: [{"key": "id1", "name": "CT头部平扫", "modality": "CT"}, ...]

        Returns:
            {"results": {...}, "stats": {...}, "rule_version": "..."}
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/batch-match",
                json={"items": items, "version": version},
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def reload(self) -> dict:
        """热重载词库/标准库"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/reload", headers=self._headers
            )
            resp.raise_for_status()
            return resp.json()

    async def health(self) -> dict:
        """健康检查"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self.base_url}/health", headers=self._headers
            )
            resp.raise_for_status()
            return resp.json()

    async def submit_feedback(
        self,
        text: str,
        modality: str,
        correct_result: Optional[dict] = None,
        comment: Optional[str] = None,
    ) -> dict:
        """提交匹配反馈（人工修正 / 错误报告）"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/feedback",
                json={
                    "text": text,
                    "modality": modality,
                    "correct_result": correct_result,
                    "comment": comment,
                },
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def cache_stats(self) -> dict:
        """获取映射库统计"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{self.base_url}/cache/stats", headers=self._headers
            )
            resp.raise_for_status()
            return resp.json()


class MatchClientSync:
    """同步匹配客户端（适用于 Django / Flask / 脚本等非 async 项目）"""

    def __init__(
        self,
        base_url: str = "http://localhost:9100",
        timeout: float = 300.0,
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._headers = {}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

    def match(self, name: str, modality: str, version: str = "V3.8.2") -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/match",
                json={"name": name, "modality": modality, "version": version},
                headers=self._headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("result", data)

    def batch_match(self, items: List[dict], version: str = "V3.8.2") -> dict:
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/batch-match",
                json={"items": items, "version": version},
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()

    def reload(self) -> dict:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{self.base_url}/reload", headers=self._headers)
            resp.raise_for_status()
            return resp.json()

    def health(self) -> dict:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{self.base_url}/health", headers=self._headers)
            resp.raise_for_status()
            return resp.json()

    def submit_feedback(
        self,
        text: str,
        modality: str,
        correct_result: Optional[dict] = None,
        comment: Optional[str] = None,
    ) -> dict:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{self.base_url}/feedback",
                json={
                    "text": text,
                    "modality": modality,
                    "correct_result": correct_result,
                    "comment": comment,
                },
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json()
