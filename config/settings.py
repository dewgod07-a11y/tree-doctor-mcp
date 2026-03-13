import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    DATA_GO_KR_API_KEY: str = os.getenv("DATA_GO_KR_API_KEY", "")
    FORESTRY_API_BASE: str = "https://openapi.forest.go.kr/openapi/service"
    KNA_API_BASE: str = "https://openapi.kna.go.kr/openapi/service"
    KAKAO_REST_API_KEY: str = os.getenv("KAKAO_REST_API_KEY", "")
    KAKAO_MAP_API_KEY: str = os.getenv("KAKAO_MAP_API_KEY", "")
    KAKAO_MAP_API_BASE: str = "https://dapi.kakao.com/v2/local"
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = False
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./tree_doctor.db")


settings = Settings()
