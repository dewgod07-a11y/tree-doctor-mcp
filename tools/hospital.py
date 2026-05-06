"""
tools/hospital.py
카테고리 2: 나무병원 찾기 Tool (1개)
  - find_tree_hospital_nearby
"""
from __future__ import annotations
import asyncio
import xml.etree.ElementTree as ET
import httpx
from config.settings import settings

_SIDO_MAP = {
    "서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시",
    "인천": "인천광역시", "광주": "광주광역시", "대전": "대전광역시",
    "울산": "울산광역시", "세종": "세종특별자치시", "경기": "경기도",
    "강원": "강원특별자치도", "충북": "충청북도", "충남": "충청남도",
    "전북": "전북특별자치도", "전남": "전라남도", "경북": "경상북도",
    "경남": "경상남도", "제주": "제주특별자치도",
}


def _kakao_headers() -> dict:
    return {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}


async def _geocode_address(address: str):
    """카카오맵 REST API로 주소 → 좌표 변환"""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{settings.KAKAO_MAP_API_BASE}/search/address.json",
                headers=_kakao_headers(),
                params={"query": address}, timeout=5.0,
            )
            docs = resp.json().get("documents", [])
            if docs:
                return float(docs[0]["y"]), float(docs[0]["x"])
            resp2 = await client.get(
                f"{settings.KAKAO_MAP_API_BASE}/search/keyword.json",
                headers=_kakao_headers(),
                params={"query": address, "size": 1}, timeout=5.0,
            )
            docs2 = resp2.json().get("documents", [])
            if docs2:
                return float(docs2[0]["y"]), float(docs2[0]["x"])
        except Exception:
            pass
    return None


async def _kakao_keyword_search(client, query: str, lon: float, lat: float, radius_m: int) -> list:
    try:
        resp = await client.get(
            f"{settings.KAKAO_MAP_API_BASE}/search/keyword.json",
            headers=_kakao_headers(),
            params={"query": query, "x": str(lon), "y": str(lat), "radius": radius_m, "size": 15},
            timeout=5.0,
        )
        if resp.status_code == 200:
            return resp.json().get("documents", [])
    except Exception:
        pass
    return []


async def _search_hospitals_kakao(lat: float, lon: float, radius_km: float) -> list:
    """카카오맵 키워드 검색 3개 동시 실행"""
    radius_m = int(min(radius_km * 1000, 20000))
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(
            _kakao_keyword_search(client, "나무병원", lon, lat, radius_m),
            _kakao_keyword_search(client, "수목진료소", lon, lat, radius_m),
            _kakao_keyword_search(client, "나무의사", lon, lat, radius_m),
        )
    hospitals = []
    seen_ids: set = set()
    for docs in results:
        for d in docs:
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
    return hospitals


async def _search_hospitals_public(sido: str, business_type: str, open_only: bool) -> tuple:
    """산림청 공공 API로 나무병원 검색. (hospitals, debug_info) 반환"""
    pub_url = f"{settings.TREE_HOSPITAL_API_BASE}/treeHospitalInfoList"
    api_key = settings.TREE_HOSPITAL_API_KEY or settings.DATA_GO_KR_API_KEY
    ctpvnm_full = _SIDO_MAP.get(sido, "")

    params: dict = {"serviceKey": api_key, "numOfRows": 2000, "pageNo": 1}
    if ctpvnm_full:
        params["ctpvnm"] = ctpvnm_full

    hospitals = []
    debug: dict = {"status": "not_called", "total_items": 0, "filtered": 0, "sido": sido, "ctpvnm": ctpvnm_full}

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(pub_url, params=params, timeout=12.0)
            debug["status"] = resp.status_code
            if resp.status_code == 200:
                root = ET.fromstring(resp.text)
                all_items = root.findall(".//item")
                debug["total_items"] = len(all_items)
                for item in all_items:
                    def t(tag, _item=item): return (_item.findtext(tag) or "").strip()
                    if open_only and t("clsbiz") == "폐업":
                        continue
                    if business_type and business_type not in t("bsnsskindnm"):
                        continue
                    addr = t("lctnaddr")
                    ctpv = t("ctpvnm")
                    if sido and sido not in addr and sido not in ctpv:
                        continue
                    hospitals.append({
                        "hospital_id":   t("corpnm"),
                        "name":          t("corpnm"),
                        "address":       addr,
                        "phone":         "",
                        "business_type": t("bsnsskindnm"),
                        "distance_km":   0,
                        "status":        t("clsbiz") or "영업중",
                    })
                debug["filtered"] = len(hospitals)
        except Exception as e:
            debug["status"] = f"error: {str(e)[:80]}"
    return hospitals, debug


async def find_tree_hospital_nearby(
    location: str,
    radius_km: float = 10.0,
    business_type: str = "",
    open_only: bool = True,
) -> dict:
    """
    현재 위치(또는 입력 주소) 기준 반경 내 등록된 나무병원을 검색합니다.

    Args:
        location:      기준 위치 주소 (예: 서울 강남구, 대구, 부산 해운대구)
        radius_km:     검색 반경 km (기본값: 10)
        business_type: 사업 종류 필터 (방제업/컨설팅/외과수술, 미입력 시 전체)
        open_only:     영업 중인 병원만 표시 (기본: True)
    """
    kakao_map_url = f"https://map.kakao.com/?q=나무병원&where={location}"
    sido = location[:2] if location else ""

    # 지오코딩 + 공공 API 병렬 실행
    coords, (pub_hospitals, pub_debug) = await asyncio.gather(
        _geocode_address(location),
        _search_hospitals_public(sido, business_type, open_only),
    )

    # 카카오 병원 검색 (좌표 획득 후)
    kakao_hospitals: list = []
    if coords:
        kakao_hospitals = await _search_hospitals_kakao(coords[0], coords[1], radius_km)

    # 중복 제거하며 병합 (카카오 우선)
    seen_names: set = set()
    hospitals: list = []
    for h in kakao_hospitals:
        name = h.get("name", "")
        if name and name not in seen_names:
            seen_names.add(name)
            hospitals.append(h)
    for h in pub_hospitals:
        name = h.get("name", "")
        if name and name not in seen_names:
            seen_names.add(name)
            hospitals.append(h)

    hospitals.sort(key=lambda x: x["distance_km"])

    _debug = {
        "kakao_found": len(kakao_hospitals),
        "pub_api": pub_debug,
        "geocode_ok": coords is not None,
    }

    if not hospitals:
        return {
            "search_location": location,
            "radius_km": radius_km,
            "total_count": 0,
            "hospitals": [],
            "message": f"{location} 반경 {radius_km}km 내 나무병원을 찾지 못했습니다.",
            "kakao_map_url": kakao_map_url,
            "tip": "카카오맵에서 '나무병원'으로 직접 검색하거나 산림청(forest.go.kr)에 문의하세요.",
            "_debug": _debug,
        }

    return {
        "search_location": location,
        "radius_km": radius_km,
        "total_count": len(hospitals),
        "hospitals": hospitals[:20],
        "kakao_map_url": kakao_map_url,
    }
