"""
tools/hospital.py
카테고리 2: 나무병원·나무의사 찾기 Tools (3개)
  - find_tree_hospital_nearby
  - find_tree_doctor
  - get_tree_hospital_detail
"""
from __future__ import annotations
import math
import httpx
from config.settings import settings


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def _geocode_address(address: str):
    """카카오맵 API로 주소 → 좌표 변환"""
    url = f"{settings.KAKAO_MAP_API_BASE}/search/address.json"
    headers = {"Authorization": f"KakaoAK {settings.KAKAO_MAP_API_KEY}"}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers, params={"query": address}, timeout=10.0)
            docs = resp.json().get("documents", [])
            if docs:
                return float(docs[0]["y"]), float(docs[0]["x"])
        except Exception:
            pass
    return None


async def find_tree_hospital_nearby(
    location: str,
    radius_km: float = 10.0,
    business_type: str = "",
    open_only: bool = True,
) -> dict:
    """
    현재 위치(또는 입력 주소) 기준 반경 내 등록된 나무병원을 검색합니다.

    Args:
        location:      기준 위치 주소 (예: 서울 강남구)
        radius_km:     검색 반경 km (기본값: 10)
        business_type: 사업 종류 필터 (방제업/컨설팅/외과수술, 미입력 시 전체)
        open_only:     영업 중인 병원만 표시 (기본: True)
    """
    coords = await _geocode_address(location)
    if not coords:
        return {"error": f"'{location}' 주소를 찾을 수 없습니다."}
    user_lat, user_lon = coords

    # 산림청 나무병원 등록현황 API 호출
    url = "https://apis.data.go.kr/1400000/forestService/getTreeHospitalList"
    params = {
        "serviceKey": settings.DATA_GO_KR_API_KEY,
        "numOfRows": 100,
        "pageNo": 1,
        "_type": "json",
    }
    if business_type:
        params["bizType"] = business_type

    hospitals = []
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10.0)
            if resp.status_code == 200:
                raw_list = (
                    resp.json().get("response", {})
                               .get("body", {})
                               .get("items", {})
                               .get("item", [])
                )
                for h in raw_list:
                    if open_only and h.get("closeYn") == "Y":
                        continue
                    h_lat = float(h.get("lat") or 0)
                    h_lon = float(h.get("lon") or 0)
                    if h_lat and h_lon:
                        dist = _haversine_km(user_lat, user_lon, h_lat, h_lon)
                        if dist <= radius_km:
                            hospitals.append({
                                "hospital_id":   h.get("hospId", ""),
                                "name":          h.get("hospNm", ""),
                                "address":       h.get("addr", ""),
                                "phone":         h.get("telNo", ""),
                                "business_type": h.get("bizType", ""),
                                "distance_km":   round(dist, 2),
                                "status":        "영업중",
                            })
        except Exception:
            hospitals = [{
                "hospital_id": "SAMPLE",
                "name": "⚠️ 샘플 - data.go.kr에서 API 키 발급 필요",
                "address": "산림청 나무병원 API 신청: data.go.kr/data/15091330",
                "phone": "042-481-4151 (산림청)",
                "distance_km": 0.0,
                "status": "영업중",
            }]

    hospitals.sort(key=lambda x: x["distance_km"])
    return {
        "search_location": location,
        "radius_km": radius_km,
        "total_count": len(hospitals),
        "hospitals": hospitals[:20],
        "kakao_map_url": f"https://map.kakao.com/?q=나무병원&where={location}",
    }


async def find_tree_doctor(
    name: str = "",
    region: str = "",
    affiliation: str = "",
) -> dict:
    """
    나무의사 자격증 보유자를 이름 또는 지역으로 조회합니다.

    Args:
        name:        나무의사 이름 (부분 검색)
        region:      지역 (예: 경기도, 부산)
        affiliation: 소속 나무병원명
    """
    if not name and not region and not affiliation:
        return {"error": "이름, 지역, 소속 중 하나 이상 입력해주세요."}

    url = "https://apis.data.go.kr/1400000/forestService/getTreeDoctorList"
    params = {"serviceKey": settings.DATA_GO_KR_API_KEY, "numOfRows": 50, "pageNo": 1, "_type": "json"}
    if name:   params["drNm"]   = name
    if region: params["siDoNm"] = region

    doctors = []
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10.0)
            if resp.status_code == 200:
                raw = resp.json().get("response", {}).get("body", {}).get("items", {}).get("item", [])
                for d in raw:
                    if affiliation and affiliation not in d.get("hospNm", ""):
                        continue
                    doctors.append({
                        "name":        d.get("drNm", ""),
                        "license_no":  d.get("licenseNo", ""),
                        "affiliation": d.get("hospNm", ""),
                        "region":      d.get("siDoNm", ""),
                        "phone":       d.get("telNo", ""),
                    })
        except Exception:
            doctors = [{"message": "⚠️ API 키 설정 후 실제 데이터 조회 가능"}]

    return {"query": {"name": name, "region": region}, "total_count": len(doctors), "doctors": doctors}


async def get_tree_hospital_detail(hospital_id: str) -> dict:
    """
    나무병원 ID로 상세 정보를 조회합니다.

    Args:
        hospital_id: 나무병원 고유 ID (find_tree_hospital_nearby 결과값)
    """
    url = "https://apis.data.go.kr/1400000/forestService/getTreeHospitalDetail"
    params = {"serviceKey": settings.DATA_GO_KR_API_KEY, "hospId": hospital_id, "_type": "json"}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10.0)
            if resp.status_code == 200:
                item = resp.json().get("response", {}).get("body", {}).get("items", {}).get("item", {})
                if item:
                    return {
                        "hospital_id":    hospital_id,
                        "name":           item.get("hospNm", ""),
                        "address":        item.get("addr", ""),
                        "phone":          item.get("telNo", ""),
                        "ceo_name":       item.get("ceoNm", ""),
                        "business_types": item.get("bizTypes", []),
                        "registered_date":item.get("regDt", ""),
                        "status":         "영업중" if item.get("closeYn") != "Y" else "폐업",
                    }
        except Exception:
            pass

    return {"hospital_id": hospital_id, "message": "⚠️ 정보를 찾을 수 없습니다. API 키를 확인하세요."}
