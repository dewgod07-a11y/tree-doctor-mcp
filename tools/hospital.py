"""
tools/hospital.py
카테고리 2: 나무병원 찾기 Tool (1개)
  - find_tree_hospital_nearby
"""
from __future__ import annotations
import asyncio
import httpx
from config.settings import settings


def _kakao_headers() -> dict:
    return {"Authorization": f"KakaoAK {settings.KAKAO_REST_API_KEY}"}


async def _geocode_address(address: str):
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

    coords = await _geocode_address(location)

    hospitals: list = []
    if coords:
        lat, lon = coords
        radius_m = int(min(radius_km * 1000, 20000))
        async with httpx.AsyncClient() as client:
            results = await asyncio.gather(
                _kakao_keyword_search(client, "나무병원", lon, lat, radius_m),
                _kakao_keyword_search(client, "수목진료소", lon, lat, radius_m),
                _kakao_keyword_search(client, "나무의사", lon, lat, radius_m),
            )
        seen_ids: set = set()
        for docs in results:
            for d in docs:
                pid = d.get("id", "")
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)
                hospitals.append({
                    "name":          d.get("place_name", ""),
                    "address":       d.get("road_address_name", "") or d.get("address_name", ""),
                    "phone":         d.get("phone", ""),
                    "business_type": d.get("category_name", ""),
                    "distance_km":   round(float(d.get("distance", 0)) / 1000, 2),
                    "kakao_url":     d.get("place_url", ""),
                })

    if not hospitals:
        return {
            "search_location": location,
            "radius_km": radius_km,
            "total_count": 0,
            "hospitals": [],
            "message": f"{location} 반경 {radius_km}km 내 카카오맵에 등록된 나무병원이 없습니다.",
            "kakao_map_url": kakao_map_url,
            "tip": "아래 카카오맵 링크에서 직접 검색하거나, 산림청 나무병원 찾기(forest.go.kr)를 이용하세요.",
        }

    return {
        "search_location": location,
        "radius_km": radius_km,
        "total_count": len(hospitals),
        "hospitals": hospitals[:20],
        "kakao_map_url": kakao_map_url,
    }
