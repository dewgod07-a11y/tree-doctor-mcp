"""
tools/schedule.py
카테고리 4: 수목 관리 일정·이력 Tools (3개)
  - create_tree_care_schedule    : 일정 등록 + 카카오 캘린더 연동
  - get_tree_care_history        : 관리 이력 조회
  - send_care_reminder_to_kakao  : 카카오톡 나챗방 알림 발송
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime
import httpx
from config.settings import settings

# ── 간단한 인메모리 DB (실제 배포 시 SQLite 또는 PostgreSQL로 교체) ─────────
# 실제 DB 연동은 아래 SQLAlchemy 주석 참고
_CARE_DB: list[dict] = []

# SQLAlchemy 사용 예시 (클라우드 배포 시 활성화):
# from sqlalchemy import create_engine, Column, String, DateTime, Text
# from sqlalchemy.orm import declarative_base, Session
# engine = create_engine(settings.DATABASE_URL)
# Base = declarative_base()
# class CareRecord(Base):
#     __tablename__ = "care_records"
#     id = Column(String, primary_key=True)
#     tree_id = Column(String)
#     care_type = Column(String)
#     scheduled_date = Column(String)
#     notes = Column(Text)
#     created_at = Column(DateTime, default=datetime.now)
# Base.metadata.create_all(engine)


async def _sync_to_kakao_calendar(
    title: str,
    date: str,
    notes: str,
    kakao_access_token: str,
) -> str | None:
    """카카오 톡캘린더 API에 일정 등록"""
    url = "https://kapi.kakao.com/v2/api/calendar/create/event"
    headers = {
        "Authorization": f"Bearer {kakao_access_token}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    event_data = {
        "calendar_id": "primary",
        "event": json.dumps({
            "title": title,
            "time": {
                "start_at": f"{date}T09:00:00+09:00",
                "end_at":   f"{date}T10:00:00+09:00",
                "time_zone": "Asia/Seoul",
                "all_day": False,
            },
            "description": notes,
            "color": "GREEN",
        }),
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, headers=headers, data=event_data, timeout=10.0)
            if resp.status_code == 200:
                return resp.json().get("event_id")
        except Exception:
            pass
    return None


async def create_tree_care_schedule(
    tree_id: str,
    care_type: str,
    scheduled_date: str,
    notes: str = "",
    sync_calendar: bool = True,
) -> dict:
    """
    수목 관리 일정을 등록하고 카카오 캘린더와 연동합니다.

    Args:
        tree_id:        관리 수목 ID 또는 위치명 (예: 여의도공원_은행나무_001)
        care_type:      관리 유형 (방제/시비/전정/외과수술/관수/진단)
        scheduled_date: 예정 날짜 (YYYY-MM-DD)
        notes:          특이사항 메모
        sync_calendar:  카카오 캘린더 동기화 여부 (기본: True)
    """
    # 날짜 형식 검증
    try:
        datetime.strptime(scheduled_date, "%Y-%m-%d")
    except ValueError:
        return {"error": "날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력하세요."}

    # 이력 저장
    record_id = str(uuid.uuid4())[:8].upper()
    record = {
        "record_id":      record_id,
        "tree_id":        tree_id,
        "care_type":      care_type,
        "scheduled_date": scheduled_date,
        "notes":          notes,
        "status":         "예정",
        "created_at":     datetime.now().isoformat(),
        "calendar_event_id": None,
    }
    _CARE_DB.append(record)

    # 카카오 캘린더 연동
    calendar_result = {"synced": False, "message": "카카오 액세스 토큰 필요"}
    if sync_calendar:
        # ⚠️ 실제 사용 시: 카카오 OAuth 토큰을 사용자별로 관리해야 합니다
        # PlayMCP 환경에서는 카카오 톡캘린더 MCP를 직접 호출하는 방식 사용
        title = f"🌳 [{care_type}] {tree_id}"
        calendar_result = {
            "synced": False,
            "message": "PlayMCP에서 카카오 톡캘린더 MCP를 함께 활성화하면 자동 연동됩니다.",
            "suggested_title": title,
            "suggested_date": scheduled_date,
        }

    return {
        "success":     True,
        "record_id":   record_id,
        "tree_id":     tree_id,
        "care_type":   care_type,
        "scheduled_date": scheduled_date,
        "notes":       notes,
        "calendar":    calendar_result,
        "message":     f"✅ {tree_id} {care_type} 일정이 {scheduled_date}에 등록되었습니다.",
    }


async def get_tree_care_history(
    tree_id: str = "",
    area_name: str = "",
    start_date: str = "",
    end_date: str = "",
    care_type: str = "",
) -> dict:
    """
    특정 수목 또는 관리 구역의 과거 처리 이력을 조회합니다.

    Args:
        tree_id:    수목 ID (미입력 시 전체)
        area_name:  관리 구역명 (예: 여의도공원 2구역)
        start_date: 조회 시작일 (YYYY-MM-DD)
        end_date:   조회 종료일 (YYYY-MM-DD)
        care_type:  관리 유형 필터
    """
    if not tree_id and not area_name:
        return {"error": "tree_id 또는 area_name 중 하나는 입력해주세요."}

    results = list(_CARE_DB)  # 실제: DB 쿼리로 교체

    # 필터 적용
    if tree_id:
        results = [r for r in results if tree_id.lower() in r["tree_id"].lower()]
    if area_name:
        results = [r for r in results if area_name in r["tree_id"]]
    if care_type:
        results = [r for r in results if r["care_type"] == care_type]
    if start_date:
        results = [r for r in results if r["scheduled_date"] >= start_date]
    if end_date:
        results = [r for r in results if r["scheduled_date"] <= end_date]

    results.sort(key=lambda x: x["scheduled_date"], reverse=True)

    # 통계 요약
    care_type_counts: dict[str, int] = {}
    for r in results:
        care_type_counts[r["care_type"]] = care_type_counts.get(r["care_type"], 0) + 1

    return {
        "query": {
            "tree_id": tree_id,
            "area_name": area_name,
            "start_date": start_date,
            "end_date": end_date,
            "care_type": care_type,
        },
        "total_count": len(results),
        "summary": care_type_counts,
        "records": results,
    }


async def send_care_reminder_to_kakao(
    message: str,
    tree_info: str = "",
    next_care_date: str = "",
    urgency: str = "일반",
) -> dict:
    """
    수목 관리 알림을 카카오톡 나와의 채팅방으로 발송합니다.

    Args:
        message:        알림 내용
        tree_info:      대상 수목 정보 (수종, 위치)
        next_care_date: 다음 처리 예정일 (YYYY-MM-DD)
        urgency:        긴급도 (일반/주의/긴급, 기본: 일반)
    """
    urgency_emoji = {"일반": "🌳", "주의": "⚠️", "긴급": "🚨"}.get(urgency, "🌳")

    # 최종 메시지 구성
    full_message = f"{urgency_emoji} [수목 관리 알림]\n\n{message}"
    if tree_info:
        full_message += f"\n\n📍 대상 수목: {tree_info}"
    if next_care_date:
        full_message += f"\n📅 다음 처리 예정: {next_care_date}"
    full_message += "\n\n- 나무의사 MCP -"

    # 카카오톡 나와의 채팅방 API 호출
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {
        "Authorization": f"Bearer YOUR_KAKAO_ACCESS_TOKEN",  # OAuth 토큰 필요
        "Content-Type": "application/x-www-form-urlencoded",
    }
    template = {
        "object_type": "text",
        "text": full_message,
        "link": {
            "web_url": "https://playmcp.kakao.com",
            "mobile_web_url": "https://playmcp.kakao.com",
        },
    }

    sent = False
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                url,
                headers=headers,
                data={"template_object": json.dumps(template)},
                timeout=10.0,
            )
            sent = resp.status_code == 200
        except Exception:
            pass

    return {
        "success": sent,
        "urgency": urgency,
        "message_preview": full_message[:100] + "...",
        "full_message": full_message,
        "note": (
            "✅ 발송 완료" if sent
            else "⚠️ PlayMCP에서 카카오톡 나챗방 MCP를 함께 활성화하면 자동 발송됩니다."
        ),
    }
