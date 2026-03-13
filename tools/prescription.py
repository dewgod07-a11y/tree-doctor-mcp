"""
tools/prescription.py
카테고리 3: 수목 처방 데이터베이스 Tools (3개)
  - get_treatment_prescription  : 수목 처방 조회
  - search_approved_pesticide   : 승인 농약 검색
  - get_tree_species_info       : 수종 정보 조회
"""
from __future__ import annotations
import json
import httpx
from anthropic import Anthropic
from config.settings import settings

anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)


async def get_treatment_prescription(
    pest_name: str,
    tree_species: str,
    severity: str = "보통",
    organic_only: bool = False,
) -> dict:
    """
    진단된 병해충에 대한 공식 처방 방법을 조회합니다.

    Args:
        pest_name:    병해충 이름
        tree_species: 수종명
        severity:     피해 정도 (경미/보통/심각)
        organic_only: 친환경 처방만 조회 (기본: False)
    """
    organic_note = "친환경·유기농 처방만 포함하세요." if organic_only else ""
    prompt = f"""
당신은 산림청 공인 수목 처방 전문가입니다.
아래 수목 병해충에 대한 처방을 JSON 형식으로 제공하세요.
{organic_note}
(다른 설명 없이 JSON만 반환)

수종: {tree_species}
병해충: {pest_name}
피해 정도: {severity}

{{
  "pest_name": "{pest_name}",
  "tree_species": "{tree_species}",
  "severity": "{severity}",
  "treatments": [
    {{
      "method": "처치 방법명 (예: 약제 살포/외과수술/토양주사)",
      "timing": "처치 적기 (예: 4~5월 유충 부화 직후)",
      "procedure": "세부 처치 절차",
      "frequency": "처치 횟수 및 간격",
      "precautions": ["주의사항1", "주의사항2"],
      "is_organic": true 또는 false
    }}
  ],
  "recommended_pesticides": [
    {{
      "product_name": "약제명",
      "active_ingredient": "유효성분",
      "dilution_ratio": "희석 배수",
      "application_method": "처리 방법",
      "re_entry_days": 안전 재입 일수
    }}
  ],
  "follow_up": "처치 후 모니터링 방법",
  "need_professional": true 또는 false,
  "legal_note": "산림보호법 관련 주의사항 (해당시)"
}}
"""
    response = anthropic_client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    import re
    raw = response.content[0].text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                result = json.loads(m.group())
            except json.JSONDecodeError:
                result = {"error": "AI 응답 파싱 실패"}
        else:
            result = {"error": "AI 응답 파싱 실패"}
    result["data_source"] = "Claude AI (산림청 임업기술 기준)"
    result["disclaimer"] = "이 처방은 참고용입니다. 실제 처방은 자격을 가진 나무의사에게 받으세요."
    return result


