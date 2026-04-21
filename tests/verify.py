"""
tests/verify.py - PlayMCP 재심사 전 실제 동작 검증
실행: python tests/verify.py
"""
import asyncio, sys, os, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.diagnosis import diagnose_tree_disease, get_seasonal_pest_alert
from tools.hospital import find_tree_hospital_nearby
from tools.prescription import get_tree_species_info
from tools.schedule import create_tree_care_schedule, get_tree_care_history

PASS = 0
FAIL = 0


def check(label, condition, actual=None):
    global PASS, FAIL
    if condition:
        print(f"  ✅ {label}")
        PASS += 1
    else:
        print(f"  ❌ {label}")
        if actual is not None:
            print(f"     실제 값: {json.dumps(actual, ensure_ascii=False)[:200]}")
        FAIL += 1


async def test_diagnose_tree_disease():
    print("\n[1] diagnose_tree_disease - 소나무 증상 진단")
    r = await diagnose_tree_disease(
        tree_species="소나무",
        symptoms="잎 끝이 갈색으로 변하고 수지가 흘러내림",
    )
    check("오류 없음", "error" not in r, r)
    check("diagnoses 리스트 존재", isinstance(r.get("diagnoses"), list), r)
    check("진단 1개 이상", len(r.get("diagnoses", [])) >= 1, r)
    diags = r.get("diagnoses", [])
    check("pest_name 있음", bool(diags[0].get("pest_name")) if diags else False, r)
    check("general_advice 있음", bool(r.get("general_advice")), r)
    if "diagnoses" in r and r["diagnoses"]:
        print(f"     → 주요 진단: {r['diagnoses'][0].get('pest_name')}")
    return "error" not in r


async def test_get_seasonal_pest_alert():
    print("\n[2] get_seasonal_pest_alert - 4월 서울 병해충 경보")
    r = await get_seasonal_pest_alert(month=4, region="서울")
    check("오류 없음", "error" not in r, r)
    check("month 반환", r.get("month") == 4, r)
    check("alert_level 있음", bool(r.get("alert_level")), r)
    check("pests 리스트 존재", isinstance(r.get("pests"), list), r)
    check("pests 1개 이상", len(r.get("pests", [])) >= 1, r)
    if r.get("pests"):
        print(f"     → 경보 병해충: {r['pests'][0].get('pest_name')}")
    return "error" not in r


async def test_find_tree_hospital():
    print("\n[3] find_tree_hospital_nearby - 서울 강남구 반경 20km")
    r = await find_tree_hospital_nearby(location="서울 강남구", radius_km=20.0)
    check("오류 없음", "error" not in r, r)
    check("search_location 있음", bool(r.get("search_location")), r)
    check("kakao_map_url 있음", bool(r.get("kakao_map_url")), r)
    count = r.get("total_count", 0)
    if count > 0:
        check(f"나무병원 {count}개 발견", True)
        print(f"     → 첫 번째: {r['hospitals'][0].get('name')} ({r['hospitals'][0].get('address')})")
    else:
        print("     ⚠️  결과 없음 (카카오 API 키 로컬 미설정이면 정상 - Railway에선 동작)")
    return True


async def test_get_tree_species_info():
    print("\n[4] get_tree_species_info - 느티나무 정보")
    r = await get_tree_species_info(species_name="느티나무", include_pests=True)
    check("오류 없음", "error" not in r, r)
    check("korean_name 있음", bool(r.get("korean_name")), r)
    check("characteristics 있음", bool(r.get("characteristics")), r)
    check("seasonal_care 있음", isinstance(r.get("seasonal_care"), dict), r)
    check("major_pests 리스트", isinstance(r.get("major_pests"), list), r)
    if r.get("major_pests"):
        print(f"     → 주요 병해충: {r['major_pests'][0].get('pest_name')}")
    return "error" not in r


async def test_schedule():
    print("\n[5] create_tree_care_schedule + get_tree_care_history")
    r = await create_tree_care_schedule(
        tree_id="강남구_느티나무_001",
        care_type="방제",
        scheduled_date="2026-05-10",
        notes="솔나방 방제",
        sync_calendar=False,
    )
    check("등록 성공", r.get("success") is True, r)
    check("record_id 있음", bool(r.get("record_id")), r)
    rid = r.get("record_id")
    print(f"     → record_id: {rid}")

    r2 = await get_tree_care_history(tree_id="강남구_느티나무_001")
    check("이력 조회 성공", r2.get("total_count", 0) >= 1, r2)
    print(f"     → 이력 수: {r2.get('total_count')}")
    return r.get("success") is True


async def main():
    print("=" * 60)
    print(" PlayMCP 재심사 전 검증 테스트")
    print("=" * 60)

    results = []
    results.append(await test_diagnose_tree_disease())
    results.append(await test_get_seasonal_pest_alert())
    results.append(await test_find_tree_hospital())
    results.append(await test_get_tree_species_info())
    results.append(await test_schedule())

    print("\n" + "=" * 60)
    print(f" 결과: ✅ {PASS}개 통과  ❌ {FAIL}개 실패")
    if FAIL == 0:
        print(" 모든 검증 통과! PlayMCP 재심사 신청 가능합니다.")
    else:
        print(" 실패 항목을 수정 후 재시도하세요.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
