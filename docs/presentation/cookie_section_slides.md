# 🍪 쿠키 섹션: Tech Behind the Magic

## 발표 슬라이드 18~ (기술 비하인드)

> **목적:** AI를 실무에 적용하면서 배운 교훈 공유  
> **대상:** 개발자, AI 코딩 도구 사용자  
> **예상 시간:** 7~10분

---

## 슬라이드 구성 Overview

| 슬라이드 | 제목 | 내용 |
|----------|------|------|
| 18 | 쿠키 인트로 | 4가지 교훈 소개 |
| 19 | 교훈 01 - 문제 | 17,000줄을 AI에게 어떻게? |
| 20 | 교훈 01 - 해결 | Clang AST 압축 |
| 21-1 | 교훈 01 - 라인번호 (문제) | LLM이 수정 위치를 못 찾음 |
| 21-2 | 교훈 01 - 라인번호 (해결) | 라인 번호 Prefix 추가 |
| 21-3 | 교훈 01 - 라인번호 (결과) | 정확도 70% → 95% |
| 22 | 교훈 02 - 문제 | JSON 파싱 실패 |
| 23 | 교훈 02 - 해결 | 다단계 후처리 파이프라인 |
| 24 | 교훈 02 - 레거시 (문제) | 인코딩/줄바꿈 깨짐 |
| 25 | 교훈 02 - 레거시 (해결) | 원본 그대로 보존 |
| 26 | 교훈 03 - 문제 | 잘못된 코드가 올라가면? |
| 27 | 교훈 03 - 해결 | 3-Layer Validation |
| 28 | 교훈 03 - 결과 | Zero Incidents |
| 29 | 교훈 04 - 문제 | LLM API 비용 폭발 |
| 30 | 교훈 04 - 해결 | Smart Caching |
| 31 | 교훈 04 - 결과 | 60% 비용 절감 |
| 32 | Key Takeaways | 4가지 원칙 정리 |

---

# Slide 18: 쿠키 인트로

## 🍪 Tech Behind the Magic

# AI를 실무에 적용하면서 배운 것들

> "AI를 '사용'하는 것과 '잘 활용'하는 것은 다릅니다"

---

### 4가지 교훈

| # | 교훈 | 핵심 |
|---|------|------|
| 01 | AI도 맥락이 필요하다 | 압축 + 라인번호 |
| 02 | AI의 출력은 후처리가 필수다 | 파싱 + 인코딩 |
| 03 | AI는 가드레일이 필요하다 | 3단계 검증 |
| 04 | AI는 비용 관리가 중요하다 | 캐싱 전략 |

---

# Slide 19: 교훈 01 - 문제 제기

## 01. AI도 맥락이 필요하다

# 17,000줄을 AI에게 어떻게 줄까요?

---

### The Problem

```
MatlDB.cpp: 17,000 lines
DBLib.cpp: 15,000 lines
DgnDataCtrl.cpp: 12,000 lines
─────────────────────────
Total: 44,000+ lines
```

**GPT-4 Context Window: ~128K tokens**

→ 전체 파일을 넣으면?

| Issue | Impact |
|-------|--------|
| ❌ 토큰 한도 초과 | API 에러 |
| ❌ 비용 폭발 | ~$1-2/건 |
| ❌ 정확도 급락 | 70% 이하 |

---

# Slide 20: 교훈 01 - 해결

## 01. AI도 맥락이 필요하다

# Solution: 구조만 추출하기

---

### Clang AST Compression

```
Before                          After
─────────────────────────────────────────────────
17,000 lines                    500 lines
Full implementation      →      Structure only
~50K tokens                     ~11K tokens
```

### How it works

```cpp
// Before: 전체 코드
void GetSteelList_SS400() {
    SteelData data;
    data.name = "SS400";
    data.fy = 235;
    // ... 200 lines of implementation
}

// After: 구조만
void GetSteelList_SS400();  // signature only
```

---

