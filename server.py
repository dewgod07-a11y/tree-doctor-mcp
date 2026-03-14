"""
🌳 나무의사 MCP 서버 (Tree Doctor MCP Server)
카카오 PlayMCP 등록용 메인 서버 파일

실행 방법:
  pip install -r requirements.txt
  python server.py
"""

from mcp.server.fastmcp import FastMCP
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

# ── MCP 서버 인스턴스 생성 ─────────────────────────────────────
mcp = FastMCP(
    name="나무의사 MCP",
    instructions=(
        "수목 병해충 진단, 나무병원 찾기, 수목 처방 DB 조회, "
        "관리 일정 등록까지 — 나무를 지키는 AI 도구 모음입니다."
    ),
)

# ── 카테고리별 Tool 등록 ───────────────────────────────────────
# 🔬 병해충 진단 (4개)
mcp.tool()(diagnose_tree_disease)
mcp.tool()(diagnose_tree_disease_by_image)
mcp.tool()(get_pest_detail)
mcp.tool()(get_seasonal_pest_alert)

# 🏥 나무병원 찾기 (3개)
mcp.tool()(find_tree_hospital_nearby)
mcp.tool()(find_tree_doctor)
mcp.tool()(get_tree_hospital_detail)

# 💊 수목 처방 DB (3개)
mcp.tool()(get_treatment_prescription)
mcp.tool()(search_approved_pesticide)
mcp.tool()(get_tree_species_info)

# 📅 관리 일정·이력 (3개)
mcp.tool()(create_tree_care_schedule)
mcp.tool()(get_tree_care_history)
mcp.tool()(send_care_reminder_to_kakao)


# ── 실행 ──────────────────────────────────────────────────────
if __name__ == "__main__":
    # 로컬 테스트: stdio 모드
    # 클라우드 배포: transport="sse" 로 변경
    mcp.run(transport="stdio")
