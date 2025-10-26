"""
Prometheus 메트릭 정의 및 수집 (SDB Agent - Flask용)
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time
from functools import wraps
import logging

logger = logging.getLogger(__name__)


# 커스텀 메트릭 정의
sdb_processing_duration_seconds = Histogram(
    'sdb_processing_duration_seconds',
    'Time spent processing SDB requests',
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

sdb_bitbucket_api_calls_total = Counter(
    'sdb_bitbucket_api_calls_total',
    'Total Bitbucket API calls',
    ['api_type', 'status']  # api_type: get_file, create_branch, create_pr 등
)

sdb_llm_requests_total = Counter(
    'sdb_llm_requests_total',
    'Total LLM requests',
    ['model', 'status']
)

sdb_llm_tokens_used_total = Counter(
    'sdb_llm_tokens_used_total',
    'Total LLM tokens used',
    ['model', 'token_type']  # token_type: prompt, completion
)

sdb_pr_created_total = Counter(
    'sdb_pr_created_total',
    'Total PRs created',
    ['status']  # success, failed
)

sdb_files_modified_total = Counter(
    'sdb_files_modified_total',
    'Total files modified'
)

sdb_errors_total = Counter(
    'sdb_errors_total',
    'Total errors',
    ['error_type', 'component']
)

sdb_active_tasks = Gauge(
    'sdb_active_tasks',
    'Number of tasks currently being processed'
)


def track_processing_time(func):
    """처리 시간 추적 데코레이터 (Flask용)"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        sdb_active_tasks.inc()
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start_time
            sdb_processing_duration_seconds.observe(duration)
            sdb_active_tasks.dec()
            logger.debug(f"Processing completed in {duration:.2f}s")

    return wrapper


def track_bitbucket_call(api_type: str):
    """Bitbucket API 호출 추적 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            status = 'success'

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = 'error'
                sdb_errors_total.labels(
                    error_type=type(e).__name__,
                    component='bitbucket_api'
                ).inc()
                raise
            finally:
                sdb_bitbucket_api_calls_total.labels(
                    api_type=api_type,
                    status=status
                ).inc()
                logger.debug(f"Bitbucket API call: {api_type} - {status}")

        return wrapper
    return decorator


def track_llm_call(model: str):
    """LLM 호출 추적 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            status = 'success'

            try:
                result = func(*args, **kwargs)

                # 토큰 사용량 기록
                if isinstance(result, dict) and 'usage' in result:
                    usage = result['usage']
                    sdb_llm_tokens_used_total.labels(
                        model=model,
                        token_type='prompt'
                    ).inc(usage.get('prompt_tokens', 0))

                    sdb_llm_tokens_used_total.labels(
                        model=model,
                        token_type='completion'
                    ).inc(usage.get('completion_tokens', 0))

                return result
            except Exception as e:
                status = 'error'
                sdb_errors_total.labels(
                    error_type=type(e).__name__,
                    component='llm'
                ).inc()
                raise
            finally:
                sdb_llm_requests_total.labels(
                    model=model,
                    status=status
                ).inc()
                logger.debug(f"LLM call: {model} - {status}")

        return wrapper
    return decorator


def get_metrics():
    """메트릭 데이터를 Prometheus 형식으로 반환"""
    return generate_latest(), CONTENT_TYPE_LATEST