### Result

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Lines | 17,000 | 500 | **97% 압축** |
| Tokens | ~50K | ~11K | **78% 절감** |
| Cost | ~$1.00 | $0.11 | **89% 절감** |

---

# Slide 21-1: 교훈 01 - 라인번호 (문제)

## 01. AI도 맥락이 필요하다

# 문제: LLM이 수정 위치를 찾지 못한다

---

### The Problem

```json
LLM 응답:
{
    "line_start": 10730,  ← 실제로는 10731이어야 함
    "line_end": 10732,    ← 부정확한 위치
    "new_content": "..."
}
```

### 결과

| Issue | Impact |
|-------|--------|
| ❌ diff 적용 시 엉뚱한 위치에 수정 | 코드 손상 |
| ❌ 컴파일 에러 발생 | 빌드 실패 |
| ❌ 수동으로 다시 수정해야 함 | 시간 낭비 |

### 초기 정확도: 70%

---

# Slide 21-2: 교훈 01 - 라인번호 (해결)

## 01. AI도 맥락이 필요하다

# Solution: 라인 번호 Prefix 추가

---

### Implementation

`llm_handler.py:51-61`

```python
def format_code_with_line_numbers(self, content: str, start_line: int = 1) -> str:
    """코드에 라인 번호 추가"""
    lines = content.splitlines()
    numbered_lines = []
    for i, line in enumerate(lines, start=start_line):
        # 6자리 우측 정렬 (최대 999,999 라인 지원)
        numbered_lines.append(f"{i:6d}|{line}")
    return '\n'.join(numbered_lines)
```

---

### Before: 라인 번호 없음

```cpp
        is_SP16_2017_tB1,
        is_SP16_2017_tB2,
        is_AlloySt_Max
};
```

> LLM: "이게 몇 번째 줄이지...? 🤔"

---

### After: 라인 번호 포함

```cpp
 10730|        is_SP16_2017_tB1,
 10731|        is_SP16_2017_tB2,
 10732|        is_AlloySt_Max
 10733|};
```

> LLM: "10731번 줄을 수정하면 되겠군! ✅"

---

# Slide 21-3: 교훈 01 - 라인번호 (결과)

## 01. AI도 맥락이 필요하다

# Result: 정확도 70% → 95%

---

### Before vs After

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| 수정 위치 정확도 | 70% | **95%** | +25% |
| diff 적용 실패 | 빈번 | 거의 없음 | - |
| 수동 수정 필요 | 30% | **5%** | -25% |

---

### 💡 Takeaway

> LLM에게 코드 수정을 요청할 때는
> 
> **라인 번호를 명시적으로 보여주세요.**
> 
> 간단한 포맷팅 하나로 정확도가 **25% 향상**됩니다.

---

# Slide 22: 교훈 02 - 문제 제기

## 02. AI의 출력은 후처리가 필수다

# AI가 준 JSON이 파싱이 안 됩니다

---

### Real Response from GPT-4

```json
{
    "changes": [
        {"line": 10732, "content": "new code"},
        {"line": 10733, "content": "more code"},  ← trailing comma!
    ]
}
```

```
json.loads() → JSONDecodeError 💥
```

---

### More Issues

| Issue | Example |
|-------|---------|
| Trailing comma | `[{...}, ]` |
| Control characters | `"code with	tab"` |
| Markdown wrapping | ` ```json ... ``` ` |

### Initial Success Rate: 75%

---

# Slide 23: 교훈 02 - 해결

## 02. AI의 출력은 후처리가 필수다

# Solution: 다단계 후처리 파이프라인

---

### Implementation

```python
def parse_llm_response(response: str) -> dict:
    
    # Step 1: Extract from markdown
    if "```json" in response:
        response = extract_from_markdown(response)
    
    # Step 2: Remove trailing commas
    response = re.sub(r',(\s*[}\]])', r'\1', response)
    
    # Step 3: Escape control characters
    response = escape_control_chars(response)
    
    # Step 4: Parse
    return json.loads(response)
