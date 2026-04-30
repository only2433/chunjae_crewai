# 천재교육 EduCrew AI - 아키텍처 개발 명세서

> **최초 작성**: 2026-04-29  
> **작성자**: 개발팀  
> **목적**: 이 문서만 보면 전체 시스템 구조와 변경 이력을 파악할 수 있는 유지보수 기준서

---

## 📌 문서 사용 방법

- **신규 개발자**: `1장 → 2장 → 3장` 순서로 읽으세요.
- **기능 추가 시**: `4장(과목 플러그인 추가 가이드)`을 먼저 확인하세요.
- **버그 수정 시**: `5장(이슈 이력)` 에서 유사 이슈를 먼저 검색하세요.
- **작업 완료 후**: 반드시 `5장`에 변경 내역을 기록하세요.

---

## 1장. 프로젝트 개요

### 1.1 목적
천재교육 콘텐츠팀의 **문항 출제 → 검수 → 해설 생성** 파이프라인을 CrewAI 기반 멀티 에이전트로 자동화.

### 1.2 핵심 설계 철학
- **하이브리드 LLM**: 반복 생성(출제/해설)은 무료 로컬 모델, 고정밀 검수는 GPT API 사용 → 비용 최소화
- **과목 플러그인 구조**: 수학/영어/과학 등 과목을 `subjects/` 디렉토리에 독립 모듈로 추가 가능
- **UI 완전 분리**: 비즈니스 로직(`core/`)과 UI(`ui/`)는 서로 알지 못함

### 1.3 지원 과목 로드맵

| 과목 | 상태 | 비고 |
|:---:|:---:|:---|
| 수학 | ✅ 완료 | 중학 수학, 계산형/문장제/도형형 3종 |
| 영어 | 🔄 개발 예정 | 독해/문법/어휘/서술형 |
| 과학 | 📋 장기 목표 | 미착수 |

---

## 2장. 현재 구조 (Before Refactoring) — 수학 전용 모놀리식

> **기준 시점**: 2026-04-28 이전 코드

### 2.1 디렉토리 구조

```
chunjae_crewai/
├── main.py           # ⚠️ 수학 로직 + 파이프라인 제어 + PDF 생성 혼재 (1200줄+)
├── tasks.py          # ⚠️ 수학 전용 프롬프트 하드코딩
├── agents.py         # ⚠️ 수학 전용 에이전트 페르소나 하드코딩
├── gui.py            # pywebview API (수학 전용 함수명)
├── config/
│   └── llm_config.py # LLM 인스턴스 (과목 무관, 재사용 가능)
└── ui/
    └── index.html    # 수학 전용 UI
```

### 2.2 현재 문제점 분석

| 문제 | 위치 | 영향 |
|:---|:---|:---|
| "수학" 페르소나가 `agents.py`에 하드코딩 | `agents.py` 전체 | 영어 에이전트 추가 시 동일 파일 수정 → 수학 에이전트 영향 위험 |
| 수학 프롬프트가 `tasks.py`에 하드코딩 | `tasks.py` 전체 | 영어 태스크 추가 불가능 |
| PDF 생성, logic_safety_review, 파이프라인 제어가 `main.py`에 혼재 | `main.py` 1200줄+ | 수정 시 전체 파일 영향 |
| UI가 수학 단원 리스트를 하드코딩 | `ui/index.html` | 과목 전환 불가 |
| 과목 선택 개념 없음 | `gui.py` | 수학/영어 전환 API 없음 |

### 2.3 현재 파이프라인 흐름

```
[gui.py] generate_crew(grade, topic)
    ↓
[main.py] run_chunjae_crew()
    ↓
[Crew 1] crew_generate: generator_agent + problem_generation_task (수학)
    ↓
[Crew 2] crew_review:   reviewer_agent  + review_task (수학)
    ↓
[Crew 3] crew_phase2:   explainer_agent + explanation_task (수학)
    ↓
[main.py] logic_safety_review() — GPT 최종 감수
    ↓
[결과 반환] 문제 + 해설 텍스트
```

---

## 3장. 목표 구조 (After Refactoring) — 과목 플러그인 아키텍처

### 3.1 목표 디렉토리 구조

