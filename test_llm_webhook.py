#!/usr/bin/env python3
"""
LLM Webhook 테스트 스크립트

Kubernetes 환경에서 GPT-5 LLM 호출이 정상 작동하는지 테스트합니다.
port-forward가 실행 중이어야 합니다.

사용법:
    # 1. port-forward 실행 (다른 터미널에서)
    kubectl port-forward -n agent-system svc/router-agent 5000:5000

    # 2. 테스트 실행
    python test_llm_webhook.py

    # 또는 특정 테스트만 실행
    python test_llm_webhook.py --test health
    python test_llm_webhook.py --test classification
    python test_llm_webhook.py --test webhook
"""

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional

try:
    import requests
except ImportError:
    print("requests 패키지가 필요합니다: pip install requests")
    sys.exit(1)


# ========================================
# 설정
# ========================================
ROUTER_URL = "http://localhost:5000"
TIMEOUT_SHORT = 30   # 분류 테스트용
TIMEOUT_LONG = 300   # 전체 webhook 테스트용 (5분)


# ========================================
# 색상 출력 (Windows 지원)
# ========================================
try:
    import colorama
    colorama.init()
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
except ImportError:
    GREEN = RED = YELLOW = BLUE = RESET = BOLD = ""


def print_header(title: str):
    """헤더 출력"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}  {title}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")


def print_success(msg: str):
    print(f"{GREEN}✅ {msg}{RESET}")


def print_error(msg: str):
    print(f"{RED}❌ {msg}{RESET}")


def print_warning(msg: str):
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def print_info(msg: str):
    print(f"{BLUE}ℹ️  {msg}{RESET}")


def print_json(data: Dict[Any, Any], title: str = "Result"):
    """JSON 데이터를 예쁘게 출력"""
    print(f"\n{BOLD}{title}:{RESET}")
    print(json.dumps(data, indent=2, ensure_ascii=False))


# ========================================
# 테스트 데이터
# ========================================

# 실제 Jira 이슈와 유사한 테스트 데이터 (ADF 형식 포함)
SAMPLE_JIRA_ISSUE = {
    "key": "TEST-LLM-001",
    "fields": {
        "issuetype": {
            "name": "Task"
        },
        "summary": "Material DB에 SP16_2025 철골 재질 추가",
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Steel Material DB 명세서"}
                    ]
                },
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [
                        {"type": "text", "text": "기본 정보"}
                    ]
                },
                {
                    "type": "bulletList",
                    "content": [
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": "Standard: SP16_2025_TEST"}
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": "DB 목록: C235 / C245 / C255"}
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "listItem",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [
                                        {"type": "text", "text": "Data unit: Length = mm, Force = N"}
                                    ]
                                }
                            ]
                        }
                    ]
                },
                {
                    "type": "heading",
                    "attrs": {"level": 2},
                    "content": [
                        {"type": "text", "text": "공통 물성치"}
                    ]
                },
                {
                    "type": "table",
                    "content": [
                        {
                            "type": "tableRow",
                            "content": [
                                {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "DB"}]}]},
                                {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Es"}]}]},
                                {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "nu"}]}]},
                                {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Fy"}]}]},
                                {"type": "tableHeader", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Fu"}]}]}
                            ]
                        },
                        {
                            "type": "tableRow",
                            "content": [
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "C235"}]}]},
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "2.06E+05"}]}]},
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "0.3"}]}]},
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "230"}]}]},
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "350"}]}]}
                            ]
                        },
                        {
                            "type": "tableRow",
                            "content": [
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "C245"}]}]},
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "2.06E+05"}]}]},
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "0.3"}]}]},
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "240"}]}]},
                                {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "360"}]}]}
                            ]
                        }
                    ]
                }
            ]
        }
    }
}

# 간단한 테스트용 이슈 (plain text)
SIMPLE_JIRA_ISSUE = {
    "key": "TEST-LLM-002",
    "fields": {
        "issuetype": {
            "name": "Task"
        },
        "summary": "SDB Material DB 추가 요청 - 테스트",
        "description": """
SDB 시스템에 테스트용 Steel 재질을 추가해주세요.

## 기본 정보
- Standard: TEST_STEEL_2025
- 재질: TEST_C235