```

---

### Result

```
Success Rate: 75% → 98%
             ████████████████████░░ +23%
```

---

### 💡 Takeaway

> AI의 출력을 그대로 쓰지 마세요.
> 
> 항상 **검증하고 정제**하세요.

---

# Slide 24: 교훈 02 - 레거시 코드 (문제)

## 02. AI의 출력은 후처리가 필수다

# 20년 된 코드의 인코딩을 지켜라

---

### The Problem

```
Git Diff:
- 실제 수정: 3줄
- 표시된 변경: 17,000줄 전체 😱
```

### Why?

```python
# 문제의 코드
content = response.text  # Python이 UTF-8로 자동 변환
                         # 원본 EUC-KR 인코딩 손실!
```

---

### Also: Line Ending 문제

```python
# CRLF → LF 강제 변환
'\n'.join(lines)  # Windows 파일의 CRLF가 LF로 변경
```

→ Git diff에서 모든 라인이 변경된 것으로 표시

---

# Slide 25: 교훈 02 - 레거시 코드 (해결)

## 02. AI의 출력은 후처리가 필수다

# Solution: 원본 그대로 보존

---

### 인코딩 보존

```python
import chardet

# 1. 바이너리로 읽기
raw = response.content  # .text ❌ → .content ✅

# 2. 원본 인코딩 감지
detected = chardet.detect(raw)
encoding = detected['encoding']  # 'EUC-KR'

# 3. 수정 작업
text = raw.decode(encoding)
modified = modify_code(text)

# 4. 원본 인코딩으로 저장
result = modified.encode(encoding)
```

---

### 줄바꿈 보존

```python
# CRLF vs LF 자동 감지 & 보존
line_ending = '\r\n' if '\r\n' in content else '\n'
result = line_ending.join(lines)
```

---

### Result

| Issue | Before | After |
|-------|--------|-------|
| 한글 주석 | 깨짐 | **100% 보존** |
| Git diff | 전체 변경 | **실제 수정만** |
| 줄바꿈 | LF로 강제 변환 | **원본 유지** |

---

### 💡 Takeaway

> 레거시 코드를 다룰 때는
> 
> **바이너리 모드**로 읽고, **원본 인코딩**을 보존하세요.

---

# Slide 26: 교훈 03 - 문제 제기

## 03. AI는 가드레일이 필요하다

# "자동화했는데 잘못된 코드가 올라가면요?"

---

### Real Risks

| Risk | Example |
|------|---------|
| 🎭 Hallucination | 존재하지 않는 함수 호출 |
| 🚫 Out of Scope | "버그 수정해줘" 요청도 처리 시도 |
| ⏰ Infinite Loop | 응답 없이 무한 대기 |

---

### Without Guardrails

```
User Request: "아무거나 수정해줘"
     ↓
LLM: "네, 알겠습니다!" (confidence: 0.3)
     ↓
Wrong Code Generated
     ↓
PR Created 💥
     ↓
Production Bug 😱
```

---

# Slide 27: 교훈 03 - 해결

## 03. AI는 가드레일이 필요하다

# Solution: 3-Layer Validation

---

### Architecture

```
┌─────────────────────────────────────┐
│         Layer 1: Confidence         │
│                                     │
│    "Material DB 추가"  → 0.95 ✅    │
│    "버그 수정해줘"     → 0.30 ❌    │
│                                     │
│         Threshold: ≥ 0.9            │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│        Layer 2: Health Check        │
│                                     │
│    GET /health → 200 OK? ✅         │
│    Agent 살아있는지 확인             │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│        Layer 3: Timeout Guard       │
│                                     │
│    Max: 300 seconds                 │
│    초과 시 자동 중단                 │
└──────────────┬──────────────────────┘
               ▼
           ✅ PASS
