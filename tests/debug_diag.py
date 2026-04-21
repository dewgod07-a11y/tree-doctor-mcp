import sys, io, asyncio, re, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

from anthropic import AsyncAnthropic
from config.settings import settings

async def run():
    client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    prompt = """
당신은 대한민국 산림청 공인 나무의사 전문가입니다.
아래 수목 증상을 분석하여 JSON 형식으로 진단 결과를 반환하세요.

수종: 소나무
증상: 잎이 노랗게 변함
발생 부위: 전체
피해 범위: 일부

반드시 아래 JSON 형식으로만 답변하세요 (다른 설명 없이):
{
  "diagnoses": [
    {
      "pest_name": "병해충명",
      "probability": "높음/보통/낮음",
      "description": "병해충 설명 (2~3문장)",
      "symptoms_match": "증상 일치 이유",
      "immediate_action": "즉시 취해야 할 조치",
      "treatment": "처치 방법",
      "severity": "경미/보통/심각"
    }
  ],
  "general_advice": "전반적인 관리 조언",
  "need_expert": true
}
"""
    resp = await client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text.strip()
    print("RAW 첫 100자:", repr(raw[:100]))
    print("첫 5글자 코드:", [ord(c) for c in raw[:5]])

    cleaned = re.sub(r"```json|```", "", raw).strip()
    print("Cleaned 첫 100자:", repr(cleaned[:100]))

    try:
        r = json.loads(cleaned)
        print("파싱 성공! diagnoses:", len(r.get("diagnoses", [])))
        if r.get("diagnoses"):
            print("첫 진단:", r["diagnoses"][0].get("pest_name"))
    except json.JSONDecodeError as e:
        print("파싱 실패:", e)
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            print("regex fallback 시도...")
            try:
                r2 = json.loads(m.group())
                print("fallback 성공! diagnoses:", len(r2.get("diagnoses", [])))
            except Exception as e2:
                print("fallback 실패:", e2)
                print("매치된 텍스트 처음:", repr(m.group()[:100]))

asyncio.run(run())
