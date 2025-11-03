#!/bin/bash
# Redis 캐시 수동 삭제 도구

set -e

NAMESPACE="${NAMESPACE:-agent-system}"

echo "Redis 캐시 관리 도구"
echo "===================="
echo ""
echo "1. 전체 캐시 삭제"
echo "2. Intent Classification 캐시 삭제"
echo "3. Bitbucket API 캐시 삭제"
echo "4. LLM 응답 캐시 삭제"
echo "5. Agent 헬스체크 캐시 삭제"
echo "6. 특정 패턴 삭제"
echo "7. 캐시 통계 조회"
echo ""
read -p "선택 (1-7): " choice

REDIS_POD=$(kubectl get pod -n $NAMESPACE -l app=redis -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$REDIS_POD" ]; then
    echo "❌ Redis Pod를 찾을 수 없습니다. Namespace를 확인하세요: $NAMESPACE"
    exit 1
fi

echo "Redis Pod: $REDIS_POD"
echo ""

case $choice in
  1)
    echo "전체 캐시를 삭제합니다..."
    kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli FLUSHDB
    echo "✅ 완료"
    ;;
  2)
    echo "Intent Classification 캐시를 삭제합니다..."
    COUNT=$(kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli --scan --pattern "classification:*" | wc -l)
    if [ "$COUNT" -gt 0 ]; then
        kubectl exec -n $NAMESPACE $REDIS_POD -- sh -c 'redis-cli --scan --pattern "classification:*" | xargs redis-cli DEL'
        echo "✅ 완료 ($COUNT개 키 삭제)"
    else
        echo "삭제할 캐시가 없습니다."
    fi
    ;;
  3)
    echo "Bitbucket API 캐시를 삭제합니다..."
    COUNT=$(kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli --scan --pattern "bitbucket:*" | wc -l)
    if [ "$COUNT" -gt 0 ]; then
        kubectl exec -n $NAMESPACE $REDIS_POD -- sh -c 'redis-cli --scan --pattern "bitbucket:*" | xargs redis-cli DEL'
        echo "✅ 완료 ($COUNT개 키 삭제)"
    else
        echo "삭제할 캐시가 없습니다."
    fi
    ;;
  4)
    echo "LLM 응답 캐시를 삭제합니다..."
    COUNT=$(kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli --scan --pattern "llm:*" | wc -l)
    if [ "$COUNT" -gt 0 ]; then
        kubectl exec -n $NAMESPACE $REDIS_POD -- sh -c 'redis-cli --scan --pattern "llm:*" | xargs redis-cli DEL'
        echo "✅ 완료 ($COUNT개 키 삭제)"
    else
        echo "삭제할 캐시가 없습니다."
    fi
    ;;
  5)
    echo "Agent 헬스체크 캐시를 삭제합니다..."
    COUNT=$(kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli --scan --pattern "agent:health:*" | wc -l)
    if [ "$COUNT" -gt 0 ]; then
        kubectl exec -n $NAMESPACE $REDIS_POD -- sh -c 'redis-cli --scan --pattern "agent:health:*" | xargs redis-cli DEL'
        echo "✅ 완료 ($COUNT개 키 삭제)"
    else
        echo "삭제할 캐시가 없습니다."
    fi
    ;;
  6)
    read -p "패턴 입력 (예: classification:*): " pattern
    echo "$pattern 패턴의 캐시를 삭제합니다..."
    COUNT=$(kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli --scan --pattern "$pattern" | wc -l)
    if [ "$COUNT" -gt 0 ]; then
        kubectl exec -n $NAMESPACE $REDIS_POD -- sh -c "redis-cli --scan --pattern \"$pattern\" | xargs redis-cli DEL"
        echo "✅ 완료 ($COUNT개 키 삭제)"
    else
        echo "삭제할 캐시가 없습니다."
    fi
    ;;
  7)
    echo "=== 캐시 통계 ==="
    echo ""
    echo "캐시 히트/미스:"
    kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli INFO stats | grep -E "keyspace_hits|keyspace_misses"
    echo ""
    echo "메모리 사용량:"
    kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli INFO memory | grep -E "used_memory_human|maxmemory_human"
    echo ""
    echo "키 개수:"
    kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli DBSIZE
    echo ""
    echo "연결된 클라이언트:"
    kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli INFO clients | grep connected_clients
    echo ""
    echo "=== 캐시 키 샘플 (최대 10개) ==="
    kubectl exec -n $NAMESPACE $REDIS_POD -- redis-cli --scan --count 10
    ;;
  *)
    echo "잘못된 선택입니다."
    exit 1
    ;;
esac
