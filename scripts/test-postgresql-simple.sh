#!/bin/bash
# PostgreSQL 간단한 테스트 스크립트
# Router Agent로 가짜 Webhook 전송 및 DB 저장 확인

set -e

# 색상
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

NAMESPACE="agent-system"

echo "PostgreSQL 통합 테스트 (간단 버전)"
echo "======================================"
echo ""

# 1. Port-forward 시작
echo "1. Router Agent Port-forward 시작..."
kubectl port-forward -n $NAMESPACE svc/router-agent-svc 8080:5000 > /dev/null 2>&1 &
PF_PID=$!

# Port-forward 준비 대기 (최대 10초)
echo "   Port-forward 준비 중..."
for i in {1..10}; do
    if curl -s --max-time 1 http://localhost:8080/health > /dev/null 2>&1; then
        echo -e "   ${GREEN}✓ Port-forward 준비 완료${NC}"
        break
    fi
    sleep 1
done

# 2. Webhook 전송
echo "2. 테스트 Webhook 전송..."
TIMESTAMP=$(date +%s)

HTTP_CODE=$(curl -s --max-time 30 -w "%{http_code}" -o /dev/null \
  -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d "{
    \"webhookEvent\": \"jira:issue_created\",
    \"issue\": {
      \"key\": \"TEST-DB-$(date +%H%M%S)\",
      \"fields\": {
        \"summary\": \"PostgreSQL 테스트 - $TIMESTAMP\",
        \"description\": \"DB 저장 테스트\",
        \"issuetype\": {\"name\": \"Task\"}
      }
    }
  }")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "   ${GREEN}✓ HTTP $HTTP_CODE${NC}"
else
    echo -e "   ${YELLOW}⚠ HTTP $HTTP_CODE${NC}"
fi

echo -e "${GREEN}✓ Webhook 전송 완료${NC}"

# Port-forward 종료
kill $PF_PID 2>/dev/null || true

# 3. DB 확인 대기
echo "3. DB 저장 대기 중..."
sleep 3

# 4. DB 조회
echo "4. PostgreSQL 데이터 조회..."
echo ""

POSTGRES_POD=$(kubectl get pod -n $NAMESPACE -l app=postgresql -o jsonpath='{.items[0].metadata.name}')

echo "📝 최근 request_history (상위 3건):"
kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U agent_user -d agent_system -c \
  "SELECT id, issue_key, status, created_at FROM request_history ORDER BY created_at DESC LIMIT 3;"

echo ""
echo "🎯 최근 classification_history (상위 3건):"
kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U agent_user -d agent_system -c \
  "SELECT id, issue_key, classified_agent, ROUND(confidence::numeric, 2) as confidence, cached FROM classification_history ORDER BY created_at DESC LIMIT 3;"

echo ""
echo "📊 최근 performance_metrics (상위 5건):"
kubectl exec -n $NAMESPACE $POSTGRES_POD -- psql -U agent_user -d agent_system -c \
  "SELECT id, agent_name, metric_type, ROUND(metric_value::numeric, 2) as value FROM performance_metrics ORDER BY created_at DESC LIMIT 5;"

echo ""
echo -e "${GREEN}======================================"
echo "테스트 완료!"
echo -e "======================================${NC}"