```
chunjae_crewai/
│
├── core/                          # ✅ 과목 무관 공통 엔진
│   ├── __init__.py
│   ├── pipeline.py                # Crew 실행 오케스트레이터 (공통)
│   ├── pdf_generator.py           # PDF 생성 (수학/영어 레이아웃 분기 포함)
│   ├── safety_review.py           # logic_safety_review (공통)
│   └── llm_registry.py           # LLM 인스턴스 중앙 관리 (기존 llm_config.py 역할)
│
├── subjects/                      # ✅ 과목 플러그인 디렉토리
│   ├── __init__.py
│   ├── base.py                    # SubjectBase 추상 클래스 (모든 과목의 인터페이스)
│   │
│   ├── math/                      # ✅ 수학 플러그인 (기존 로직 이관)
│   │   ├── __init__.py
│   │   ├── config.json            # 수학 메타데이터 (단원, 학년, 문제 유형)
│   │   ├── agents.py              # 수학 에이전트 페르소나
│   │   └── tasks.py               # 수학 태스크 프롬프트
│   │
│   └── english/                   # 🔄 영어 플러그인 (신규 추가)
│       ├── __init__.py
│       ├── config.json            # 영어 메타데이터 (유형, 학년, 수준)
│       ├── agents.py              # 영어 에이전트 페르소나
│       └── tasks.py               # 영어 태스크 프롬프트
│
├── gui.py                         # pywebview API (과목 파라미터 추가)
├── main.py                        # 진입점 (core/pipeline.py 호출)
├── config/
│   └── llm_config.py             # 기존 유지 (core/llm_registry.py로 점진 이관)
└── ui/
    └── index.html                 # 과목 탭 UI (수학/영어 전환)
```

### 3.2 SubjectBase 추상 클래스 설계

모든 과목 플러그인은 아래 인터페이스를 구현해야 합니다.

```python
# subjects/base.py
from abc import ABC, abstractmethod

class SubjectBase(ABC):

    @property
    @abstractmethod
    def subject_id(self) -> str:
        """과목 식별자. e.g. 'math', 'english'"""
        pass

    @property
    @abstractmethod
    def label(self) -> str:
        """UI 표시명. e.g. '수학', '영어'"""
        pass

    @abstractmethod
    def get_generator_agent(self, use_fast: bool = False):
        """출제 에이전트를 반환합니다."""
        pass

    @abstractmethod
    def get_reviewer_agent(self):
        """검수 에이전트를 반환합니다."""
        pass

    @abstractmethod
    def get_explainer_agent(self, use_fast: bool = False):
        """해설 에이전트를 반환합니다."""
        pass

    @abstractmethod
    def get_generation_task(self, agent, grade: str, topic: str, variety_hint: str = ""):
        """출제 태스크를 반환합니다."""
        pass

    @abstractmethod
    def get_review_task(self, agent, context_tasks, grade: str):
        """검수 태스크를 반환합니다."""
        pass

    @abstractmethod
    def get_explanation_task(self, agent, context_tasks):
        """해설 태스크를 반환합니다."""
        pass

    @abstractmethod
    def get_variety_hints(self) -> list[str]:
        """문제 다양성 힌트 목록을 반환합니다. (시험지 순환용)"""
        pass
```

### 3.3 config.json 표준 형식

각 과목 플러그인은 반드시 `config.json`을 포함해야 합니다.

```json
{
  "subject_id": "math",
  "label": "수학",
  "grade_options": ["중1", "중2", "중3"],
  "topic_options": {
    "중1": ["정수와 유리수", "방정식", "함수"],
    "중2": ["연립방정식", "부등식", "도형"],
    "중3": ["인수분해", "이차방정식", "삼각비"]
  },
  "question_types": [
    { "id": "calculation", "label": "계산형", "weight": 40 },
    { "id": "word_problem", "label": "문장제", "weight": 30 },
    { "id": "geometry", "label": "도형형", "weight": 30 }
  ],
  "reviewer_model": "gpt-4o-mini",
  "generator_model": "ollama/qwen3:4b",
  "pdf_template": "math"
}
```

### 3.4 core/pipeline.py 역할

```python
# core/pipeline.py — 과목에 상관없이 동일 흐름 실행
def run_pipeline(subject: SubjectBase, grade: str, topic: str, ...):
    # 1. 과목 플러그인에서 에이전트/태스크 가져오기
    generator = subject.get_generator_agent()
    reviewer  = subject.get_reviewer_agent()
    explainer = subject.get_explainer_agent()

    # 2. Crew 실행 (흐름은 모든 과목 동일)
    crew_generate → crew_review → crew_phase2

    # 3. 공통 safety_review
    safety_review.run(...)

    # 4. 결과 반환
    return result
```

---

## 4장. 과목 플러그인 추가 가이드

> **새 과목을 추가할 때 이 섹션만 따라하면 됩니다.**

### 4.1 추가 절차 (5단계)

