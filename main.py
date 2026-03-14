"""
Tree Doctor MCP Server for Kakao PlayMCP
"""

import os
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from tools.diagnosis import (
    diagnose_tree_disease,
    diagnose_tree_disease_by_image,
    get_pest_detail,
    get_seasonal_pest_alert,
)
from tools.hospital import (
    find_tree_hospital_nearby,
    find_tree_doctor,
    get_tree_hospital_detail,
)
from tools.prescription import (
    get_treatment_prescription,
    search_approved_pesticide,
    get_tree_species_info,
)
from tools.schedule import (
    create_tree_care_schedule,
    get_tree_care_history,
    send_care_reminder_to_kakao,
)

# ── MCP 서버 인스턴스 ─────────────────────────────────────────────
mcp = FastMCP(
    name="tree-doctor-mcp",
    instructions=(
        "수목 병해충 진단, 나무병원 찾기, 수목 처방 조회, "
        "수목 관리 일정 기록 기능을 제공합니다."
    ),
    host="0.0.0.0",
    port=int(os.environ.get("PORT", 8000)),
    stateless_http=True,
)

# ── Health check (Railway / PlayMCP 연결 확인용) ──────────────────
@mcp.custom_route("/", methods=["GET"])
async def root(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "tree-doctor-mcp"})


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


# ── Tool 등록 ─────────────────────────────────────────────────────
mcp.tool()(diagnose_tree_disease)
mcp.tool()(diagnose_tree_disease_by_image)
mcp.tool()(get_pest_detail)
mcp.tool()(get_seasonal_pest_alert)

mcp.tool()(find_tree_hospital_nearby)
mcp.tool()(find_tree_doctor)
mcp.tool()(get_tree_hospital_detail)

mcp.tool()(get_treatment_prescription)
mcp.tool()(search_approved_pesticide)
mcp.tool()(get_tree_species_info)

mcp.tool()(create_tree_care_schedule)
mcp.tool()(get_tree_care_history)
mcp.tool()(send_care_reminder_to_kakao)

# ── ASGI app (uvicorn main:app 으로 실행) ─────────────────────────
app = mcp.streamable_http_app()

if __name__ == "__main__":
    mcp.run(transport="streamable-http")

