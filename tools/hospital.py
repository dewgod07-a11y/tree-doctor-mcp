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

    coords = await _geocode_address(location)
    if coords:
        user_lat, user_lon = coords
        hospitals = await _search_hospitals_kakao(user_lat, user_lon, radius_km)

        # 카카오맵 결과가 부족하면 산림청 공공 API 보완
        if len(hospitals) < 3:
            pub_url = f"{settings.TREE_HOSPITAL_API_BASE}/getTreeHospitalInfoList"
            api_key = settings.TREE_HOSPITAL_API_KEY or settings.DATA_GO_KR_API_KEY
            # 시도명 추출 (주소 앞 2글자: 서울, 경기 등)
            sido = location[:2] if location else ""
            params = {
                "serviceKey": api_key,
                "numOfRows": 100, "pageNo": 1,
            }
            if sido:
                params["sidoName"] = sido
            async with httpx.AsyncClient() as client:
                try:
                    resp = await client.get(pub_url, params=params, timeout=10.0)
                    if resp.status_code == 200:
                        import xml.etree.ElementTree as ET
                        root = ET.fromstring(resp.text)
                        for item in root.findall(".//item"):
                            def t(tag): return (item.findtext(tag) or "").strip()
                            if open_only and t("hogyStus") == "폐업":
                                continue
                            if business_type and business_type not in t("hogyBizType"):
                                continue
                            hospitals.append({
                                "hospital_id":   t("hogyNo"),
                                "name":          t("hogyName"),
                                "address":       t("hogyAddr"),
                                "phone":         t("hogyTelno"),
                                "business_type": t("hogyBizType"),
                                "distance_km":   0,
                                "status":        t("hogyStus") or "영업중",
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


async def find_tree_doctor(
    name: str = "",
    region: str = "",
    affiliation: str = "",
) -> dict:
    """
    나무의사 자격증 보유자를 이름 또는 지역으로 조회합니다.

    Args:
        name:        나무의사 이름 (부분 검색, 미입력 가능)
        region:      지역 (예: 경기도, 부산, 미입력 시 전국)
        affiliation: 소속 나무병원명
    """
    doctors = []

    # 공공 데이터 API 조회
    url = "https://apis.data.go.kr/1400000/forestService/getTreeDoctorList"
    params = {"serviceKey": settings.DATA_GO_KR_API_KEY, "numOfRows": 50, "pageNo": 1, "_type": "json"}
    if name:   params["drNm"]   = name
    if region: params["siDoNm"] = region

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10.0)
            if resp.status_code == 200:
                raw = _to_list(
                    resp.json().get("response", {})
                               .get("body", {})
                               .get("items", {})
                               .get("item", [])
                )
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
            pass

    # 공공 API 결과 없으면 카카오맵 키워드 검색으로 보완
    if not doctors:
        search_query = f"나무의사 {region}" if region else "나무병원 나무의사"
        kw_url = f"{settings.KAKAO_MAP_API_BASE}/search/keyword.json"
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    kw_url, headers=_kakao_headers(),
                    params={"query": search_query, "size": 15}, timeout=10.0,
                )
                if resp.status_code == 200:
                    for d in resp.json().get("documents", []):
                        doctors.append({
                            "name":        d.get("place_name", ""),
                            "license_no":  "",
                            "affiliation": d.get("place_name", ""),
                            "region":      d.get("address_name", ""),
                            "phone":       d.get("phone", ""),
                            "kakao_url":   d.get("place_url", ""),
                            "source":      "카카오맵",
                        })
            except Exception:
                pass

    region_str = region or "전국"
    return {
        "query": {"name": name, "region": region, "affiliation": affiliation},
        "total_count": len(doctors),
        "doctors": doctors,
        "tip": f"산림청 나무의사 공식 조회: https://www.forest.go.kr ('{region_str}' 기준)",
    }


async def get_tree_hospital_detail(hospital_id: str) -> dict:
    """
    나무병원 ID로 상세 정보를 조회합니다.

    Args:
        hospital_id: 나무병원 고유 ID (find_tree_hospital_nearby 결과값)
    """
    # 공공 데이터 API 조회 (산림청 등록 병원 ID인 경우)
    url = "https://apis.data.go.kr/1400000/forestService/getTreeHospitalDetail"
    params = {"serviceKey": settings.DATA_GO_KR_API_KEY, "hospId": hospital_id, "_type": "json"}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10.0)
            if resp.status_code == 200:
                item = (
                    resp.json().get("response", {})
                               .get("body", {})
                               .get("items", {})
                               .get("item", {})
                )
                if item:
                    return {
                        "hospital_id":     hospital_id,
                        "name":            item.get("hospNm", ""),
                        "address":         item.get("addr", ""),
                        "phone":           item.get("telNo", ""),
                        "ceo_name":        item.get("ceoNm", ""),
                        "business_types":  item.get("bizTypes", []),
                        "registered_date": item.get("regDt", ""),
                        "status":          "영업중" if item.get("closeYn") != "Y" else "폐업",
                    }
        except Exception:
            pass

    # 카카오맵 place ID인 경우 (숫자로만 구성) → 카카오맵 링크 반환
    if hospital_id.isdigit():
        kakao_place_url = f"https://place.map.kakao.com/{hospital_id}"
        # 카카오맵 키워드 검색으로 장소 정보 재조회 시도
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(
                    f"{settings.KAKAO_MAP_API_BASE}/search/keyword.json",
                    headers=_kakao_headers(),
                    params={"query": "나무병원", "size": 15}, timeout=10.0,
                )
                if resp.status_code == 200:
                    for d in resp.json().get("documents", []):
                        if d.get("id") == hospital_id:
                            return {
                                "hospital_id":   hospital_id,
                                "name":          d.get("place_name", ""),
                                "address":       d.get("road_address_name", "") or d.get("address_name", ""),
                                "phone":         d.get("phone", ""),
                                "business_type": d.get("category_name", ""),
                                "status":        "영업중",
                                "kakao_url":     d.get("place_url", kakao_place_url),
                            }
            except Exception:
                pass
        return {
            "hospital_id":  hospital_id,
            "kakao_url":    kakao_place_url,
            "message":      "카카오맵에서 상세 정보를 확인하세요.",
            "status":       "조회 완료",
        }

    return {
        "hospital_id": hospital_id,
        "message":     "해당 ID의 나무병원 정보를 찾을 수 없습니다.",
        "tip":         "find_tree_hospital_nearby로 병원을 먼저 검색하세요.",
    }