```

---

# Slide 28: 교훈 03 - 결과

## 03. AI는 가드레일이 필요하다

# Result: Zero Incidents

---

### Validation Results

| Request | Confidence | Result |
|---------|------------|--------|
| "Material DB 추가해주세요" | 0.95 | ✅ PASS |
| "Steel 강종 SS400 추가" | 0.92 | ✅ PASS |
| "버그 수정해줘" | 0.30 | ❌ BLOCK |
| "코드 리팩토링 해줘" | 0.25 | ❌ BLOCK |

---

### Stats

| Metric | Value |
|--------|-------|
| Pass Rate | **98%** |
| False Positives | **0** |
| Wrong Commits | **0** |

---

### 💡 Takeaway

> 자동화할수록 **안전장치**가 중요합니다.
> 
> "신뢰하되, 검증하라" (Trust but Verify)

---

# Slide 29: 교훈 04 - 문제 제기

## 04. AI는 비용 관리가 중요하다

# LLM API 비용이 예상보다 많이 나옵니다

---

### The Problem

```
동일한 요청이 반복됨:
├── "Material DB 추가" → LLM 호출 → $0.11
├── "Material DB 추가" → LLM 호출 → $0.11  (같은 요청!)
├── "Material DB 추가" → LLM 호출 → $0.11  (또 같은 요청!)
└── ...
```

### Also

| Issue | Impact |
|-------|--------|
| Bitbucket API Rate Limit | 요청 차단 |
| 같은 파일 반복 조회 | 불필요한 지연 |
| 응답 시간 지연 | 사용자 경험 저하 |

---

# Slide 30: 교훈 04 - 해결

## 04. AI는 비용 관리가 중요하다

# Solution: Smart Caching Strategy

---

### Cache Strategy

```python
CACHE_STRATEGY = {
    
    # Intent Classification: 24시간
    # "Material DB 추가" 같은 요청 유형은 하루 동안 캐시
    'classification': timedelta(hours=24),
    
    # Bitbucket API: 5분
    # 파일 목록, 브랜치 정보 등
    'bitbucket': timedelta(minutes=5),
    
    # LLM Response: 24시간
    # 동일 입력에 대한 코드 생성 결과
    'llm_response': timedelta(hours=24),
}
```

---

### Cache Flow

```
Request: "Material DB 추가"
    │
    ▼
┌─────────────────┐
│  Cache Check    │
│                 │
│  Hit? ─────────────→ Return cached (0.01s)
│    │            │
│   Miss          │
│    │            │
└────┼────────────┘
     ▼
┌─────────────────┐
│  LLM API Call   │──→ Save to cache
│  (38 seconds)   │
└─────────────────┘
```

---

# Slide 31: 교훈 04 - 결과

## 04. AI는 비용 관리가 중요하다

# Result: 60% Cost Reduction

---

### Before vs After

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| API Cost | 100% | 40% | **-60%** |
| Response Time | 38s | 15s (avg) | **-60%** |
| Cache Hit Rate | - | **70%** | - |

---

### Monthly Cost

```
Before:  $375/month
After:   $150/month
         ─────────────
