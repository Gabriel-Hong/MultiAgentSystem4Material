#!/bin/bash
# Redis 캐싱 동작 테스트 스크립트

echo "=== Redis 캐싱 동작 확인 ==="
echo ""

NAMESPACE="${NAMESPACE:-agent-system}"

# 1. Redis Pod 확인
echo "1. Redis Pod 상태 확인..."
kubectl get pod -n $NAMESPACE -l app=redis

if [ $? -ne 0 ]; then
    echo "❌ Kubernetes를 사용하지 않는 것 같습니다. docker-compose 환경인가요?"
    echo ""
    echo "Docker Compose 환경이면 다음 명령어를 사용하세요:"
    echo "  docker ps | grep redis"
    exit 1
fi

REDIS_POD=$(kubectl get pod -n $NAMESPACE -l app=redis -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$REDIS_POD" ]; then
    echo "❌ Redis Pod를 찾을 수 없습니다."
    exit 1
fi

echo "✅ Redis Pod: $REDIS_POD"
echo ""

# 2. Redis 연결 테스트
echo "2. Redis 연결 테스트..."
PONG=$(kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli PING 2>/dev/null)
if [ "$PONG" == "PONG" ]; then
    echo "✅ Redis 연결 성공"
else
    echo "❌ Redis 연결 실패"
    exit 1
fi
echo ""

# 3. Router Agent 로그에서 Redis 연결 확인
echo "3. Router Agent의 Redis 연결 로그 확인..."
ROUTER_POD=$(kubectl get pod -n $NAMESPACE -l app=router-agent -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$ROUTER_POD" ]; then
    echo "Router Agent Pod: $ROUTER_POD"
    kubectl logs $ROUTER_POD -n $NAMESPACE --tail=50 | grep -i redis || echo "⚠️  Redis 관련 로그 없음"
else
    echo "⚠️  Router Agent Pod를 찾을 수 없습니다."
fi
echo ""

# 4. SDB Agent 로그에서 Redis 연결 확인
echo "4. SDB Agent의 Redis 연결 로그 확인..."
SDB_POD=$(kubectl get pod -n $NAMESPACE -l app=sdb-agent -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$SDB_POD" ]; then
    echo "SDB Agent Pod: $SDB_POD"
    kubectl logs $SDB_POD -n $NAMESPACE --tail=50 | grep -i redis || echo "⚠️  Redis 관련 로그 없음"
else
    echo "⚠️  SDB Agent Pod를 찾을 수 없습니다."
fi
echo ""

# 5. 현재 캐시 상태
echo "5. 현재 캐시 상태..."
echo "총 키 개수:"
kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli DBSIZE
echo ""
echo "캐시 키 샘플 (최대 10개):"
kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli --scan --count 10
echo ""

echo "=== 테스트 준비 완료 ==="
echo ""
echo "📌 다음 단계:"
echo "  1. 동일한 webhook을 첫 번째로 전송 (캐시 MISS 예상)"
echo "  2. 동일한 webhook을 두 번째로 전송 (캐시 HIT 예상)"
echo "  3. 로그 확인: kubectl logs -f $ROUTER_POD -n $NAMESPACE | grep 캐시"
