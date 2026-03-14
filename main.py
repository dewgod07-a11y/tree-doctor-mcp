"""
🌳 나무의사 MCP 서버 - 메인 진입점
Tree Doctor MCP Server for Kakao PlayMCP

실행 방법:
  pip install -r requirements.txt
  python main.py
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

# ── MCP 서버 인스턴스 생성 ───────────────────────────────────────────────────
mcp = FastMCP(
    name="나무의사 MCP",
    instructions="""
    이 MCP는 수목 병해충 진단, 나무병원 찾기, 수목 처방 조회,
    수목 관리 일정 기록 기능을 제공합니다.
    나무 관련 질문이 들어오면 적절한 Tool을 선택해 실행하세요.
    """,
)

# ── Tool 등록 ────────────────────────────────────────────────────────────────
# 카테고리 1: 병해충 진단
mcp.tool()(diagnose_tree_disease)
mcp.tool()(diagnose_tree_disease_by_image)
mcp.tool()(get_pest_detail)
mcp.tool()(get_seasonal_pest_alert)

# 카테고리 2: 나무병원 찾기
mcp.tool()(find_tree_hospital_nearby)
mcp.tool()(find_tree_doctor)
mcp.tool()(get_tree_hospital_detail)

# 카테고리 3: 수목 처방 DB
mcp.tool()(get_treatment_prescription)
mcp.tool()(search_approved_pesticide)
mcp.tool()(get_tree_species_info)

# 카테고리 4: 관리 일정·이력
mcp.tool()(create_tree_care_schedule)
mcp.tool()(get_tree_care_history)
mcp.tool()(send_care_reminder_to_kakao)


if __name__ == "__main__":
    # 로컬 테스트: stdio 모드
    # 클라우드 배포: streamable-http 모드 (아래 주석 해제)
    # mcp.run(transport="stdio")

    # 클라우드 배포 시 아래로 교체:
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
