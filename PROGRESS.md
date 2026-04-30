# 천재교육 EduCrew AI - 개발 진행 이력

> 마지막 업데이트: 2026-04-29

---

## 📌 프로젝트 개요

CrewAI 기반 **수학/영어 문제 자동 출제 시스템** (과목 플러그인 아키텍처).
- **로컬 모델**: `qwen3:4b` (Ollama) — 문제 출제 + 해설 생성
- **GPT 모델**: `gpt-4o-mini` (OpenAI) — 문제 검수 + 최종 감수
- **UI**: pywebview + HTML/CSS/JS
- **아키텍처 명세**: `ARCHITECTURE.md` 참조

---

## 🔄 Phase 1 — 과목 플러그인 기반 구조 생성 (2026-04-29) ✅ 완료

### 배경
- 수학 전용 코드가 루트 `agents.py`, `tasks.py`, `main.py`에 하드코딩되어 있어
  영어 등 신규 과목 추가 시 기존 코드 오염 위험
- 과목 플러그인 구조(`subjects/`)를 도입하여 확장성 확보

### 생성된 파일

| 파일 | 역할 |
|:---|:---|
| `subjects/base.py` | `SubjectBase` 추상 인터페이스 (7개 메서드 강제) |
| `subjects/math/__init__.py` | `MathSubject` 클래스 (SubjectBase 구현체) |
| `subjects/math/agents.py` | 수학 에이전트 페르소나 (루트에서 이관) |
| `subjects/math/tasks.py` | 수학 태스크 프롬프트 (루트에서 이관) |
| `subjects/math/config.json` | 수학 메타데이터 (학년/단원/문제유형 목록) |
| `core/__init__.py` | core 패키지 (Phase 2에서 내용 채울 예정) |

### 변경된 파일

| 파일 | 변경 내용 |
|:---|:---|
| `main.py` | import 경로를 `subjects.math.agents/tasks`로 변경 |
| `agents.py` (루트) | 호환성 래퍼로 변환 (re-export만 수행) |
| `tasks.py` (루트) | 호환성 래퍼로 변환 (re-export만 수행) |
| `config/llm_config.py` | 이모지 제거 (cp949 인코딩 오류 수정) |

### 검증 결과
```
python -c "from subjects.math import MathSubject; s = MathSubject(); print(s.subject_id, s.label)"
→ OK: math 수학  ✅
```

---

## 🔄 Phase 2 — core 엔진 분리 (main.py 분해) (2026-04-29) ✅ 완료

### 배경
- `main.py`가 618줄짜리 단일 파일로, PDF 생성 + 안전 감수 + 파이프라인 제어가 혼재
- core/ 패키지로 분리하여 책임을 명확히 분리

### 생성된 파일

| 파일 | 역할 | 이관 원본 |
|:---|:---|:---|
| `core/safety_review.py` | `logic_safety_review()` — GPT 최종 감수 | `main.py:17~63` |
| `core/pdf_generator.py` | `generate_pdf_exam()` — reportlab PDF 생성 | `main.py:377~523` |
| `core/pipeline.py` | `run_pipeline()`, `run_exam_pipeline()`, `_run_python_illustrator()` | `main.py:66~610` |

### 변경된 파일

| 파일 | 변경 전 | 변경 후 |
|:---|:---:|:---:|
| `main.py` | 618줄 (전체 비즈니스 로직) | 60줄 (래퍼만 남김) |

### 하위 호환 설계
- `gui.py`는 `from main import run_chunjae_crew, run_exam_crew`를 사용하고 있음
- `main.py`에 동명의 래퍼 함수를 유지하여 `gui.py` 수정 없이 동작 보장
- 래퍼 함수는 내부에서 `MathSubject()` + `core.pipeline` 을 호출

### 검증 결과
```
python -c "from core.pipeline import run_pipeline, run_exam_pipeline; from core.safety_review import logic_safety_review; from core.pdf_generator import generate_pdf_exam; from main import run_chunjae_crew, run_exam_crew; print('ALL OK')"
→ Phase 2 import check: ALL OK  ✅
```

---

## 🔄 Phase 3 — 영어 과목 플러그인 추가 (2026-04-29) ✅ 완료

### 배경
- 수학 전용 구조에서 영어를 동등한 과목으로 지원
- 과목 레지스트리 패턴으로 Phase 4(과학) 추가 시 단 2줄 등록으로 확장 가능

### 생성된 파일

| 파일 | 역할 |
|:---|:---|
| `subjects/english/config.json` | 영어 메타데이터 (학년/단원/문제유형) |
| `subjects/english/agents.py` | 영어 에이전트 3종 페르소나 |
| `subjects/english/tasks.py` | 영어 태스크 프롬프트 (문법/어휘/독해 유형 순환) |
| `subjects/english/__init__.py` | `EnglishSubject` 클래스 (SubjectBase 구현) |

