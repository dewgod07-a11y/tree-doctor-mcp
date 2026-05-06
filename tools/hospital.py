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


def _to_list(val) -> list:
    if isinstance(val, list):
        return val
    if isinstance(val, dict):
        return [val]
    return []


def _haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _kakao_headers() -> dict:
    return {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}


async def _geocode_address(address: str):
    """카카오맵 REST API로 주소 → 좌표 변환"""
    url = f"{settings.KAKAO_MAP_API_BASE}/search/address.json"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                url, headers=_kakao_headers(),
                params={"query": address}, timeout=10.0,
            )
            docs = resp.json().get("documents", [])
            if docs:
                return float(docs[0]["y"]), float(docs[0]["x"])
            # address 검색 실패 시 키워드 검색으로 재시도
            resp2 = await client.get(
                f"{settings.KAKAO_MAP_API_BASE}/search/keyword.json",
                headers=_kakao_headers(),
                params={"query": address, "size": 1}, timeout=10.0,
            )
            docs2 = resp2.json().get("documents", [])
            if docs2:
                return float(docs2[0]["y"]), float(docs2[0]["x"])
        except Exception:
            pass
    return None


async def _search_hospitals_kakao(lat: float, lon: float, radius_km: float) -> list:
    """카카오맵 키워드 검색으로 나무병원 찾기"""
    url = f"{settings.KAKAO_MAP_API_BASE}/search/keyword.json"
    radius_m = int(min(radius_km * 1000, 20000))
    hospitals = []
    seen_ids = set()
    async with httpx.AsyncClient() as client:
        for query in ["나무병원", "수목진료소", "나무의사"]:
            try:
                resp = await client.get(
                    url, headers=_kakao_headers(),
                    params={"query": query, "x": str(lon), "y": str(lat), "radius": radius_m, "size": 15},
                    timeout=10.0,
                )
                if resp.status_code == 200:
                    for d in resp.json().get("documents", []):
                        pid = d.get("id", "")
                        if pid in seen_ids:
                            continue
                        seen_ids.add(pid)
                        dist_m = float(d.get("distance", 0))
                        hospitals.append({
                            "hospital_id":   pid,
                            "name":          d.get("place_name", ""),
                            "address":       d.get("road_address_name", "") or d.get("address_name", ""),
                            "phone":         d.get("phone", ""),
                            "business_type": d.get("category_name", ""),
                            "distance_km":   round(dist_m / 1000, 2),
                            "status":        "영업중",
                            "kakao_url":     d.get("place_url", ""),
                        })
            except Exception:
                continue
    return hospitals


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
    kakao_map_url = f"https://map.kakao.com/?q=나무병원&where={location}"
    hospitals = []
    sido = location[:2] if location else ""

    coords = await _geocode_address(location)
    if coords:
        user_lat, user_lon = coords
        hospitals = await _search_hospitals_kakao(user_lat, user_lon, radius_km)

    # 카카오 결과 부족 or 지오코딩 실패 시 산림청 공공 API로 보완
    if len(hospitals) < 3:
        import xml.etree.ElementTree as ET
        pub_url = f"{settings.TREE_HOSPITAL_API_BASE}/treeHospitalInfoList"
        api_key = settings.TREE_HOSPITAL_API_KEY or settings.DATA_GO_KR_API_KEY
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(pub_url, params={
                    "serviceKey": api_key,
                    "numOfRows": 2000, "pageNo": 1,
                }, timeout=15.0)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    for item in root.findall(".//item"):
                        def t(tag): return (item.findtext(tag) or "").strip()
                        if open_only and t("clsbiz") == "폐업":
                            continue
                        if business_type and business_type not in t("bsnsskindnm"):
                            continue
                        addr = t("lctnaddr")
                        ctpv = t("ctpvnm")
                        if sido and sido not in addr and sido not in ctpv:
                            continue
                        hospitals.append({
                            "hospital_id":    t("corpnm"),
                            "name":           t("corpnm"),
                            "address":        addr,
                            "phone":          "",
                            "business_type":  t("bsnsskindnm"),
                            "distance_km":    0,
                            "status":         t("clsbiz") or "영업중",
                        })
            except Exception:
                pass

    hospitals.sort(key=lambda x: x["distance_km"])

    if not hospitals:
        return {
            "search_location": location,
            "radius_km": radius_km,
            "total_count": 0,
            "hospitals": [],
            "message": f"{location} 반경 {radius_km}km 내 나무병원을 찾지 못했습니다. 반경을 늘리거나 다른 지역을 검색해보세요.",
            "kakao_map_url": kakao_map_url,
            "tip": "카카오맵에서 '나무병원'으로 직접 검색하거나 산림청(forest.go.kr)에 문의하세요.",
        }

    return {
        "search_location": location,
        "radius_km": radius_km,
        "total_count": len(hospitals),
        "hospitals": hospitals[:20],
        "kakao_map_url": kakao_map_url,
    }



async def get_tree_hospital_detail(hospital_id: str) -> dict:
    """
    나무병원 이름으로 상세 정보를 조회합니다.

    Args:
        hospital_id: 나무병원 이름 또는 ID (find_tree_hospital_nearby 결과값)
    """
    import xml.etree.ElementTree as ET
    api_key = settings.TREE_HOSPITAL_API_KEY or settings.DATA_GO_KR_API_KEY
    pub_url = f"{settings.TREE_HOSPITAL_API_BASE}/treeHospitalInfoList"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(pub_url, params={
                "serviceKey": api_key,
                "numOfRows": 2000, "pageNo": 1,
            }, timeout=15.0)
            if resp.status_code == 200:
                root = ET.fromstring(resp.text)
                for item in root.findall(".//item"):
                    def t(tag): return (item.findtext(tag) or "").strip()
                    hosp = t("corpnm")
                    if hospital_id in hosp or hosp in hospital_id:
                        return {
                            "hospital_id":   hosp,
                            "name":          hosp,
                            "address":       t("lctnaddr"),
                            "business_type": t("bsnsskindnm"),
                            "region":        t("ctpvnm"),
                            "district":      t("sggnm"),
                            "status":        t("clsbiz") or "영업중",
                            "zip":           t("zip"),
                        }
        except Exception:
            pass

    return {
        "hospital_id": hospital_id,
        "message":     f"'{hospital_id}' 나무병원 정보를 찾을 수 없습니다.",
        "tip":         "find_tree_hospital_nearby로 병원 목록을 먼저 조회하세요.",
    }
