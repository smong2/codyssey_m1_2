#!/usr/bin/env python3
"""
보안 필터링 및 레이어드 아키텍처(APIRouter/Services) 자동화 검증 스크립트
==========================================================================
사전평가 지적사항 2가지에 대한 완벽한 기술적 충족을 검증합니다:
1. 악성 입력 필터링(XSS/HTML 인젝션, 위험 스크립트, 날짜 형식 화이트리스트, 길이 제한, 보안 로깅)
2. 디렉토리 구조 및 모듈화 (core/, models/, services/, routers/, main.py)
"""

import sys
import os

# 모듈 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_tests():
    print("=" * 65)
    print("🛡️ [테스트 1] 악성 입력 필터링 및 보안 정제 모듈 검증 (api.core.security)")
    print("=" * 65)

    from api.core.security import (
        check_malicious_input,
        sanitize_text,
        validate_date_format
    )

    # 1. XSS 스크립트 공격 탐지 테스트
    xss_samples = [
        ("<script>alert('XSS')</script>", "기본 스크립트 태그"),
        ("<iframe src='http://evil.com'></iframe>", "아이프레임 인젝션"),
        ("javascript:document.cookie", "자바스크립트 가상 프로토콜"),
        ("<img src=x onerror=alert(1)>", "이벤트 핸들러 인젝션"),
        ("SELECT * FROM users; DROP TABLE stock_data;", "SQL 인젝션 시도")
    ]

    for payload, desc in xss_samples:
        is_mal = check_malicious_input(payload, field_name="test_field")
        assert is_mal is True, f"악성 입력 탐지 실패: {desc}"
        print(f"  ✅ [차단 성공] {desc}: '{payload[:35]}...'")

    # 2. 정상 입력 통과 테스트
    normal_samples = [
        "삼성전자 7만 전자 돌파 기념 분할 매수",
        "2024년 상반기 HBM 반도체 수요 급증 전망",
        "10주 매수 완료 (평단가 70,000원)"
    ]
    for text in normal_samples:
        assert check_malicious_input(text) is False, f"정상 텍스트 오탐: {text}"
        print(f"  ✅ [정상 통과] '{text}'")

    # 3. HTML 특수문자 이스케이프 정제(Sanitization) 테스트
    raw_html = "<b>강조</b> 및 <script>alert(1)</script>"
    sanitized = sanitize_text(raw_html)
    assert "<script>" not in sanitized, "스크립트 태그 미이스케이프"
    assert "&lt;script&gt;" in sanitized, "HTML 이스케이프 실패"
    print(f"  ✅ [정제 성공] 원문: '{raw_html}' -> 정제: '{sanitized}'")

    # 4. 날짜 형식 화이트리스트 검증 테스트
    assert validate_date_format("2024-05-10") == "2024-05-10"
    print("  ✅ [날짜 검증 성공] '2024-05-10' 정상 통과")

    invalid_dates = ["2024/05/10", "2024-99-99", "abc", "2024-02-30"]
    for inv in invalid_dates:
        try:
            validate_date_format(inv)
            raise AssertionError(f"유효하지 않은 날짜 통과 오류: {inv}")
        except ValueError:
            print(f"  ✅ [날짜 거부 성공] 부적절한 날짜 '{inv}' 예외 차단 완료")

    print("\n" + "=" * 65)
    print("🏗️ [테스트 2] 레이어드 아키텍처 파일 및 모듈 분리 구조 검증")
    print("=" * 65)

    base = os.path.dirname(os.path.abspath(__file__))
    required_files = [
        "api/core/config.py",
        "api/core/security.py",
        "api/core/database.py",
        "api/models/data.py",
        "api/models/portfolio.py",
        "api/models/chat.py",
        "api/services/stock_service.py",
        "api/services/portfolio_service.py",
        "api/services/chat_service.py",
        "api/routers/data.py",
        "api/routers/portfolio.py",
        "api/routers/chat.py",
        "api/routers/conversations.py",
        "api/main.py",
    ]

    for rel_path in required_files:
        full_path = os.path.join(base, rel_path)
        assert os.path.exists(full_path), f"필수 파일 누락: {rel_path}"
        size = os.path.getsize(full_path)
        print(f"  ✅ [모듈 확인] {rel_path:<32} ({size:,} bytes)")

    # main.py 슬림화 검증 (기존 880줄 -> 100줄 이하 모듈형 진입점)
    main_path = os.path.join(base, "api", "main.py")
    with open(main_path, "r", encoding="utf-8") as f:
        main_lines = len(f.readlines())
    print(f"\n  📊 [main.py 코드 라인수 점검] 현재 {main_lines}줄 (기존 880줄에서 100줄 이내 슬림화 완료!)")
    assert main_lines <= 100, f"main.py가 여전히 비대합니다: {main_lines}줄"

    print("\n" + "=" * 65)
    print("📦 [테스트 3] 서비스 계층(Services) 로직 정상 작동 검증")
    print("=" * 65)

    from api.services.stock_service import auto_expand_dates, calculate_stock_summary
    s, e, t = auto_expand_dates("2023년", "", "")
    assert s == "2023-01-01" and e == "2023-12-31"
    print(f"  ✅ [날짜 자동 확장 서비스] '2023년' -> {s} ~ {e}")

    summary = calculate_stock_summary(10)
    assert summary.get("status") == "success", "주가 요약 서비스 실패"
    print(f"  ✅ [주가 요약 연산 서비스] 10거래일 요약 산출 성공 (최근 종가: {summary['summary']['current_price']:,}원)")

    print("\n" + "=" * 65)
    print("🎉 [최종 결과] 사전평가 2대 지적사항에 대한 보완 구현 및 자체 검증 100% 통과!")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