### 변경된 파일

| 파일 | 변경 내용 |
|:---|:---|
| `subjects/__init__.py` | 과목 레지스트리 (`get_subject()`, `list_subjects()`) |
| `gui.py` | `subject_id` 파라미터 추가, `get_subjects()` API 추가 |
| `ui/index.html` | 수학/영어 과목 탭 UI, 영어 단원 DB, API 호출에 `subject_id` 전달 |

### 설계 원칙

```
subjects/
├── __init__.py      ← 레지스트리 (새 과목 추가 = 2줄 추가)
├── base.py          ← SubjectBase 추상 인터페이스
├── math/            ← 수학 플러그인
└── english/         ← 영어 플러그인 (Phase 3 신규)
```

### UI 변화
- 수학(파랑) / 영어(초록) 과목 탭 → 선택 시 Primary Color 자동 전환
- 영어 선택 시 중1/중2/중3 학년 탭 노출 (수학은 중1/중2)
- 영어 단원 칩: 문법기초 / 품사·어휘 / 시제·준동사 / 독해 등

### 검증 결과
```
Registry: ['math', 'english']   ← 레지스트리 정상
기존 41개 테스트: 41 passed (회귀 없음)  ✅
```

---

 (2026-04-29) — 41/41 PASS

```
pytest tests/test_phase2_regression.py -v
41 passed, 42 warnings in 5.48s
```

| 테스트 클래스 | 항목 | 내용 |
|:---|:---:|:---|
| TestImportChain | 10 | 전체 모듈 임포트 체인 |
| TestSubjectBaseInterface | 6 | MathSubject 인터페이스 준수 |
| TestAgentCreation | 4 | 3종 에이전트 생성 및 역할 |
| TestTaskCreation | 5 | 태스크 description 내용 |
| TestBackwardCompatibility | 5 | 래퍼 함수 시그니처 |
| TestPdfGenerator | 4 | LaTeX변환 + 실제 PDF 생성 |
| TestSafetyReview | 3 | API Mock 반환값 검증 |
| TestAnswerLeakRemoval | 4 | 정답 누출 제거 로직 |

> **이슈 없음** — Phase 2 후 수학 기능 100% 정상 동작 확인

---

## 🏗️ 현재 파이프라인 구조 (Phase 2 이후)


```
[1단계] 출제 마스터 (qwen3:4b)
    ↓ Crew 1: crew_generate
[2단계] 문제 검수관 (gpt-4o-mini)
    ↓ Crew 2: crew_review
[3단계] 해설가 (qwen3:4b)
    ↓ Crew 3: crew_phase2
[4단계] 최종 감수 (gpt-4o-mini, logic_safety_review)
    ↓
[결과 출력] 문제 + 해설 + 이미지(선택)
```

---

## ✅ 이번 세션 작업 내역

### 1. Crew 분리 (2-Crew 구조)
**문제**: 출제(로컬)와 검수(GPT)가 하나의 Crew로 묶여 있어 UI가 단계를 구분 못 함.  
**해결**: `crew_generate` + `crew_review`로 분리 → 1단계 done 후 2단계 active가 정확히 표시됨.

```python
# main.py
crew_generate = Crew(agents=[generator], tasks=[task1], ...)
crew_generate.kickoff()
notify(1, "문제 출제 완료 ✓", "done")

notify(2, "OpenAI 감수관이 문제 검증 중...", "active")
crew_review = Crew(agents=[reviewer], tasks=[task2], ...)
crew_review.kickoff()
notify(2, "OpenAI 감수관 검증 완료 ✓", "done")
```

---

### 2. 정답 누출 차단 (이중 안전망)

**문제**: 로컬 모델이 문제 텍스트 하단에 몰래 "정답: 3번" 같은 답을 포함시킴.

**해결 1**: GPT 검수관 OUTPUT FORMAT에 삭제 지시 추가 (`tasks.py`)
```python
f"CRITICAL: If the problem text contains any answer disclosure (e.g. '정답:', '답:', 'Answer:'),\n"
f"DELETE that line entirely. The problem output must NEVER contain the answer.\n"
```

**해결 2**: `main.py` 후처리로 정규식 강제 제거
```python
_answer_pattern = re.compile(
    r'^\s*(정답|답|Answer|Correct Answer|해답|풀이)\s*[:：].*$',
    re.IGNORECASE | re.MULTILINE
)
final_problem = _answer_pattern.sub('', final_problem).strip()
```

---

### 3. MCQ 오탐 수정 (logic_safety_review)