```
Step 1. subjects/{과목명}/ 디렉토리 생성
Step 2. config.json 작성 (3.3 표준 형식 참고)
Step 3. agents.py 작성 (SubjectBase 참고, 과목별 페르소나 작성)
Step 4. tasks.py 작성 (SubjectBase 참고, 과목별 프롬프트 작성)
Step 5. ui/index.html에 과목 탭 추가 (config.json 자동 읽기)
```

### 4.2 영어 과목 설계 상세 (`subjects/english/`)

#### 에이전트 페르소나

| 에이전트 | 역할 | 사용 LLM |
|:---|:---|:---:|
| english_generator | 중/고등 영어 교과서 문제 출제 전문가 | qwen3:4b (로컬) |
| english_reviewer | 원어민 수준 영어 감수관 + 교육과정 적합성 | gpt-4o-mini |
| english_explainer | 영어 핵심 어법 + 오답 이유 해설가 | qwen3:4b (로컬) |

#### 영어 문제 유형 (variety_hints)

```
유형 A (독해형): 영어 지문 제시 → 주제/요지/세부내용 파악
유형 B (문법형): 어법/어형 변화/올바른 표현 선택
유형 C (어휘형): 빈칸 완성/동의어/문맥상 적절한 어휘
유형 D (서술형): 우리말 조건에 맞게 영어로 쓰기
```

#### 영어 검수 특화 포인트

수학과 달리 영어 검수관은 다음을 추가 확인해야 합니다:

```python
# subjects/english/tasks.py — review_task에 추가할 항목
"""
ENGLISH-SPECIFIC CHECKS:
A) NATURAL ENGLISH: Is the passage/question written in natural, idiomatic English?
   - Avoid awkward phrasing, unnatural collocations
B) CURRICULUM FIT: Is the vocabulary and grammar level appropriate for {grade}?
   - 중1: 기초 문법, 일상 어휘
   - 고3: 수능 수준 추상적 지문, 고급 어휘
C) COPYRIGHT SAFETY: Does the passage resemble any known copyrighted text?
   - If yes, modify key elements while preserving the topic.
D) ANSWER UNAMBIGUITY: For MCQ, ensure exactly ONE option is correct.
   - Especially critical for grammar questions.
"""
```

### 4.3 PDF 템플릿 분기 설계 (`core/pdf_generator.py`)

```python
def generate_pdf(problems, subject_id, grade, topic, with_explanation=False):
    if subject_id == "math":
        return _render_math_pdf(problems, ...)    # 기존 로직
    elif subject_id == "english":
        return _render_english_pdf(problems, ...) # 신규: 지문 박스 레이아웃
```

영어 PDF 레이아웃은 수학과 다릅니다:
- **지문 박스**: 영어 독해 지문을 회색 박스 안에 배치
- **라인 번호**: 독해 지문에 줄 번호 표시 (수능 스타일)
- **2단 구성**: 지문(좌) + 문제(우) 배치 옵션

---

## 5장. 리팩토링 실행 계획

### Phase 1 — 기반 구조 생성 (수학 로직은 건드리지 않음)

> **목표**: 새 디렉토리 구조를 만들되, 기존 수학 기능이 100% 동작하는 상태 유지

| 작업 | 파일 | 상태 |
|:---|:---|:---:|
| `core/` 디렉토리 생성 | `core/__init__.py` | ✅ 완료 |
| SubjectBase 추상 클래스 작성 | `subjects/base.py` | ✅ 완료 |
| `subjects/math/` 디렉토리 생성 | - | ✅ 완료 |
| 기존 `agents.py` → `subjects/math/agents.py`로 이관 | `subjects/math/agents.py` | ✅ 완료 |
| 기존 `tasks.py` → `subjects/math/tasks.py`로 이관 | `subjects/math/tasks.py` | ✅ 완료 |
| 수학 `config.json` 작성 | `subjects/math/config.json` | ✅ 완료 |
| MathSubject 클래스 작성 (SubjectBase 구현) | `subjects/math/__init__.py` | ✅ 완료 |

### Phase 2 — core 엔진 분리 (main.py 분해)

| 작업 | 파일 | 상태 |
|:---|:---|:---:|
| PDF 생성 로직 분리 | `core/pdf_generator.py` | ✅ 완료 |
| logic_safety_review 분리 | `core/safety_review.py` | ✅ 완료 |
| 파이프라인 오케스트레이터 작성 | `core/pipeline.py` | ✅ 완료 |
| `main.py` 경량화 (core/ 호출만 남기기) | `main.py` | ✅ 완료 |

### Phase 3 — 영어 플러그인 추가