Savings: $225/month (60%)
```

---

### 💡 Takeaway

> 캐싱은 **비용**과 **성능**, 두 마리 토끼를 잡습니다.
> 
> LLM API를 쓴다면 캐싱은 필수입니다.

---

# Slide 32: Key Takeaways

## 🍪 What We Learned

# AI를 잘 활용하기 위한 4가지 원칙

---

### Summary

| # | Principle | Implementation | Result |
|---|-----------|----------------|--------|
| 01 | **맥락을 줘라** | AST 압축 + 라인번호 | 97% 압축, 95% 정확도 |
| 02 | **출력을 정제하라** | 후처리 파이프라인 | 98% 파싱 성공 |
| 03 | **가드레일을 세워라** | 3-Layer Validation | 0 incidents |
| 04 | **비용을 관리하라** | Smart Caching | 60% 비용 절감 |

---

### One More Thing...

> 이 모든 것은 **"잘 동작하는 자동화"**를 위한 것입니다.
> 
> AI는 도구입니다.
> 
> **잘 다루는 방법**을 알아야 합니다.

---

# 부록: 트러블슈팅 Tier 분류

## 발표 항목 선정 기준

### Tier 1: 필수 (발표에 포함)

| # | 카테고리 | 문제 | 해결 | 효과 |
|---|----------|------|------|------|
| 1 | 대용량 파일 처리 | 17,000줄 토큰 초과 | Clang AST 압축 | **97% 압축** |
| 2 | 라인번호 포맷팅 | 수정 위치 부정확 | 라인 번호 Prefix | **정확도 +25%** |
| 3 | 인코딩 보존 | EUC-KR → UTF-8 변환 | chardet 감지 | **100% 보존** |
| 4 | 안전한 자동화 | LLM 환각 위험 | 3-Layer Guardrails | **0 incidents** |
| 5 | 비용 최적화 | API 비용 폭발 | Redis 캐싱 | **60% 절감** |

### Tier 2: 권장 (시간 여유 시)

| # | 카테고리 | 문제 | 해결 | 효과 |
|---|----------|------|------|------|
| 6 | LLM 응답 파싱 | JSON 파싱 실패 | 다단계 후처리 | **75% → 98%** |
| 7 | 줄바꿈 보존 | CRLF → LF 변환 | 자동 감지 & 유지 | **Git diff 정확** |
| 8 | 들여쓰기 보존 | 탭 → 스페이스 변환 | 프롬프트 가이드 | **스타일 유지** |
| 9 | 템플릿 패턴 | 코드 스타일 불일치 | Few-shot 예시 | **일관성 확보** |

### Tier 3: 선택 (Q&A 대비)

| # | 카테고리 | 문제 | 해결 | 비고 |
|---|----------|------|------|------|
| 10 | 매크로 처리 | #define 파싱 불가 | #pragma region 추출 | 기술적 |
| 11 | K8s Secret | 401 에러 | 토큰 타입 구분 | 인프라 |
| 12 | Redis 설정 | Connection refused | protected-mode 설정 | 인프라 |

---

## Q&A 대비

### 예상 질문 및 답변

**Q1: "다른 업무에도 적용할 수 있나요?"**

> 네, 패턴이 있는 모든 반복 업무에 적용 가능합니다.
> - Phase 2: Section DB Agent (예정)
> - Phase 3: MQC Assistant Agent (예정)

**Q2: "비용은 얼마나 드나요?"**

> 월 약 $150 정도입니다.
> - 건당 LLM 비용: $0.11
> - 캐싱으로 60% 비용 절감

**Q3: "LLM이 잘못된 코드를 생성하면?"**

> Guardrails 3단계 검증으로 방지합니다.
> - 신뢰도 0.9 미만 자동 거부
> - 결과: 잘못된 처리 **0건**

**Q4: "기존 코드 스타일이 유지되나요?"**

> 네, 여러 기법으로 원본 스타일을 유지합니다.
> - 인코딩 보존 (EUC-KR)
> - 줄바꿈 보존 (CRLF/LF)
> - 라인번호로 정확한 위치 수정

---

## 참고 자료

### 관련 구현 파일

| 파일 | 위치 | 역할 |
|------|------|------|
| `llm_handler.py` | sdb-agent/app/ | 라인번호 포맷팅, diff 적용, JSON 파싱 |
| `encoding_handler.py` | sdb-agent/app/ | 인코딩 감지 및 보존 |
| `prompt_builder.py` | sdb-agent/app/ | 프롬프트 생성 |
| `code_chunker.py` | sdb-agent/app/ | AST 압축, 함수 분할 |

### 관련 문서

| 문서 | 내용 |
|------|------|
| `LARGE_FILE_STRATEGY.md` | 대용량 파일 처리 전략 |
| `ENCODING_FIX_GUIDE.md` | 인코딩 문제 해결 |
| `LINE_ENDING_FIX.md` | 줄바꿈 보존 |

---

*Last Updated: 2025-12*
