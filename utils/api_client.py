"""
utils/api_client.py
공공데이터 API 호출 공통 클라이언트
"""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

PUBLIC_DATA_API_KEY = os.getenv("PUBLIC_DATA_API_KEY", "")
BASE_URL = "http://apis.data.go.kr"


async def fetch_public_data(endpoint: str, params: dict) -> dict:
    """
    공공데이터포털 API 공통 호출 함수

    사용 예:
        result = await fetch_public_data(
            "/B552584/treeDoctorService/getHospitalList",
            {"sido": "서울", "numOfRows": 10}
        )
    """
    params["serviceKey"] = PUBLIC_DATA_API_KEY
    params.setdefault("_type", "json")
    params.setdefault("numOfRows", 20)
    params.setdefault("pageNo", 1)

    url = BASE_URL + endpoint

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    # 공공데이터 표준 응답 구조에서 실제 데이터 추출
    # 구조: { response: { body: { items: { item: [...] } } } }
    try:
        body = data["response"]["body"]
        items = body.get("items", {})
        if not items:
            return {"items": [], "totalCount": 0}

        item_list = items.get("item", [])
        # 결과가 1개일 때 dict로 오는 경우 처리
        if isinstance(item_list, dict):
            item_list = [item_list]

        return {
            "items": item_list,
            "totalCount": body.get("totalCount", len(item_list)),
        }
    except (KeyError, TypeError):
        return {"items": [], "totalCount": 0, "raw": data}
