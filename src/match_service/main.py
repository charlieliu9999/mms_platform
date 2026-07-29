"""
medical-match-service — 独立医学影像检查项目标准匹配服务

三层架构：
  L1: 映射库（已确认映射，O(1) hash 命中）
  L2: 算法引擎（NLP pipeline + 关键词引擎）
  L3: Agent 审核 + 进化（异步）

启动：
  cd match_service
  poetry install
  poetry run uvicorn match_service.main:app --host 0.0.0.0 --port 9100 --reload
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.legacy import legacy_router
from .api.routes import router
from .api.admin import router as admin_router
from .api.evaluation import router as evaluation_router
from .config import get_settings
from .core.engine_holder import get_engine_holder
from .db import get_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"[{settings.APP_NAME}] v{settings.APP_VERSION} 启动中...")

    # 数据库 schema 演进由 Alembic 管理，不再在启动时自动 create_all。
    # 首次部署前需手动执行：alembic upgrade head
    # 后续 schema 变更：alembic revision --autogenerate -m "..." && alembic upgrade head

    holder = get_engine_holder()
    await holder.initialize()

    logger.info(f"[{settings.APP_NAME}] 就绪, 端口={settings.PORT}")
    yield
    await holder.dispose()
    logger.info(f"[{settings.APP_NAME}] 已关闭")


settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="独立医学影像检查项目标准匹配服务（三层架构：映射库→算法引擎→Agent审核）",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api", tags=["matching"])
# 旧服务 API 兼容层（Phase C1/C2）：平替生产 examine-standard(:50000)
app.include_router(legacy_router)
# 管理后台 API（Phase E）- admin_router 已包含 /api/admin prefix
app.include_router(admin_router)
# 评测系统 API（Phase F）- evaluation_router 已包含 /api/evaluation prefix
app.include_router(evaluation_router)

# 挂载前端静态文件（生产部署时使用）
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    logger.info(f"前端静态文件已挂载: {frontend_dist}")
else:
    logger.info("前端静态文件未找到，跳过挂载（开发模式）")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "match_service.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
