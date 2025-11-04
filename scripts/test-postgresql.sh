#!/bin/bash
# PostgreSQL 통합 테스트 스크립트
# Router Agent로 가짜 Webhook을 전송하고 DB에 저장되는지 검증

set -e  # 에러 발생 시 즉시 종료

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 네임스페이스 설정
NAMESPACE="agent-system"
ROUTER_SERVICE="router-agent-svc"
ROUTER_PORT="5000"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PostgreSQL 통합 테스트${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 1. Kubernetes 리소스 확인
echo -e "${YELLOW}[1/6] Kubernetes 리소스 확인 중...${NC}"
echo ""

# PostgreSQL Pod 확인
echo -n "  - PostgreSQL Pod: "
if kubectl get pod -n $NAMESPACE -l app=postgresql | grep -q "Running"; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not Running${NC}"
    echo -e "${RED}Error: PostgreSQL Pod가 실행 중이 아닙니다.${NC}"
    exit 1
fi

# Router Agent Pod 확인
echo -n "  - Router Agent Pod: "
if kubectl get pod -n $NAMESPACE -l app=router-agent | grep -q "Running"; then
    echo -e "${GREEN}✓ Running${NC}"
else
    echo -e "${RED}✗ Not Running${NC}"
    echo -e "${RED}Error: Router Agent Pod가 실행 중이 아닙니다.${NC}"
    exit 1
fi

# PostgreSQL Service 확인
echo -n "  - PostgreSQL Service: "
if kubectl get svc postgresql -n $NAMESPACE &> /dev/null; then
    echo -e "${GREEN}✓ Exists${NC}"
else
    echo -e "${RED}✗ Not Found${NC}"
    exit 1
fi

# Router Agent Service 확인
echo -n "  - Router Agent Service: "
if kubectl get svc $ROUTER_SERVICE -n $NAMESPACE &> /dev/null; then
    echo -e "${GREEN}✓ Exists${NC}"
else
    echo -e "${RED}✗ Not Found${NC}"
    exit 1
fi

echo ""

# 2. PostgreSQL 연결 테스트
echo -e "${YELLOW}[2/6] PostgreSQL 연결 테스트...${NC}"
echo ""

POSTGRES_POD=$(kubectl get pod -n $NAMESPACE -l app=postgresql -o jsonpath='{.items[0].metadata.name}')
echo "  PostgreSQL Pod: $POSTGRES_POD"

# 테이블 존재 확인
echo -n "  - 테이블 존재 확인: "
TABLE_COUNT=$(kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U agent_user -d agent_system -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name IN ('request_history', 'classification_history', 'code_change_history', 'performance_metrics');" 2>/dev/null | tr -d ' ')

if [ "$TABLE_COUNT" -eq "4" ]; then
    echo -e "${GREEN}✓ 4개 테이블 확인${NC}"
else
    echo -e "${RED}✗ 테이블 누락 (${TABLE_COUNT}/4)${NC}"
    echo -e "${RED}Error: 필요한 테이블이 존재하지 않습니다.${NC}"
    exit 1
fi

echo ""

# 3. 테스트 전 기존 데이터 확인
echo -e "${YELLOW}[3/6] 테스트 전 데이터 상태 확인...${NC}"
echo ""

BEFORE_REQUEST_COUNT=$(kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U agent_user -d agent_system -t -c "SELECT COUNT(*) FROM request_history WHERE issue_key='TEST-DB-001';" 2>/dev/null | tr -d ' ')
BEFORE_CLASSIFICATION_COUNT=$(kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U agent_user -d agent_system -t -c "SELECT COUNT(*) FROM classification_history WHERE issue_key='TEST-DB-001';" 2>/dev/null | tr -d ' ')

echo "  - 기존 request_history (TEST-DB-001): $BEFORE_REQUEST_COUNT"
echo "  - 기존 classification_history (TEST-DB-001): $BEFORE_CLASSIFICATION_COUNT"
echo ""

# 4. 가짜 Webhook 전송
echo -e "${YELLOW}[4/6] 가짜 Webhook 전송 중...${NC}"
echo ""

# Port-forward 시작 (백그라운드)
echo "  Port-forward 시작: localhost:8080 -> $ROUTER_SERVICE:$ROUTER_PORT"
kubectl port-forward -n $NAMESPACE svc/$ROUTER_SERVICE 8080:$ROUTER_PORT > /dev/null 2>&1 &
PORT_FORWARD_PID=$!

# Port-forward가 준비될 때까지 대기
sleep 3

# 가짜 Webhook 페이로드 생성
TIMESTAMP=$(date +%s)
WEBHOOK_PAYLOAD=$(cat <<EOF
{
  "webhookEvent": "jira:issue_created",
  "issue": {
    "key": "TEST-DB-001",
    "fields": {
      "summary": "PostgreSQL 통합 테스트 - DB 저장 검증",
      "description": "이 이슈는 PostgreSQL 데이터베이스 저장을 테스트하기 위한 것입니다. Timestamp: $TIMESTAMP",
      "issuetype": {
        "name": "Task"
      },
      "priority": {
        "name": "Medium"
      }
    }
  },
  "user": {
    "displayName": "Test User",
    "emailAddress": "test@example.com"
  },
  "timestamp": $TIMESTAMP
}
EOF
)

echo "  Webhook 페이로드:"
echo "$WEBHOOK_PAYLOAD" | sed 's/^/    /'
echo ""

# Webhook 전송
echo -n "  Webhook 전송: "
HTTP_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
  -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d "$WEBHOOK_PAYLOAD" \
  --max-time 30 2>&1)

# Port-forward 종료
kill $PORT_FORWARD_PID 2>/dev/null || true

if [ "$HTTP_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ 성공 (HTTP 200)${NC}"
elif [ "$HTTP_RESPONSE" = "000" ]; then
    echo -e "${RED}✗ 실패 (연결 오류)${NC}"
    echo -e "${RED}Error: Router Agent에 연결할 수 없습니다.${NC}"
    exit 1
else
    echo -e "${YELLOW}⚠ 경고 (HTTP $HTTP_RESPONSE)${NC}"
fi

echo ""

# 5. 데이터베이스 검증
echo -e "${YELLOW}[5/6] 데이터베이스 검증 중...${NC}"
echo ""

# 잠시 대기 (비동기 처리를 위해)
echo "  데이터 저장 대기 중 (3초)..."
sleep 3

# request_history 확인
echo -n "  - request_history 저장 확인: "
AFTER_REQUEST_COUNT=$(kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U agent_user -d agent_system -t -c "SELECT COUNT(*) FROM request_history WHERE issue_key='TEST-DB-001';" 2>/dev/null | tr -d ' ')

if [ "$AFTER_REQUEST_COUNT" -gt "$BEFORE_REQUEST_COUNT" ]; then
    echo -e "${GREEN}✓ 저장됨 (+$((AFTER_REQUEST_COUNT - BEFORE_REQUEST_COUNT))건)${NC}"
    REQUEST_SAVED=true
else
    echo -e "${RED}✗ 저장 안됨${NC}"
    REQUEST_SAVED=false
fi

# classification_history 확인
echo -n "  - classification_history 저장 확인: "
AFTER_CLASSIFICATION_COUNT=$(kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U agent_user -d agent_system -t -c "SELECT COUNT(*) FROM classification_history WHERE issue_key='TEST-DB-001';" 2>/dev/null | tr -d ' ')

if [ "$AFTER_CLASSIFICATION_COUNT" -gt "$BEFORE_CLASSIFICATION_COUNT" ]; then
    echo -e "${GREEN}✓ 저장됨 (+$((AFTER_CLASSIFICATION_COUNT - BEFORE_CLASSIFICATION_COUNT))건)${NC}"
    CLASSIFICATION_SAVED=true
else
    echo -e "${RED}✗ 저장 안됨${NC}"
    CLASSIFICATION_SAVED=false
fi

# performance_metrics 확인
echo -n "  - performance_metrics 저장 확인: "
METRICS_COUNT=$(kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U agent_user -d agent_system -t -c "SELECT COUNT(*) FROM performance_metrics WHERE agent_name='router-agent' AND created_at > NOW() - INTERVAL '1 minute';" 2>/dev/null | tr -d ' ')

if [ "$METRICS_COUNT" -gt "0" ]; then
    echo -e "${GREEN}✓ 저장됨 (${METRICS_COUNT}건)${NC}"
    METRICS_SAVED=true
else
    echo -e "${YELLOW}⚠ 최근 1분 내 데이터 없음${NC}"
    METRICS_SAVED=false
fi

echo ""

# 6. 상세 데이터 조회
echo -e "${YELLOW}[6/6] 저장된 데이터 상세 조회...${NC}"
echo ""

if [ "$REQUEST_SAVED" = true ]; then
    echo "  📝 최근 저장된 request_history:"
    kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U agent_user -d agent_system -c \
        "SELECT id, issue_key, webhook_event, status, created_at FROM request_history WHERE issue_key='TEST-DB-001' ORDER BY created_at DESC LIMIT 3;" 2>/dev/null | sed 's/^/    /'
    echo ""
fi

if [ "$CLASSIFICATION_SAVED" = true ]; then
    echo "  🎯 최근 저장된 classification_history:"
    kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U agent_user -d agent_system -c \
        "SELECT id, issue_key, classified_agent, confidence, cached, created_at FROM classification_history WHERE issue_key='TEST-DB-001' ORDER BY created_at DESC LIMIT 3;" 2>/dev/null | sed 's/^/    /'
    echo ""
fi

if [ "$METRICS_SAVED" = true ]; then
    echo "  📊 최근 저장된 performance_metrics (router-agent):"
    kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U agent_user -d agent_system -c \
        "SELECT id, agent_name, metric_type, metric_value, created_at FROM performance_metrics WHERE agent_name='router-agent' ORDER BY created_at DESC LIMIT 5;" 2>/dev/null | sed 's/^/    /'
    echo ""
fi

# 7. 결과 요약
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}테스트 결과 요약${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

TOTAL_TESTS=3
PASSED_TESTS=0

if [ "$REQUEST_SAVED" = true ]; then
    echo -e "  ${GREEN}✓${NC} request_history 저장"
    ((PASSED_TESTS++))
else
    echo -e "  ${RED}✗${NC} request_history 저장 실패"
fi

if [ "$CLASSIFICATION_SAVED" = true ]; then
    echo -e "  ${GREEN}✓${NC} classification_history 저장"
    ((PASSED_TESTS++))
else
    echo -e "  ${RED}✗${NC} classification_history 저장 실패"
fi

if [ "$METRICS_SAVED" = true ]; then
    echo -e "  ${GREEN}✓${NC} performance_metrics 저장"
    ((PASSED_TESTS++))
else
    echo -e "  ${YELLOW}⚠${NC} performance_metrics 저장 (선택사항)"
fi

echo ""
echo -e "  통과: ${GREEN}$PASSED_TESTS${NC}/$TOTAL_TESTS"
echo ""

if [ "$PASSED_TESTS" -ge 2 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ PostgreSQL 통합 테스트 성공!${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ PostgreSQL 통합 테스트 실패${NC}"
    echo -e "${RED}========================================${NC}"

    echo ""
    echo -e "${YELLOW}트러블슈팅:${NC}"
    echo "  1. Router Agent 로그 확인:"
    echo "     kubectl logs -f deployment/router-agent -n $NAMESPACE | grep DB"
    echo ""
    echo "  2. PostgreSQL 로그 확인:"
    echo "     kubectl logs -f $POSTGRES_POD -n $NAMESPACE"
    echo ""
    echo "  3. DB 연결 테스트:"
    echo "     kubectl exec -it $POSTGRES_POD -n $NAMESPACE -- psql -U agent_user -d agent_system"
    echo ""

    exit 1
fi
