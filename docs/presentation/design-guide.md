# PPT 디자인 가이드

## 개요

시나리오가 **공감(문제) → 기대(솔루션) → 놀람(데모) → 신뢰(기술) → 흥분(로드맵)** 순서로 구성되어 있습니다. 이 스토리텔링 구조에 맞는 디자인 방향을 제안합니다.

---

## 추천 디자인 스타일: "Technical Minimalism + Hand-drawn Warmth"

### 기본 원칙

| 요소 | 권장 사항 |
|------|----------|
| **배경** | 순수 화이트 (#FFFFFF) 또는 오프화이트 (#FAFAFA) |
| **주요 텍스트** | 검정 또는 다크 그레이 (#1A1A1A) |
| **강조 색상** | MIDAS 브랜드 레드 (표지처럼) 1가지만 사용 |
| **폰트** | 제목: Pretendard Bold / 본문: Pretendard Regular |
| **여백** | 슬라이드 상하좌우 최소 10% 마진 유지 |

---

## 섹션별 디자인 제안

### 0. 표지 (현재 디자인 유지)

- 이미 깔끔하고 좋습니다
- MIDAS 로고 + 큰 타이틀 + 서브타이틀 구조 유지

---

### 1. 공감 섹션 (Slide 1-3)

**목표**: 청중이 "맞아, 나도 그래" 느끼게

| Slide | 레이아웃 제안 |
|-------|--------------|
| 1 | 왼쪽: 사업/기획 말풍선, 오른쪽: 개발자 말풍선 (Excalidraw 캐릭터 활용) |
| 2 | 코드 파일 목록을 Excalidraw 손글씨 박스로 나열, 화살표로 "반복 작업" 강조 |
| 3 | 왼쪽: 문제점 리스트, 오른쪽: "왜 사람이 해야 할까?" 큰 텍스트 |

**디자인 팁**:
- 숫자를 강조할 때 크게 (예: "**17,000줄**")
- 부정적 내용은 ❌ 아이콘, 긍정적 내용은 ✅ 아이콘 일관되게

---

### 2. 기대 섹션 (Slide 4-7)

**목표**: 솔루션의 가치를 직관적으로

| Slide | 레이아웃 제안 |
|-------|--------------|
| 4 | 2분할: 왼쪽 "기존 방식" (회색 톤) vs 오른쪽 "Multi-Agent" (컬러 강조) |
| 5 | 중앙에 큰 숫자 "120개 DB" + 아래 설명 텍스트 |
| 6 | Before/After 비교 카드: "240시간 → 3.2시간" |
| 7 | Excalidraw 시스템 플로우 다이어그램 (이미 준비된 것 활용) |

**디자인 팁**:
- 비교 시 왼쪽은 흐리게(opacity 50%), 오른쪽은 선명하게
- "75배 빠름" 같은 핵심 수치는 **슬라이드당 1개만** 강조

---

### 3. 놀람 섹션 (Slide 8-9)

**목표**: "진짜 되네?" 감탄

| Slide | 레이아웃 제안 |
|-------|--------------|
| 8 | "실제 동작을 확인해보시죠" 한 줄 + 데모 영상 링크/QR |
| 9 | 사업적 임팩트 3개 카드 (비용 절감 / 일정 단축 / 품질 향상) |

**디자인 팁**:
- 데모 슬라이드는 최대한 심플하게 (텍스트 1-2줄)
- 임팩트 카드는 아이콘 + 제목 + 핵심 수치 구조

---

### 4. 신뢰 섹션 (Slide 10-15)

**목표**: 기술적 깊이로 신뢰 확보

| Slide | 레이아웃 제안 |
|-------|--------------|
| 10 | 3-layer 아키텍처 다이어그램 (Excalidraw) - 전체 화면 |
| 11 | 좌측: 플로우 다이어그램, 우측: 설명 카드 |
| 12 | 좌측: 손그림 다이어그램, 우측: 실제 시나리오 결과 |
| 13 | 코드 생성 플로우 (단계별 Excalidraw) |
| 14 | 대시보드 스크린샷 + 핵심 메트릭 카드 |
| 15 | Auto-scaling 시나리오 시각화 |

**디자인 팁**:
- 기술 다이어그램은 Excalidraw 그대로 배치
- 배경과 조화되도록 Excalidraw 배경을 투명하게 export

---

### 5. 흥분 섹션 (Slide 16-19)

**목표**: 미래 비전으로 기대감 고조

| Slide | 레이아웃 제안 |
|-------|--------------|
| 16 | 2분할: "현재" vs "다음 단계" (화살표로 진화 표현) |
| 17 | 로드맵 타임라인 (Phase 1,2,3 가로 배치) |
| 18 | 임팩트 요약 카드들 (개인 차원 / 팀 차원) |
| 19 | "감사합니다" + 연락처 |

---

## 참고할 레퍼런스

### 1. Anthropic 스타일 (가장 유사)

- [Code with Claude 2025 이벤트](https://www.anthropic.com/events/code-with-claude-2025)
- 특징: 흰 배경, 검정 텍스트, 단일 강조색, 큰 타이포그래피

### 2. Linear App 스타일

- [Linear Design System (Figma)](https://www.figma.com/community/file/1222872653732371433/linear-design-system)
- 특징: 극단적 미니멀리즘, 다크/라이트 모드, 깔끔한 UI

### 3. Notion 일러스트 스타일

- [Popsy Free Notion Illustrations](https://popsy.co/illustrations)
- [Notional Illustration Pack](https://getillustrations.com/illustration-pack/illustrations-for-notion-templates)
- 특징: 손그림 느낌의 흑백 일러스트 (Excalidraw와 궁합 좋음)

### 4. Figma 템플릿

- [CICLO - Minimal Presentation Template](https://www.figma.com/community/file/1036293089097484788/ciclo-minimal-presentation-template)
- [Minimalist Simple Slide Deck](https://www.figma.com/community/file/1162281073102570063/minimalist-simple-slide-deck-presentation-template)

### 5. 프레젠테이션 트렌드 가이드

- [8 Presentation Design Trends 2024 - Prezlab](https://prezlab.com/8-presentation-design-trends-for-2024/)
- 손그림 스타일 + 미니멀리즘 조합 상세 설명

---

## Excalidraw 다이어그램 통합 팁

1. **Export 설정**: 배경 투명 + PNG 2x 해상도
2. **배치**: 슬라이드 중앙 또는 우측 60% 영역
3. **여백**: 다이어그램 주변 충분한 공백 유지
4. **설명**: 좌측에 간단한 텍스트 포인트 3-4개

---

## 전체 슬라이드 구조 요약

```
[표지] 타이틀 + 서브타이틀
  │
[공감] 1-2-3: 문제 공감 유도
  │
[기대] 4-5-6-7: 솔루션 가치 제시
  │
[놀람] 8-9: 데모 + 임팩트
  │
[신뢰] 10-15: 기술 아키텍처 상세
  │
[흥분] 16-19: 로드맵 + 마무리
```

이 구조가 시나리오의 **Problem → Solution → Benefit** 스토리텔링과 잘 맞습니다.

---

## 색상 팔레트

```css
/* Primary */
--background: #FFFFFF;
--background-alt: #FAFAFA;
--text-primary: #1A1A1A;
--text-secondary: #666666;

/* Accent (MIDAS Brand) */
--accent-red: #E31837;  /* 표지에서 사용된 레드 */

/* Functional */
--success: #22C55E;
--warning: #F59E0B;
--error: #EF4444;

/* Diagram (Excalidraw default) */
--excalidraw-stroke: #1E1E1E;
--excalidraw-fill: #FFF9DB;  /* 연한 노랑 */
```

---

## 타이포그래피 가이드

| 용도 | 폰트 | 크기 | 굵기 |
|------|------|------|------|
| 슬라이드 제목 | Pretendard | 44-56pt | Bold |
| 섹션 헤더 | Pretendard | 32-40pt | SemiBold |
| 본문 텍스트 | Pretendard | 20-24pt | Regular |
| 강조 숫자 | Pretendard | 72-96pt | Bold |
| 캡션/주석 | Pretendard | 14-16pt | Regular |

---

## 추가 리소스

### OpenAI DevDay 디자인 참고

- [OpenAI DevDay 2024](https://openai.com/devday/2024/)
- [Play Studio - OpenAI DevDay Design](https://play.studio/work/openai-devday)
- 특징: Söhne Mono 타입페이스, bit 모티프, 보라/마젠타 컬러

### Stripe Sessions 디자인 참고

- [Stripe Sessions 2024](https://stripe.com/sessions/2024)
- 특징: 대담한 타이포그래피, 모던한 마감, 몰입형 브랜딩
