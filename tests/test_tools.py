"""
tests/test_tools.py  -  Tool 동작 로컬 테스트 스크립트
실행: python tests/test_tools.py
"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.diagnosis  import diagnose_tree_disease, get_seasonal_pest_alert
from tools.hospital   import find_tree_hospital_nearby
from tools.prescription import get_tree_species_info
from tools.schedule   import create_tree_care_schedule, get_tree_care_history


async def test_all():
    print("=" * 60)
    print("🌳 나무의사 MCP Tool 테스트 시작")
    print("=" * 60)

    print("\n[Test 1] diagnose_tree_disease")
    result = await diagnose_tree_disease(
        tree_species="소나무",
        symptoms="잎 끝이 갈색으로 변하고 수지가 흘러내림",
        location="줄기", affected_area="일부 가지",
    )
    print(f"  → 진단 수: {len(result.get('diagnoses', []))}")
    if result.get("diagnoses"):
        print(f"  → 주요 진단: {result['diagnoses'][0].get('pest_name','N/A')}")
    print("  ✅ 통과")

    print("\n[Test 2] get_seasonal_pest_alert")
    result = await get_seasonal_pest_alert(month=5, region="서울")
    print(f"  → 경보 수준: {result.get('alert_level','N/A')}, 병해충 수: {len(result.get('pests',[]))}")
    print("  ✅ 통과")

    print("\n[Test 3] find_tree_hospital_nearby  (API 키 없으면 샘플 반환)")
    result = await find_tree_hospital_nearby(location="서울 여의도", radius_km=5.0)
    print(f"  → 결과 수: {result.get('total_count', 0)}")
    print("  ✅ 통과")

    print("\n[Test 4] get_tree_species_info")
    result = await get_tree_species_info(species_name="느티나무", include_pests=True)
    print(f"  → 수종: {result.get('korean_name','N/A')}, 병해충: {len(result.get('major_pests',[]))}")
    print("  ✅ 통과")

    print("\n[Test 5] create_tree_care_schedule")
    result = await create_tree_care_schedule(
        tree_id="여의도공원_은행나무_001", care_type="방제",
        scheduled_date="2026-04-15", notes="솔나방 방제", sync_calendar=False,
    )
    print(f"  → 등록: {result.get('success')}, ID: {result.get('record_id')}")
    print("  ✅ 통과")

    print("\n[Test 6] get_tree_care_history")
    result = await get_tree_care_history(tree_id="여의도공원_은행나무_001")
    print(f"  → 이력 수: {result.get('total_count', 0)}")
    print("  ✅ 통과")

    print("\n" + "=" * 60)
    print("🎉 모든 테스트 완료!")
    print("\n다음 단계:")
    print("  1. cp .env.example .env  →  API 키 입력")
    print("  2. pip install -r requirements.txt")
    print("  3. python main.py")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_all())