async def search_approved_pesticide(
    target_pest: str,
    tree_species: str = "",
    ingredient: str = "",
) -> dict:
    """
    수목 병해충 방제용으로 승인된 농약을 검색합니다.

    Args:
        target_pest:  방제 대상 병해충명
        tree_species: 적용 수종 (미입력 시 전체)
        ingredient:   성분명 검색 (예: 이미다클로프리드)
    """
    # 농촌진흥청 농약 등록 현황 API 호출
    url = "https://apis.data.go.kr/1390000/PesticideInfoService/getPesticideInfo"
    params = {
        "serviceKey":  settings.DATA_GO_KR_API_KEY,
        "pestNm":      target_pest,
        "numOfRows":   20,
        "pageNo":      1,
        "_type":       "json",
    }
    if ingredient:
        params["ingrdNm"] = ingredient

    pesticides = []
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10.0)
            if resp.status_code == 200:
                items = (
                    resp.json().get("response", {})
                               .get("body", {})
                               .get("items", {})
                               .get("item", [])
                )
                for p in items:
                    if tree_species and tree_species not in p.get("cropNm", ""):
                        continue
                    pesticides.append({
                        "product_name":       p.get("pestNm", ""),
                        "registration_no":    p.get("regNo", ""),
                        "active_ingredient":  p.get("ingrdNm", ""),
                        "manufacturer":       p.get("compNm", ""),
                        "target_pest":        p.get("pestName", ""),
                        "target_crop":        p.get("cropNm", ""),
                        "dilution_ratio":     p.get("dilutRatio", ""),
                        "application_method": p.get("usageMethod", ""),
                        "re_entry_days":      p.get("safeDay", ""),
                        "expiry_date":        p.get("expDt", ""),
                    })
        except Exception:
            pass

    # API 결과 없으면 AI 보완
    if not pesticides:
        ingredient_filter = f"성분명에 '{ingredient}' 포함" if ingredient else ""
        crop_filter = f"수종은 '{tree_species}'에 적용 가능" if tree_species else ""
        prompt = f"""
한국에서 '{target_pest}' 방제에 등록된 수목용 농약을 JSON 배열로 알려주세요.
{ingredient_filter} {crop_filter}
(다른 설명 없이 JSON 배열만 반환)

[{{
  "product_name": "제품명",
  "active_ingredient": "유효성분 및 함량",
  "dilution_ratio": "희석 배수 (예: 1000배)",
  "application_method": "처리 방법",
  "re_entry_days": 안전 재입 일수,
  "note": "주의사항"
}}]
"""
        response = anthropic_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        import re
        raw = response.content[0].text.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        try:
            pesticides = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\[.*\]", raw, re.DOTALL)
            if m:
                try:
                    pesticides = json.loads(m.group())
                except json.JSONDecodeError:
                    pesticides = []
            else:
                pesticides = []

    return {
        "query": {"target_pest": target_pest, "tree_species": tree_species, "ingredient": ingredient},
        "total_count": len(pesticides),
        "pesticides": pesticides,
        "disclaimer": "농약 사용 전 최신 등록 현황을 농촌진흥청(pis.rda.go.kr)에서 반드시 확인하세요.",
    }


async def get_tree_species_info(
    species_name: str,
    include_pests: bool = True,
) -> dict:
    """
    수종명으로 특성, 주요 병해충, 관리 요령 등 기본 정보를 조회합니다.

    Args:
        species_name: 수종명 (한국명 또는 학명)
        include_pests: 주요 병해충 목록 포함 여부 (기본: True)
    """
    # 국립수목원 식물자원 서비스 API 호출
    url = "https://openapi.kna.go.kr/openapi/service/rest/PlantService/getPlantList"
    params = {
        "serviceKey": settings.DATA_GO_KR_API_KEY,
        "searchNm":   species_name,
        "numOfRows":  5,
        "pageNo":     1,
        "_type":      "json",
    }

    species_data = {}
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10.0)
            if resp.status_code == 200:
                items = (
                    resp.json().get("response", {})
                               .get("body", {})
                               .get("items", {})
                               .get("item", [])
                )
                if items:
                    item = items[0] if isinstance(items, list) else items
                    species_data = {
                        "korean_name":  item.get("korNm", species_name),
                        "scientific_name": item.get("sciNm", ""),
                        "family":       item.get("familyKorNm", ""),
                        "description":  item.get("plantPart", ""),
                        "distribution": item.get("spread", ""),
                    }
        except Exception:
            pass

    # AI로 관리 정보 보완
    pests_request = "주요 병해충 목록과 발생 시기를 포함하세요." if include_pests else ""
    prompt = f"""
한국의 수목 '{species_name}'에 대한 관리 정보를 JSON 형식으로 제공하세요.
{pests_request}
(다른 설명 없이 JSON만 반환)

{{
  "korean_name": "{species_name}",
  "characteristics": "형태적 특성 및 생태 요약",
  "preferred_environment": "생육 환경 (토양, 햇빛, 수분)",
  "seasonal_care": {{
    "spring": "봄철 관리 포인트",
    "summer": "여름철 관리 포인트",
    "autumn": "가을철 관리 포인트",
    "winter": "겨울철 관리 포인트"
  }},
  "major_pests": [
    {{
      "pest_name": "병해충명",
      "occurrence": "발생 시기",
      "symptoms": "피해 증상",
      "control": "방제 방법"
    }}
  ],
  "pruning_guide": "전정 방법 및 시기",
  "fertilization": "시비 방법 및 시기"
}}
"""
    response = anthropic_client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    import re
    raw = response.content[0].text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        ai_data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                ai_data = json.loads(m.group())
            except json.JSONDecodeError:
                ai_data = {"error": "AI 응답 파싱 실패"}
        else:
            ai_data = {"error": "AI 응답 파싱 실패"}

    # 공공 API 데이터와 AI 데이터 병합
    species_data.update(ai_data)
    return species_data
