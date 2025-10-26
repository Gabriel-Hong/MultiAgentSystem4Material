"""
Prometheus 메트릭 정의 및 수집 (Router Agent)
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
from fastapi.responses import Response
import time
from functools import wraps
import logging

logger = logging.getLogger(__name__)


# 메트릭 정의
router_requests_total = Counter(
    'router_requests_total',
    'Total number of requests received by router',
    ['method', 'endpoint', 'status']
)

router_classification_duration_seconds = Histogram(
    'router_classification_duration_seconds',
    'Time spent on intent classification',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

router_agent_calls_total = Counter(
    'router_agent_calls_total',
    'Total number of agent calls',
    ['agent', 'status']
)

router_agent_call_duration_seconds = Histogram(
    'router_agent_call_duration_seconds',
    'Time spent calling agents',
    ['agent'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

router_errors_total = Counter(
    'router_errors_total',
    'Total number of errors',
    ['error_type', 'agent']
)

router_active_requests = Gauge(
    'router_active_requests',
    'Number of requests currently being processed'
)

router_classification_confidence = Histogram(
    'router_classification_confidence',
    'Confidence score of intent classification',
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)


def track_request_metrics(endpoint: str):
    """요청 메트릭 추적 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            router_active_requests.inc()
            start_time = time.time()
            status = 'success'

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'error'
                router_errors_total.labels(
                    error_type=type(e).__name__,
                    agent='router'
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                router_active_requests.dec()
                router_requests_total.labels(
                    method='POST',
                    endpoint=endpoint,
                    status=status
                ).inc()
                logger.debug(f"Request to {endpoint} completed in {duration:.2f}s with status {status}")

        return wrapper
    return decorator


def track_classification(func):
    """분류 메트릭 추적 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = func(*args, **kwargs)

            # 분류 소요 시간 기록
            duration = time.time() - start_time
            router_classification_duration_seconds.observe(duration)

            # 신뢰도 기록
            if isinstance(result, dict) and 'confidence' in result:
                confidence = result['confidence']
                router_classification_confidence.observe(confidence)
                logger.debug(f"Classification completed in {duration:.2f}s with confidence {confidence:.2f}")

            return result
        except Exception as e:
            router_errors_total.labels(
                error_type=type(e).__name__,
                agent='classification'
            ).inc()
            raise

    return wrapper


def track_agent_call(agent_name: str):
    """Agent 호출 메트릭 추적 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 'success'

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'error'
                router_errors_total.labels(
                    error_type=type(e).__name__,
                    agent=agent_name
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                router_agent_call_duration_seconds.labels(
                    agent=agent_name
                ).observe(duration)
                router_agent_calls_total.labels(
                    agent=agent_name,
                    status=status
                ).inc()
                logger.debug(f"Agent {agent_name} call completed in {duration:.2f}s with status {status}")

        return wrapper
    return decorator


def get_metrics_response():
    """메트릭 엔드포인트 응답 생성"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

