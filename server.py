"""
🌳 나무의사 MCP 서버 (Tree Doctor MCP Server)
카카오 PlayMCP 등록용 메인 서버 파일

실행 방법:
  pip install -r requirements.txt
  python server.py
"""

from mcp.server.fastmcp import FastMCP
from tools.diagnosis   import register_diagnosis_tools
from tools.hospital    import register_hospital_tools
from tools.prescription import register_prescription_tools
from tools.schedule    import register_schedule_tools

# ── MCP 서버 인스턴스 생성 ─────────────────────────────────────
mcp = FastMCP(
    name="나무의사 MCP",
    description=(
        "수목 병해충 진단, 나무병원 찾기, 수목 처방 DB 조회, "
        "관리 일정 등록까지 — 나무를 지키는 AI 도구 모음입니다."
    ),
)

# ── 카테고리별 Tool 등록 ───────────────────────────────────────
register_diagnosis_tools(mcp)      # 🔬 병해충 진단 (4개)
register_hospital_tools(mcp)       # 🏥 나무병원 찾기 (3개)
register_prescription_tools(mcp)   # 💊 수목 처방 DB (3개)
register_schedule_tools(mcp)       # 📅 관리 일정·이력 (3개)


# ── 실행 ──────────────────────────────────────────────────────
if __name__ == "__main__":
    # 로컬 테스트: stdio 모드
    # 클라우드 배포: transport="sse" 로 변경
    mcp.run(transport="stdio")
