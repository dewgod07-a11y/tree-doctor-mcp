"""
tools/prescription.py
카테고리 3: 수목 처방 데이터베이스 Tools (3개)
  - get_treatment_prescription  : 수목 처방 조회
  - search_approved_pesticide   : 승인 농약 검색
  - get_tree_species_info       : 수종 정보 조회
"""
from __future__ import annotations
import json
import re
from anthropic import AsyncAnthropic
from config.settings import settings

anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


def _parse_json(raw: str):
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"[\[{].*[\]}]", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return None


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
      "method": "처치 방법명",
      "timing": "처치 적기",
      "procedure": "세부 처치 절차",
      "frequency": "처치 횟수 및 간격",
      "precautions": ["주의사항1", "주의사항2"]
    }}
  ],
  "recommended_pesticides": [
    {{
      "product_name": "약제명",
      "active_ingredient": "유효성분",
      "dilution_ratio": "희석 배수",
      "application_method": "처리 방법"
    }}
  ],
  "follow_up": "처치 후 모니터링 방법",
  "need_professional": true,
  "disclaimer": "이 처방은 참고용이며 실제 처방은 나무의사에게 받으세요."
}}
"""
    try:
        response = await anthropic_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        result = _parse_json(response.content[0].text)
        if result:
            return result
    except Exception:
        pass
    return {
        "pest_name": pest_name,
        "tree_species": tree_species,
        "error": "처방 정보를 가져오지 못했습니다. 잠시 후 다시 시도해주세요.",
    }


async def search_approved_pesticide(
    target_pest: str = "",
    tree_species: str = "",
    ingredient: str = "",
) -> dict:
    """
    수목 병해충 방제용으로 승인된 농약을 검색합니다.
    농약 제품명·성분명으로도 검색 가능합니다.

    Args:
        target_pest:  방제 대상 병해충명 또는 농약 제품명 (예: 스미치온, 솔잎혹파리)
        tree_species: 적용 수종 (미입력 시 전체)
        ingredient:   유효성분명 검색 (예: 이미다클로프리드, 페니트로티온)
    """
    if ingredient and not target_pest:
        query_desc = f"'{ingredient}' 성분(또는 제품명)에 관한 농약"
    elif target_pest:
        query_desc = f"'{target_pest}' 방제에 등록된 수목용 농약"
    else:
        query_desc = "대표적인 수목용 농약"

    crop_filter = f"수종 '{tree_species}'에 적용 가능한 것만" if tree_species else ""

    prompt = f"""
한국에서 {query_desc}을 JSON 배열로 알려주세요. {crop_filter}
(다른 설명 없이 JSON 배열만 반환)

[{{
  "product_name": "제품명",
  "active_ingredient": "유효성분 및 함량",
  "dilution_ratio": "희석 배수 (예: 1000배)",
  "application_method": "처리 방법",
  "re_entry_days": 3,
  "note": "주의사항"
}}]
"""
    try:
        response = await anthropic_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        result = _parse_json(response.content[0].text)
        pesticides = result if isinstance(result, list) else []
    except Exception:
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
    pests_request = "주요 병해충 최대 3종만 간략히 포함하세요." if include_pests else '"major_pests": [],'
    prompt = f"""
한국의 수목 '{species_name}'에 대한 관리 정보를 JSON 형식으로 제공하세요.
{pests_request}
각 항목은 1~2문장으로 간결하게 작성하세요.
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
    try:
        response = await anthropic_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        result = _parse_json(response.content[0].text)
        if result:
            return result
    except Exception:
        pass
    return {"species_name": species_name, "error": "수종 정보를 가져오지 못했습니다. 잠시 후 다시 시도해주세요."}
