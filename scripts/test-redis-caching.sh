#!/bin/bash
# Redis 캐싱 완전 테스트 스크립트

set -e

NAMESPACE="${NAMESPACE:-agent-system}"

echo "========================================"
echo "Redis 캐싱 완전 테스트"
echo "========================================"
echo ""

# 1. Redis 기본 상태 확인
echo "📌 1단계: Redis 기본 상태 확인"
echo "----------------------------------------"

REDIS_POD=$(kubectl get pod -n $NAMESPACE -l app=redis -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -z "$REDIS_POD" ]; then
    echo "❌ Redis Pod를 찾을 수 없습니다."
    exit 1
fi

echo "✅ Redis Pod: $REDIS_POD"

# PING 테스트
PONG=$(kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli PING 2>/dev/null)
if [ "$PONG" == "PONG" ]; then
    echo "✅ Redis 연결 성공"
else
    echo "❌ Redis 연결 실패"
    exit 1
fi

# 현재 캐시 상태
echo ""
echo "현재 캐시 상태:"
kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli DBSIZE
echo ""

# 2. Port Forward 설정
echo "📌 2단계: Port Forward 설정"
echo "----------------------------------------"

# 기존 Port Forward 종료
pkill -f "port-forward.*router-agent" 2>/dev/null || true

# Port Forward 시작
kubectl port-forward svc/router-agent-svc 5000:5000 -n $NAMESPACE > /dev/null 2>&1 &
PF_PID=$!
echo "Port Forward 시작됨 (PID: $PF_PID)"
sleep 3

# Health Check
if curl -f http://localhost:5000/health > /dev/null 2>&1; then
    echo "✅ Router Agent 정상 동작"
else
    echo "❌ Router Agent에 연결할 수 없습니다."
    kill $PF_PID 2>/dev/null || true
    exit 1
fi
echo ""

# 3. 캐싱 테스트
echo "📌 3단계: 캐싱 동작 테스트"
echo "----------------------------------------"

# 기존 classification 캐시 삭제 (깨끗한 테스트를 위해)
echo "기존 캐시 초기화 중..."
kubectl exec -n $NAMESPACE $REDIS_POD -- sh -c 'redis-cli --scan --pattern "classification:*" | xargs redis-cli DEL' > /dev/null 2>&1 || true
echo ""

# 첫 번째 요청 (캐시 MISS 예상)
echo "🔹 첫 번째 요청 전송 (캐시 MISS 예상)..."
START1=$(date +%s%N)
curl -s -X POST http://localhost:5000/test-classification \
  -H "Content-Type: application/json" \
  -d '{
    "issue": {
      "key": "TEST-CACHE-123",
      "fields": {
        "summary": "SDB Material 추가 테스트",
        "description": "SM490A 재질을 DB에 추가해주세요",
        "issuetype": {"name": "Task"}
      }
    }
  }' | jq -r '.classification.cached // "unknown"' > /tmp/cache1.txt

END1=$(date +%s%N)
DURATION1=$(( (END1 - START1) / 1000000 ))
CACHED1=$(cat /tmp/cache1.txt)

echo "  - 소요 시간: ${DURATION1}ms"
echo "  - 캐시 사용: $CACHED1"

sleep 2

# 두 번째 요청 (캐시 HIT 예상)
echo ""
echo "🔹 두 번째 요청 전송 (캐시 HIT 예상)..."
START2=$(date +%s%N)
curl -s -X POST http://localhost:5000/test-classification \
  -H "Content-Type: application/json" \
  -d '{
    "issue": {
      "key": "TEST-CACHE-123",
      "fields": {
        "summary": "SDB Material 추가 테스트",
        "description": "SM490A 재질을 DB에 추가해주세요",
        "issuetype": {"name": "Task"}
      }
    }
  }' | jq -r '.classification.cached // "unknown"' > /tmp/cache2.txt

END2=$(date +%s%N)
DURATION2=$(( (END2 - START2) / 1000000 ))
CACHED2=$(cat /tmp/cache2.txt)

echo "  - 소요 시간: ${DURATION2}ms"
echo "  - 캐시 사용: $CACHED2"
echo ""

# 결과 분석
echo "📊 결과 분석"
echo "----------------------------------------"
echo "첫 번째 요청: ${DURATION1}ms (cached: $CACHED1)"
echo "두 번째 요청: ${DURATION2}ms (cached: $CACHED2)"

if [ "$CACHED2" == "true" ] && [ $DURATION2 -lt $DURATION1 ]; then
    IMPROVEMENT=$(( (DURATION1 - DURATION2) * 100 / DURATION1 ))
    echo ""
    echo "✅ 캐싱 성공!"
    echo "   - 속도 개선: ${IMPROVEMENT}% 향상"
else
    echo ""
    echo "⚠️  캐싱이 예상대로 동작하지 않았습니다."
    echo "   Router Agent 로그를 확인하세요:"
    echo "   kubectl logs deployment/router-agent -n $NAMESPACE | grep -i cache"
fi
echo ""

# 4. Redis 캐시 내용 확인
echo "📌 4단계: Redis 캐시 내용 확인"
echo "----------------------------------------"
kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli --scan --pattern "classification:*"
echo ""

echo "캐시 통계:"
kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli INFO stats | grep -E "keyspace_hits|keyspace_misses"
echo ""

# Port Forward 종료
echo "Port Forward 종료 중..."
kill $PF_PID 2>/dev/null || true

echo ""
echo "========================================"
echo "테스트 완료!"
echo "========================================"
