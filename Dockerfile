# ── 클라우드 배포용 Dockerfile ──────────────────────────
FROM python:3.12-slim

WORKDIR /app

# 의존성 먼저 복사 (레이어 캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY . .

# 포트 오픈
EXPOSE 8000

# 실행 (클라우드 모드: streamable-http)
# main.py 내 transport를 streamable-http 로 바꾼 후 사용
CMD ["python", "main.py"]