## 물성치
- 탄성계수 (Es): 2.06E+05 MPa
- 포아송비 (nu): 0.3
- 항복강도 (Fy): 235 MPa
- 인장강도 (Fu): 360 MPa

이것은 LLM 호출 테스트를 위한 이슈입니다.
"""
    }
}


# ========================================
# 테스트 함수
# ========================================

def test_health() -> bool:
    """
    헬스 체크 테스트
    Router Agent와 SDB Agent가 정상인지 확인
    """
    print_header("1. 헬스 체크 테스트")

    try:
        print_info(f"GET {ROUTER_URL}/health")
        response = requests.get(f"{ROUTER_URL}/health", timeout=10)

        if response.status_code != 200:
            print_error(f"상태 코드: {response.status_code}")
            print(response.text)
            return False

        result = response.json()
        print_json(result)

        # 상태 확인
        status = result.get("status")
        agents = result.get("agents", {})

        if status == "healthy":
            print_success("Router Agent: 정상")
        else:
            print_warning(f"Router Agent 상태: {status}")

        # 각 Agent 상태 확인
        for agent_name, is_healthy in agents.items():
            if is_healthy:
                print_success(f"{agent_name}: 정상")
            else:
                print_error(f"{agent_name}: 비정상")

        if not agents.get("sdb-agent"):
            print_error("SDB Agent가 응답하지 않습니다!")
            print_warning("kubectl port-forward -n agent-system svc/sdb-agent 5001:5001 도 필요할 수 있습니다")
            return False

        return status == "healthy"

    except requests.exceptions.ConnectionError:
        print_error(f"{ROUTER_URL}에 연결할 수 없습니다!")
        print_warning("port-forward가 실행 중인지 확인하세요:")
        print("  kubectl port-forward -n agent-system svc/router-agent 5000:5000")
        return False
    except Exception as e:
        print_error(f"헬스 체크 실패: {e}")
        return False


def test_classification() -> Optional[Dict]:
    """
    LLM 분류 테스트 (Agent 호출 없음)
    GPT-5 API 호출이 정상 작동하는지 확인
    """
    print_header("2. LLM 분류 테스트 (Intent Classification)")

    print_info("이 테스트는 Router Agent의 LLM 호출만 테스트합니다.")
    print_info("SDB Agent는 호출하지 않습니다.")

    payload = {"issue": SIMPLE_JIRA_ISSUE}

    print(f"\n{BOLD}테스트 이슈:{RESET}")
    print(f"  - Key: {SIMPLE_JIRA_ISSUE['key']}")
    print(f"  - Summary: {SIMPLE_JIRA_ISSUE['fields']['summary']}")

    try:
        print_info(f"POST {ROUTER_URL}/test-classification")
        start_time = time.time()

        response = requests.post(
            f"{ROUTER_URL}/test-classification",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT_SHORT
        )

        elapsed = time.time() - start_time
        print_info(f"소요 시간: {elapsed:.2f}초")

        if response.status_code != 200:
            print_error(f"상태 코드: {response.status_code}")
            print(response.text[:500])

            # GPT-5 관련 에러 확인
            if "max_tokens" in response.text:
                print_error("max_tokens 파라미터 오류! max_completion_tokens로 변경 필요")
            elif "temperature" in response.text:
                print_error("temperature 파라미터 오류! GPT-5는 기본값만 지원")

            return None

        result = response.json()
        print_json(result)

        # 결과 분석
        classification = result.get("classification", {})
        agent = classification.get("agent")
        confidence = classification.get("confidence", 0)
        reasoning = classification.get("reasoning", "")
        cached = classification.get("cached", False)

        print(f"\n{BOLD}분류 결과:{RESET}")
        print(f"  - 선택된 Agent: {agent}")
        print(f"  - 신뢰도: {confidence:.2f}")
        print(f"  - 캐시 사용: {'예' if cached else '아니오'}")
        print(f"  - 이유: {reasoning[:100]}...")

        if agent and confidence > 0:
            print_success("LLM 분류 호출 성공!")
            if cached:
                print_warning("캐시된 결과입니다. 새로운 LLM 호출을 테스트하려면 Redis 캐시를 초기화하세요.")
            return result
        else:
            print_error("LLM 분류 실패")
            return None

    except requests.exceptions.Timeout:
        print_error(f"타임아웃 ({TIMEOUT_SHORT}초)")
        print_warning("LLM API 호출이 오래 걸리고 있습니다.")
        return None
    except Exception as e:
        print_error(f"분류 테스트 실패: {e}")

        # 상세 에러 분석
        error_str = str(e)
        if "max_tokens" in error_str:
            print_error("max_tokens 파라미터 오류 감지!")
            print_warning("GPT-5는 max_completion_tokens를 사용해야 합니다.")
        elif "temperature" in error_str:
            print_error("temperature 파라미터 오류 감지!")
            print_warning("GPT-5는 기본 temperature만 지원합니다.")

        return None


def test_webhook_full_flow(use_adf: bool = False) -> Optional[Dict]:
    """
    전체 Webhook 흐름 테스트
    Router Agent -> SDB Agent 전체 파이프라인 테스트

    Args:
        use_adf: True면 ADF 형식 이슈 사용, False면 plain text 이슈 사용
    """
    print_header("3. 전체 Webhook 흐름 테스트")

    print_warning("이 테스트는 실제로 SDB Agent의 LLM을 호출합니다.")
    print_warning("Bitbucket API 호출이 발생할 수 있습니다.")
    print_info(f"최대 대기 시간: {TIMEOUT_LONG}초 (5분)")

    # 테스트 이슈 선택
    issue = SAMPLE_JIRA_ISSUE if use_adf else SIMPLE_JIRA_ISSUE
    issue_type = "ADF 형식" if use_adf else "Plain Text"

    webhook_payload = {
        "webhookEvent": "jira:issue_created",
        "issue": issue
    }

    print(f"\n{BOLD}테스트 이슈 ({issue_type}):{RESET}")
    print(f"  - Key: {issue['key']}")
    print(f"  - Summary: {issue['fields']['summary']}")

    try:
        print_info(f"POST {ROUTER_URL}/webhook")
        start_time = time.time()

        response = requests.post(
            f"{ROUTER_URL}/webhook",
            json=webhook_payload,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT_LONG
        )

        elapsed = time.time() - start_time

        print(f"\n{BOLD}응답:{RESET}")
        print(f"  - 상태 코드: {response.status_code}")
        print(f"  - 소요 시간: {elapsed:.2f}초")

        if response.status_code != 200:
            print_error(f"Webhook 처리 실패: {response.status_code}")

            try:
                error_detail = response.json()
                print_json(error_detail, "에러 상세")

                # 에러 분석
                detail = error_detail.get("detail", "")
                if "max_tokens" in detail or "max_tokens" in str(error_detail):
                    print_error("max_tokens 파라미터 오류!")
                    print_warning("sdb-agent의 코드에서 max_tokens를 max_completion_tokens로 변경하세요.")
                elif "temperature" in detail:
                    print_error("temperature 파라미터 오류!")

            except:
                print(response.text[:500])

            return None

        result = response.json()
        print_json(result)

        # 결과 분석
        status = result.get("status")
        agent = result.get("agent")
        sdb_result = result.get("result", {})

        print(f"\n{BOLD}처리 결과:{RESET}")
        print(f"  - 전체 상태: {status}")
        print(f"  - 선택된 Agent: {agent}")

        if status == "success":
            print_success("전체 Webhook 흐름 테스트 성공!")

            # SDB Agent 결과 분석
            sdb_status = sdb_result.get("status")
            modified_files = sdb_result.get("modified_files", [])
            pr_url = sdb_result.get("pr_url")
            errors = sdb_result.get("errors", [])

            print(f"\n{BOLD}SDB Agent 결과:{RESET}")
            print(f"  - 상태: {sdb_status}")
            print(f"  - 수정된 파일: {len(modified_files)}개")

            if pr_url:
                print_success(f"PR 생성됨: {pr_url}")

            if errors:
                print_warning(f"에러 {len(errors)}개:")
                for err in errors[:3]:
                    print(f"    - {err}")

            return result

        elif status == "uncertain":
            print_warning("분류 신뢰도가 낮아 처리되지 않았습니다.")
            return result

        else:
            print_error(f"처리 실패: {status}")
            return None

    except requests.exceptions.Timeout:
        print_error(f"타임아웃 ({TIMEOUT_LONG}초)")
        print_warning("SDB Agent 처리가 오래 걸리고 있습니다.")
        print_info("kubectl logs -f -n agent-system deployment/sdb-agent 로 로그를 확인하세요.")
        return None
    except Exception as e:
        print_error(f"Webhook 테스트 실패: {e}")
        return None


def run_all_tests():
    """모든 테스트 순차 실행"""
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}  LLM Webhook 테스트 시작{RESET}")
    print(f"{BOLD}  시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BOLD}{'='*70}{RESET}")

    results = {
        "health": False,
        "classification": False,
        "webhook": False
    }

    # 1. 헬스 체크
    results["health"] = test_health()

    if not results["health"]:
        print_error("\n헬스 체크 실패. 테스트를 중단합니다.")
        print_warning("\n해결 방법:")
        print("  1. kubectl get pods -n agent-system 으로 Pod 상태 확인")
        print("  2. kubectl port-forward -n agent-system svc/router-agent 5000:5000 실행")
        return results

    # 2. 분류 테스트 (LLM 호출)
    print("\n")
    classification_result = test_classification()
    results["classification"] = classification_result is not None

    if not results["classification"]:
        print_error("\nLLM 분류 테스트 실패.")
        print_warning("GPT-5 API 호환성 문제일 수 있습니다.")
        print_warning("로그 확인: kubectl logs -n agent-system deployment/router-agent")

        # 계속할지 확인
        try:
            continue_test = input("\n전체 Webhook 테스트를 계속하시겠습니까? (y/N): ")
            if continue_test.lower() != 'y':
                return results
        except:
            return results

    # 3. 전체 Webhook 테스트
    print("\n")
    webhook_result = test_webhook_full_flow(use_adf=False)
    results["webhook"] = webhook_result is not None and webhook_result.get("status") == "success"

    # 최종 결과 요약
    print_header("테스트 결과 요약")

    for test_name, passed in results.items():
        if passed:
            print_success(f"{test_name}: 통과")
        else:
            print_error(f"{test_name}: 실패")

    all_passed = all(results.values())

    if all_passed:
        print(f"\n{GREEN}{BOLD}모든 테스트 통과! GPT-5 LLM 호출이 정상 작동합니다.{RESET}")
    else:
        print(f"\n{RED}{BOLD}일부 테스트 실패. 로그를 확인하세요.{RESET}")
        print_info("kubectl logs -n agent-system deployment/router-agent")
        print_info("kubectl logs -n agent-system deployment/sdb-agent")

    return results


# ========================================
# 메인 실행
# ========================================

def main():
    parser = argparse.ArgumentParser(
        description="LLM Webhook 테스트 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예제:
  python test_llm_webhook.py                  # 모든 테스트 실행
  python test_llm_webhook.py --test health    # 헬스 체크만
  python test_llm_webhook.py --test classification  # LLM 분류만
  python test_llm_webhook.py --test webhook   # 전체 webhook 테스트만
  python test_llm_webhook.py --test webhook --adf  # ADF 형식 이슈로 테스트

사전 준비:
  kubectl port-forward -n agent-system svc/router-agent 5000:5000
        """
    )

    parser.add_argument(
        "--test", "-t",
        choices=["health", "classification", "webhook", "all"],
        default="all",
        help="실행할 테스트 (기본값: all)"
    )

    parser.add_argument(
        "--adf",
        action="store_true",
        help="ADF 형식 Jira 이슈로 테스트 (webhook 테스트에만 적용)"
    )

    parser.add_argument(
        "--url",
        default="http://localhost:5000",
        help="Router Agent URL (기본값: http://localhost:5000)"
    )

    args = parser.parse_args()

    # URL 설정 (모듈 레벨 변수 업데이트)
    import test_llm_webhook
    test_llm_webhook.ROUTER_URL = args.url

    print(f"""
{BOLD}╔═══════════════════════════════════════════════════════════════════╗
║          LLM Webhook 테스트 (GPT-5 호환성 확인)                      ║
╚═══════════════════════════════════════════════════════════════════╝{RESET}

대상 URL: {args.url}
테스트: {args.test}
    """)

    if args.test == "all":
        run_all_tests()
    elif args.test == "health":
        test_health()
    elif args.test == "classification":
        test_classification()
    elif args.test == "webhook":
        test_webhook_full_flow(use_adf=args.adf)


if __name__ == "__main__":
    main()
