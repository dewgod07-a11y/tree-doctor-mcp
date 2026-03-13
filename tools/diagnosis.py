"""
tools/diagnosis.py
카테고리 1: 병해충 진단 Tools (4개)

  - diagnose_tree_disease          : 증상 텍스트 → 병해충 진단
  - diagnose_tree_disease_by_image : 사진 URL  → AI 비전 진단
  - get_pest_detail                : 병해충 상세 정보 조회
  - get_seasonal_pest_alert        : 계절별 주의 병해충 알림
"""

from __future__ import annotations
import json
import httpx
from anthropic import Anthropic
from config.settings import settings

anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)


# ── Tool 1: diagnose_tree_disease ────────────────────────────────────────────
async def diagnose_tree_disease(
    tree_species: str,
    symptoms: str,
    location: str = "전체",
    affected_area: str = "일부",
) -> dict:
    """
    수목의 증상을 텍스트로 입력받아 병해충을 진단하고 초기 대응 방법을 반환합니다.

    Args:
        tree_species:  수종명 (예: 소나무, 느티나무, 벚나무)
        symptoms:      증상 설명 (예: 잎이 노랗게 변하고 갈색 점이 생김)
        location:      발생 부위 (잎/줄기/뿌리/전체)
        affected_area: 피해 범위 (예: 일부 가지, 전체)
    """
    prompt = f"""
당신은 대한민국 산림청 공인 나무의사 전문가입니다.
아래 수목 증상을 분석하여 JSON 형식으로 진단 결과를 반환하세요.

수종: {tree_species}
증상: {symptoms}
발생 부위: {location}
피해 범위: {affected_area}

반드시 아래 JSON 형식으로만 답변하세요 (다른 설명 없이):
{{
  "diagnoses": [
    {{
      "pest_name": "병해충명",
      "probability": "높음/보통/낮음",
      "description": "병해충 설명 (2~3문장)",
      "symptoms_match": "증상 일치 이유",
      "immediate_action": "즉시 취해야 할 조치",
      "treatment": "처치 방법",
      "severity": "경미/보통/심각"
    }}
  ],
  "general_advice": "전반적인 관리 조언",
  "need_expert": true
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
                result = {"diagnoses": [], "general_advice": "AI 응답 파싱 실패", "need_expert": True}
        else:
            result = {"diagnoses": [], "general_advice": "AI 응답 파싱 실패", "need_expert": True}
    result["input"] = {
        "tree_species": tree_species,
        "symptoms": symptoms,
        "location": location,
        "affected_area": affected_area,
    }
    return result


# ── Tool 2: diagnose_tree_disease_by_image ───────────────────────────────────
async def diagnose_tree_disease_by_image(
    image_url: str,
    tree_species: str = "모름",
    location: str = "",
) -> dict:
    """
    수목 사진을 업로드하면 AI Vision으로 병해충을 분석합니다.

    Args:
        image_url:    수목 이상 증상 사진 URL (공개 접근 가능한 URL)
        tree_species: 수종명 (모를 경우 '모름' 입력)
        location:     촬영 위치 (예: 서울 여의도)
    """
    prompt = f"""
당신은 대한민국 산림청 공인 나무의사입니다.
첨부된 수목 사진을 보고 병해충 여부를 진단하세요.

알려진 수종: {tree_species}
촬영 위치: {location if location else '미입력'}

반드시 아래 JSON 형식으로만 답변하세요:
{{
  "detected_species": "사진에서 식별된 수종",
  "visible_symptoms": ["관찰된 증상1", "관찰된 증상2"],
  "diagnoses": [
    {{
      "pest_name": "병해충명",
      "confidence": "높음/보통/낮음",
      "description": "설명",
      "treatment": "처치 방법"
    }}
  ],
  "image_quality": "진단에 충분함/불충분함",
  "recommendation": "전문가 방문 권고 여부 및 이유"
}}
"""
    response = anthropic_client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "url", "url": image_url}},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    import re
    raw = response.content[0].text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        return {"error": "AI 응답 파싱 실패", "image_url": image_url}


# ── Tool 3: get_pest_detail ──────────────────────────────────────────────────
async def get_pest_detail(
    pest_name: str,
    include_pesticide: bool = False,
) -> dict:
    """
    병해충 이름으로 상세 정보를 조회합니다. (생태, 피해 양상, 방제 방법, 발생 시기)

    Args:
        pest_name:         병해충 이름 (예: 솔잎혹파리, 밤나무혹벌)
        include_pesticide: 사용 가능한 약제 목록 포함 여부
    """
    # 산림청 임업기술 핸드북 API 호출
    url = f"{settings.FORESTRY_API_BASE}/ForestTechService/getForestTechList"
    params = {
        "serviceKey": settings.DATA_GO_KR_API_KEY,
        "searchNm": pest_name,
        "numOfRows": 5,
        "pageNo": 1,
        "_type": "json",
    }

    items = []
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                items = (
                    data.get("response", {})
                        .get("body", {})
                        .get("items", {})
                        .get("item", [])
                )
        except Exception:
            pass  # API 실패 시 AI fallback으로 전환

    # API 결과 없으면 Claude AI로 보완
    if not items:
        pesticide_field = '"pesticides": ["사용 가능 약제1", "약제2"],' if include_pesticide else ""
        prompt = f"""
한국의 수목 병해충 '{pest_name}'에 대해 아래 JSON 형식으로 정보를 제공하세요.
(다른 설명 없이 JSON만 반환)

[{{
  "pest_name": "{pest_name}",
  "category": "병 또는 해충",
  "host_trees": ["주요 기주 수종 목록"],
  "occurrence_months": [발생 월 숫자 목록],
  "damage_symptoms": "피해 증상 설명",
  "ecology": "생태 및 생활사",
  "control_method": "방제 방법",
  {pesticide_field}
  "prevention": "예방 방법"
}}]
"""
        response = anthropic_client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
        import re
        raw = response.content[0].text.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        try:
            return json.loads(raw)
        except Exception:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                return json.loads(m.group())
            return {"error": "파싱 실패", "pest_name": pest_name}

    return {
        "pest_name": pest_name,
        "data_source": "산림청 임업기술 핸드북 (+ AI 보완)",
        "results": items,
    }


# ── Tool 4: get_seasonal_pest_alert ─────────────────────────────────────────
async def get_seasonal_pest_alert(
    month: int = 0,
    region: str = "전국",
) -> dict:
    """
    현재 월/지역 기반으로 주의 병해충 목록과 예방 조치를 반환합니다.

    Args:
        month:  조회 월 (1~12, 0이면 현재 월 자동 적용)
        region: 지역명 (예: 서울, 경기, 전남)
    """
    from datetime import datetime
    if month == 0:
        month = datetime.now().month

    prompt = f"""
한국의 수목 병해충 전문가로서 {month}월 {region} 지역에서
주의해야 할 수목 병해충을 JSON 형식으로 알려주세요.
(다른 설명 없이 JSON만 반환)

{{
  "month": {month},
  "region": "{region}",
  "alert_level": "주의/경보/관심",
  "pests": [
    {{
      "pest_name": "병해충명",
      "target_trees": ["피해 수종"],
      "risk_level": "높음/보통/낮음",
      "description": "이달 발생 특성",
      "prevention_checklist": ["예방 조치1", "예방 조치2", "예방 조치3"]
    }}
  ],
  "monthly_tip": "이달의 수목 관리 핵심 포인트"
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
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        return {"error": "파싱 실패", "month": month, "region": region}
