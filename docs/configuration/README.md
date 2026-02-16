# Configuration 문서

Multi-Agent 시스템의 설정 및 환경 변수 관리에 관한 문서 모음입니다.

## 📚 문서 목록

### [환경 변수 동작 흐름](./ENVIRONMENT_VARIABLES_FLOW.md)
환경 변수가 로컬 개발 환경과 Kubernetes 환경에서 어떻게 로드되고 사용되는지에 대한 전체 흐름을 상세히 설명합니다.

**주요 내용:**
- 로컬 개발 환경에서 .env 파일 사용
- Kubernetes 환경에서 Secret/ConfigMap 주입
- Pydantic Settings 자동 매핑
- 환경 변수 우선순위
- 테스트 방법 및 문제 해결

---

## 🎯 빠른 시작

### 로컬 개발 환경 설정

```bash
# 1. agent 디렉토리에 .env 파일 생성
cd sdb-agent  # 또는 router-agent
cat > .env << EOF
OPENAI_API_KEY=sk-your-key
REDIS_HOST=localhost
DB_HOST=localhost
EOF

# 2. 실행
python app/main.py
```

### Kubernetes 환경 설정

```bash
# 1. 프로젝트 루트에 .env 파일 생성
cd /path/to/project
cat > .env << EOF
OPENAI_API_KEY=sk-your-key
BITBUCKET_ACCESS_TOKEN=ATCTT-your-token
BITBUCKET_USERNAME=your-email@example.com
EOF

# 2. Secret 생성
./scripts/create-secrets-from-env.sh

# 3. Helm 배포
helm install multi-agent-system ./helm/multi-agent-system -n agent-system
```

---

## 📊 설정 파일 구조

```
Multi-Agent System
├── router-agent/
│   ├── .env                      # 로컬 개발용 (gitignore)
│   └── app/
│       └── config.py             # Pydantic Settings 정의
├── sdb-agent/
│   ├── .env                      # 로컬 개발용 (gitignore)
│   └── app/
│       └── config.py             # Pydantic Settings 정의
├── helm/multi-agent-system/
│   ├── values.yaml               # Helm Chart 설정
│   └── templates/
│       ├── configmap.yaml        # 공통 설정 (비밀 아님)
│       ├── router-agent/
│       │   └── deployment.yaml   # 환경변수 주입
│       └── sdb-agent/
│           └── deployment.yaml   # 환경변수 주입
├── scripts/
│   └── create-secrets-from-env.sh # Secret 생성 스크립트
└── .env                          # Kubernetes Secret 생성용 (gitignore)
```

---

## 🔑 환경 변수 카테고리

### 1. 민감한 정보 (Secret)
- `OPENAI_API_KEY`: OpenAI API 키
- `BITBUCKET_ACCESS_TOKEN`: Bitbucket 액세스 토큰
- `BITBUCKET_USERNAME`: Bitbucket 사용자명
- `DB_PASSWORD`: PostgreSQL 비밀번호

### 2. 공통 설정 (ConfigMap)
- `OPENAI_MODEL`: 사용할 OpenAI 모델
- `LOG_LEVEL`: 로깅 레벨
- `BITBUCKET_URL`: Bitbucket API URL
- `BITBUCKET_WORKSPACE`: Bitbucket 워크스페이스
- `BITBUCKET_REPOSITORY`: Bitbucket 저장소

### 3. 인프라 설정 (values.yaml)
- `REDIS_HOST`, `REDIS_PORT`: Redis 연결 정보
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`: PostgreSQL 연결 정보

---

## 🔄 환경별 설정 전략

| 환경 | 설정 방법 | 주요 파일 |
|------|---------|---------|
| **로컬 개발** | .env 파일 | `agent/.env` |
| **Kubernetes** | Secret + ConfigMap + values.yaml | `helm/` |
| **CI/CD** | 환경 변수 또는 Secret | Pipeline 설정 |

---

## ⚠️ 주의사항

1. **절대 커밋하지 말 것:**
   - `.env` 파일
   - API 키, 토큰 등 민감한 정보

   ```bash
   # .gitignore에 추가되어 있는지 확인
   cat .gitignore | grep .env
   ```

2. **환경 변수 우선순위:**
   ```
   OS 환경 변수 > .env 파일 > config.py 기본값
   ```

3. **대소문자 무시:**
   - `REDIS_HOST`, `redis_host`, `Redis_Host` 모두 동일하게 처리됨
   - `case_sensitive = False` 설정 덕분

---

## 🔗 관련 문서

- [Kubernetes Secret 자동화](../kubernetes/KUBERNETES_SECRET_AUTOMATION.md)
- [Redis 설정 관리](../redis/CONFIGURATION_MANAGEMENT.md)
- [배포 워크플로우](../redis/DEPLOYMENT_WORKFLOW.md)
- [Minikube 배포 가이드](../kubernetes/MINIKUBE_DEPLOYMENT.md)

---

## 💡 팁

### 환경 변수 확인

```bash
# 로컬에서
python3 << EOF
from router_agent.app.config import get_settings
settings = get_settings()
print(f"Redis: {settings.redis_host}:{settings.redis_port}")
EOF

# Kubernetes에서
kubectl exec -n agent-system deployment/router-agent -- env | grep REDIS
```

### Secret 값 확인

```bash
# Secret의 키 목록
kubectl get secret agent-secrets -n agent-system -o jsonpath='{.data}' | jq -r 'keys[]'

# 특정 값 디코딩 (주의: 민감한 정보!)
kubectl get secret agent-secrets -n agent-system -o jsonpath='{.data.openai-api-key}' | base64 -d
```

---

## 📝 문서 작성 규칙

이 디렉토리에 새로운 문서를 추가할 때:

1. **명확한 제목**: 문서 내용을 정확히 반영
2. **목차 포함**: 긴 문서의 경우 필수
3. **예시 코드**: 실제 사용 가능한 코드 제공
4. **흐름도/다이어그램**: 복잡한 개념은 시각화
5. **관련 문서 링크**: 다른 문서와 연결

---

**마지막 업데이트:** 2025-01-XX
**작성자:** Claude Code
