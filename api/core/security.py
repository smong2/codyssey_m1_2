import re
import html
import logging
from datetime import datetime
try:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response
except ImportError:
    class BaseHTTPMiddleware:
        def __init__(self, app):
            self.app = app
    Request = object
    Response = object

# 보안 전용 로거 설정
logger = logging.getLogger("security")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [SECURITY] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# 악성 패턴 정규식 (XSS, Script injection, 위험 프로토콜 등)
MALICIOUS_PATTERNS = [
    re.compile(r'<\s*script[^>]*>', re.IGNORECASE),
    re.compile(r'javascript\s*:', re.IGNORECASE),
    re.compile(r'onload\s*=', re.IGNORECASE),
    re.compile(r'onerror\s*=', re.IGNORECASE),
    re.compile(r'onclick\s*=', re.IGNORECASE),
    re.compile(r'<\s*iframe[^>]*>', re.IGNORECASE),
    re.compile(r'document\.cookie', re.IGNORECASE),
    re.compile(r'alert\s*\(', re.IGNORECASE),
    re.compile(r'eval\s*\(', re.IGNORECASE),
    re.compile(r'union\s+select', re.IGNORECASE),
    re.compile(r'drop\s+table', re.IGNORECASE),
]

def check_malicious_input(text: str, field_name: str = "input") -> bool:
    """텍스트 내 위험 스크립트 또는 공격 패턴이 포함되어 있는지 검사합니다."""
    if not text or not isinstance(text, str):
        return False
        
    for pattern in MALICIOUS_PATTERNS:
        if pattern.search(text):
            log_security_alert(
                field_name=field_name,
                detail=f"악성 패턴 탐지: {pattern.pattern}",
                payload=text[:100]
            )
            return True
    return False

def sanitize_text(text: str) -> str:
    """HTML 특수문자를 안전하게 이스케이프하고 위험 태그를 제거/치환합니다."""
    if not text or not isinstance(text, str):
        return ""
    # 1. HTML 엔티티 이스케이프 (< -> &lt;, > -> &gt;, & -> &amp;)
    escaped = html.escape(text.strip())
    # 2. 위험 프로토콜 치환
    sanitized = re.sub(r'javascript\s*:', 'blocked-script:', escaped, flags=re.IGNORECASE)
    return sanitized

def validate_date_format(date_str: str) -> str:
    """YYYY-MM-DD 형식 및 유효한 실제 날짜인지 검증합니다."""
    if not date_str or not isinstance(date_str, str):
        raise ValueError("날짜는 필수 입력 항목입니다.")
    date_str = date_str.strip()
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        raise ValueError("날짜는 반드시 YYYY-MM-DD 형식(예: 2024-05-10)이어야 합니다.")
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"유효하지 않은 날짜입니다: {date_str}")
    return date_str

def log_security_alert(field_name: str, detail: str, payload: str = "", client_ip: str = "unknown"):
    """보안 위협 시도에 대해 보안 감사 로그를 기록합니다."""
    logger.warning(
        f"[ALERT] IP={client_ip} | Field='{field_name}' | Detail={detail} | Payload='{payload}'"
    )

class SecurityLoggingMiddleware(BaseHTTPMiddleware):
    """
    모든 들어오는 HTTP 요청을 모니터링하고 보안 헤더를 추가하는 미들웨어
    """
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # 쿼리 스트링 악성 입력 사전 검사
        query_params = str(request.query_params)
        if check_malicious_input(query_params, field_name=f"query:{path}"):
            log_security_alert(
                field_name=path,
                detail="URL 쿼리 파라미터에서 악성 스크립트 시도 차단",
                payload=query_params,
                client_ip=client_ip
            )

        response: Response = await call_next(request)

        # 브라우저 보안 헤더 주입
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        return response