| 작업 | 파일 | 상태 |
|:---|:---|:---:|
| 영어 `config.json` 작성 | `subjects/english/config.json` | ✅ 완료 |
| 영어 에이전트 페르소나 작성 | `subjects/english/agents.py` | ✅ 완료 |
| 영어 태스크 프롬프트 작성 | `subjects/english/tasks.py` | ✅ 완료 |
| EnglishSubject 클래스 작성 | `subjects/english/__init__.py` | ✅ 완료 |
| 과목 레지스트리 작성 | `subjects/__init__.py` | ✅ 완료 |
| 영어 PDF 레이아웃 분기 추가 | `core/pdf_generator.py` | ✅ 완료 |

### Phase 4 — UI 업데이트

| 작업 | 파일 | 상태 |
|:---|:---|:---:|
| 과목 선택 탭 추가 (수학/영어) | `ui/index.html` | ✅ 완료 |
| 과목별 Primary Color 전환 | `ui/index.html` | ✅ 완료 |
| 영어 단원 목록 DB 추가 | `ui/index.html` | ✅ 완료 |
| 단원 칩 과목별 분기 | `ui/index.html` + `gui.py` | ✅ 완료 |

---

## 6장. 이슈 이력 (버그 & 결정 기록)

> 작업 완료 후 반드시 이 섹션에 기록하세요.

### [2026-04-28] Crew 분리 (2-Crew 구조)
- **문제**: 출제(로컬)와 검수(GPT)가 하나의 Crew로 묶여 있어 UI 단계 구분 불가
- **해결**: `crew_generate` + `crew_review`로 분리
- **영향 파일**: `main.py`

### [2026-04-28] 정답 누출 차단 이중 안전망
- **문제**: qwen3:4b가 문제 텍스트 하단에 `정답: 3번` 등을 포함시킴
- **해결 1**: GPT 검수 프롬프트에 삭제 지시 추가 (`tasks.py`)
- **해결 2**: `main.py` 후처리 정규식 강제 제거
- **재발 시**: `tasks.py`의 `review_task` STEP 4 + `main.py`의 `_answer_pattern` 확인

### [2026-04-28] MCQ 연립방정식 오탐 수정
- **문제**: 쌍 정답(`x=2, y=1`)을 단일 숫자로 비교하여 `FAIL_PROBLEM` 오탐
- **해결**: CHECK 3을 교차검증 방식으로 전환 (해설의 `【최종 정답】`과 보기 교차 대조)
- **영향 파일**: `main.py`의 `logic_safety_review()`

### [2026-04-28] qwen3:4b max_tokens 금지
- **문제**: `max_tokens` 설정 시 Thinking 토큰 소비 후 `Final Answer:` 생성 실패
- **결정**: `config/llm_config.py`에서 `max_tokens` 파라미터 완전 제거
- **⚠️ 재적용 금지**: 이 설정은 되돌리지 말 것

### [2026-04-28] 문제 소재 다양성 3종 순환
- **문제**: 10문제 연속 생성 시 같은 패턴 반복
- **해결**: `variety_hint` 파라미터 추가 (계산형/문장제/도형형 순환)
- **영향 파일**: `tasks.py`, `main.py`의 `run_exam_crew()`

---

## 7장. 환경 설정 기준

### 7.1 필수 환경

```bash
# Ollama 로컬 모델 실행 (반드시 먼저 실행)
ollama run qwen3:4b

# Python 패키지
pip install crewai openai pywebview reportlab python-dotenv
```

### 7.2 .env 설정

```
OPENAI_API_KEY=sk-...          # OpenAI API 키 (검수용)
CREWAI_TELEMETRY_OPT_OUT=true  # CrewAI 원격 텔레메트리 비활성화
OTEL_SDK_DISABLED=true         # OpenTelemetry 비활성화 (성능 향상)
```

### 7.3 LLM 역할 분담 원칙

| 역할 | 모델 | 이유 |
|:---|:---:|:---|
| 문제 출제 | `qwen3:4b` (로컬) | 반복 생성 → 비용 0원 |
| 해설 작성 | `qwen3:4b` (로컬) | 반복 생성 → 비용 0원 |
| 문제 검수 | `gpt-4o-mini` (API) | 높은 정확도 필요 |
| 최종 감수 | `gpt-4o-mini` (API) | 논리 검증 필요 |
| 빠른 모드 | `gpt-4o-mini` (API) | 출제/해설도 GPT로 |

> **원칙**: 정확도보다 속도·비용이 중요한 작업은 로컬, 품질이 최우선인 작업은 GPT

---

*이 문서는 개발 진행에 따라 지속적으로 업데이트됩니다.*  
*작업 완료 시 반드시 Phase 체크박스와 6장 이슈 이력을 갱신하세요.*
