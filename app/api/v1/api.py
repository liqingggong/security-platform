from fastapi import APIRouter

from app.api.v1.endpoints import (
    assets,
    auth,
    credentials,
    domains,
    fingerprints,
    scan_plans,
    tasks,
    tools,
    vulnerabilities,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["認證"])
api_router.include_router(credentials.router, prefix="/credentials", tags=["API憑證"])
api_router.include_router(scan_plans.router, prefix="/scan-plans", tags=["掃描方案"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["任務管理"])
api_router.include_router(assets.router, prefix="/assets", tags=["資產管理"])
api_router.include_router(domains.router, prefix="/domains", tags=["域名資產"])
api_router.include_router(vulnerabilities.router, prefix="/vulnerabilities", tags=["漏洞管理"])
api_router.include_router(fingerprints.router, prefix="/fingerprints", tags=["指紋管理"])
api_router.include_router(tools.router, prefix="/tools", tags=["工具管理"])