**문제**: 연립방정식처럼 쌍(pair) 형태 정답(`x=2, y=1`)을 검수할 때, 기존 프롬프트가 단일 숫자만 예시로 제공해서 보기에 답이 있어도 `FAIL_PROBLEM` 오탐 발생.

**해결**: CHECK 3 방식을 **교차 검증** 방식으로 전환
- 기존: GPT가 직접 재계산 → 단일 숫자 비교
- 변경: 해설의 `【최종 정답】`과 보기 값을 교차 대조 (단일/쌍/복합 모두 지원)

```python
"CHECK 3 - MCQ CROSS-REFERENCE (MOST CRITICAL):\n"
"  a) Find the answer stated in the explanation's section marked 【최종 정답】.\n"
"  b) Look at ALL numbered options in the problem (1~5).\n"
"  c) Check if the stated answer corresponds to any of those options.\n"
"     - For pair answers like 'x=2, y=1', check if any option contains both x=2 AND y=1.\n"
"  Example PASS: explanation says '② x=2, y=1', problem has option '2) x=2, y=1' => PASS\n"
```

---

### 4. UI 개선 - 로딩바 & 마진

**변경 사항**:
- `stage-item.active::after`: 하단에 좌→우로 흐르는 펄싱 로딩바 (`loadingBar` 애니메이션)
- `stage-icon`: active 시 파란 글로우 깜빡임 (`iconPulse` 애니메이션)
- 결과 카드에 `margin: 0 4px` 추가 → 메인/서브 박스 좌우 여백 확보
- 카드 내부 padding 조정: `48px → 36px 40px`

---

### 5. 시험지 일괄 생성 기능 (10문제 → PDF)

**버튼 3개 분리**:

| 버튼 | 색상 | 기능 | 예상 시간 |
|:---|:---:|:---|:---:|
| 📝 1문제 출제 | 검정 | 문제+해설+감수 전체 | ~90초 |
| 📋 시험지 (10문제) | 파랑 | 문제만 10개 → PDF | ~6~8분 |
| 📖 시험지+해설 (10문제) | 보라 | 문제+해설 10개 → PDF | ~15분 |

**주요 함수**:
- `run_exam_crew(grade, topic, count, with_explanation)` — `main.py`
- `generate_pdf_exam(problems_list, grade, topic)` — reportlab 기반 한글 PDF
- `generate_exam()` / `generate_exam_full()` / `open_pdf()` — `gui.py` API
- `startExam()` / `startExamFull()` / `openPdf()` — `index.html` JS

**PDF 구성**:
- 시험지 모드: 표지 + 문제 1~10
- 해설 포함 모드: 표지 + 문제 1~10 (1페이지) + 정답/해설 (2페이지)

---

### 6. 문제 소재 다양성 (3종 순환)

**문제**: 10문제를 동일 프롬프트로 생성하면 같은 패턴 반복.  
**해결**: `tasks.py`에 `variety_hint` 파라미터 추가, `run_exam_crew`에서 3종 순환 적용.

```
문제 1, 4, 7, 10 → 계산형 (수식 직접 계산)
문제 2, 5, 8     → 문장제 (실생활 소재)
문제 3, 6, 9     → 도형형 (삼각형/사각형 소재)
```

> **원칙**: 난이도는 건드리지 않고, 문제 소재(맥락)만 순환.

---

## 📁 현재 파일 구조

```
chunjae_crewai/
├── main.py           # 파이프라인 제어, logic_safety_review, PDF 생성
├── tasks.py          # 출제/검수/해설 태스크 프롬프트 (variety_hint 포함)
├── agents.py         # 에이전트 페르소나 정의
├── gui.py            # pywebview API (generate_crew/exam/exam_full/open_pdf)
├── config/
│   └── llm_config.py # qwen3:4b (로컬), gpt-4o-mini (검수/감수)
└── ui/
    ├── index.html    # 메인 UI (3버튼, 진행 단계, 결과, PDF)
    └── exam_output.pdf  # 시험지 출력 결과
```

---

## ⚙️ 환경 설정

```bash
# 필수: Ollama에서 qwen3:4b 실행
ollama run qwen3:4b

# 필수 패키지
pip install crewai openai pywebview reportlab

# 실행
python gui.py
```

**환경 변수 (`.env`)**:
```
OPENAI_API_KEY=sk-...
CREWAI_TELEMETRY_OPT_OUT=true
OTEL_SDK_DISABLED=true
```

---

## 🔮 다음 개발 후보

- [ ] 문제 저장/히스토리 (SQLite)
- [ ] 문제 재출제 버튼 (결과 화면에 "다시 만들기")
- [ ] 난이도 슬라이더 (기본/심화/최고난도)
- [ ] PyInstaller .exe 패키징 (배포용)
- [ ] 출제 이력 대시보드 (단원별 출제 횟수 통계)
