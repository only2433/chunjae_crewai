"""
tests/test_english_subject.py
──────────────────────────────
영어 과목 플러그인 검증 테스트 (Phase 3 + 성별 모호성 수정 v2)

[테스트 범위]
1. TestEnglishImport         - import 체인 검증
2. TestEnglishSubjectClass   - EnglishSubject 인터페이스 준수
3. TestEnglishAgents         - 에이전트 생성 및 역할 검증
4. TestGenderAmbiguityRules  - 성별 모호성 방지 규칙이 프롬프트에 포함되는지 검증
5. TestEnglishReviewTask     - 검수 태스크 5단계 구조 검증
6. TestEnglishRegistry       - 레지스트리에서 english 정상 반환 검증
7. TestCp949Compatibility    - cp949 인코딩 호환성 (em-dash 등 특수문자 금지)
"""

import sys
import os
import pytest

# 프로젝트 루트를 sys.path에 추가
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ──────────────────────────────────────────────────────────────
# 1. Import 체인 검증
# ──────────────────────────────────────────────────────────────
class TestEnglishImport:

    def test_english_config_import(self):
        import json
        cfg_path = os.path.join(ROOT, "subjects", "english", "config.json")
        assert os.path.exists(cfg_path), "config.json이 없습니다"
        with open(cfg_path, encoding="utf-8") as f:
            cfg = json.load(f)
        assert cfg["subject_id"] == "english"

    def test_english_agents_import(self):
        from subjects.english.agents import (
            create_generator_agent,
            create_reviewer_agent,
            create_explainer_agent,
        )

    def test_english_tasks_import(self):
        from subjects.english.tasks import (
            problem_generation_task,
            review_task,
            explanation_task,
        )

    def test_english_subject_import(self):
        from subjects.english import EnglishSubject

    def test_registry_import(self):
        from subjects import get_subject, list_subjects


# ──────────────────────────────────────────────────────────────
# 2. EnglishSubject 인터페이스 준수
# ──────────────────────────────────────────────────────────────
class TestEnglishSubjectClass:

    @pytest.fixture
    def subject(self):
        from subjects.english import EnglishSubject
        return EnglishSubject()

    def test_subject_id(self, subject):
        assert subject.subject_id == "english"

    def test_label(self, subject):
        assert subject.label == "영어"

    def test_config_loaded(self, subject):
        assert isinstance(subject.config, dict)
        assert "grade_options" in subject.config
        assert "topic_options" in subject.config

    def test_grade_options(self, subject):
        grades = subject.config["grade_options"]
        assert "중1" in grades
        assert "중2" in grades
        assert "중3" in grades  # 수학은 중3 없음 — 영어만의 특징

    def test_variety_hints_count(self, subject):
        hints = subject.get_variety_hints()
        assert len(hints) == 3, f"variety_hints가 3개여야 합니다. 현재: {len(hints)}"

    def test_variety_hints_cover_types(self, subject):
        hints = " ".join(subject.get_variety_hints())
        assert "문법형" in hints
        assert "어휘형" in hints
        assert "독해형" in hints

    def test_has_all_interface_methods(self, subject):
        assert callable(getattr(subject, "get_generator_agent", None))
        assert callable(getattr(subject, "get_reviewer_agent", None))
        assert callable(getattr(subject, "get_explainer_agent", None))
        assert callable(getattr(subject, "get_generation_task", None))
        assert callable(getattr(subject, "get_review_task", None))
        assert callable(getattr(subject, "get_explanation_task", None))


# ──────────────────────────────────────────────────────────────
# 3. 에이전트 생성 및 역할 검증
# ──────────────────────────────────────────────────────────────
class TestEnglishAgents:

    def test_generator_agent_role(self):
        from subjects.english.agents import create_generator_agent
        agent = create_generator_agent()
        assert "영어" in agent.role or "English" in agent.role or "출제" in agent.role

    def test_reviewer_agent_role(self):
        from subjects.english.agents import create_reviewer_agent
        agent = create_reviewer_agent()
        assert "감수" in agent.role or "검수" in agent.role or "reviewer" in agent.role.lower()

    def test_reviewer_uses_gpt(self):
        """검수 에이전트는 항상 GPT 계열 모델을 사용해야 합니다."""
        from subjects.english.agents import create_reviewer_agent
        from config.llm_config import reviewer_llm
        agent = create_reviewer_agent()
        # LLM이 reviewer_llm과 동일한 타입이어야 함
        assert type(agent.llm) == type(reviewer_llm)

    def test_explainer_agent_has_backstory(self):
        from subjects.english.agents import create_explainer_agent
        agent = create_explainer_agent()
        assert len(agent.backstory) > 50


# ──────────────────────────────────────────────────────────────
# 4. 성별 모호성 방지 규칙 검증 (핵심 테스트)
# ──────────────────────────────────────────────────────────────
class TestGenderAmbiguityRules:

    @pytest.fixture
    def gen_task_desc(self):
        from subjects.english.agents import create_generator_agent
        from subjects.english.tasks import problem_generation_task
        agent = create_generator_agent()
        task = problem_generation_task(agent, topic="인칭대명사와 소유격", grade="중1")
        return task.description

    @pytest.fixture
    def review_task_desc(self):
        from subjects.english.agents import create_generator_agent, create_reviewer_agent
        from subjects.english.tasks import problem_generation_task, review_task
        g = create_generator_agent()
        r = create_reviewer_agent()
        t1 = problem_generation_task(g, topic="인칭대명사와 소유격", grade="중1")
        t2 = review_task(r, [t1], grade="중1")
        return t2.description

    def test_generation_prohibits_gender_neutral_nouns(self, gen_task_desc):
        """출제 프롬프트에 성별 모호 명사 금지 규칙이 포함되어야 합니다."""
        desc = gen_task_desc
        assert "GENDER" in desc, "GENDER CLARITY RULE이 출제 프롬프트에 없습니다"
        assert "friend" in desc, "friend 예시가 출제 프롬프트에 없습니다"

    def test_generation_has_self_check(self, gen_task_desc):
        """출제 전 셀프 체크 항목이 포함되어야 합니다."""
        assert "MCQ SELF-CHECK" in gen_task_desc

    def test_generation_has_correct_example(self, gen_task_desc):
        """올바른 예시(brother)와 금지 예시(friend)가 모두 있어야 합니다."""
        assert "brother" in gen_task_desc
        assert "FORBIDDEN" in gen_task_desc or "BAD" in gen_task_desc

    def test_review_has_gender_ambiguity_check(self, review_task_desc):
        """검수 프롬프트에 GENDER AMBIGUITY CHECK 단계가 있어야 합니다."""
        assert "GENDER AMBIGUITY" in review_task_desc

    def test_review_lists_gender_neutral_nouns(self, review_task_desc):
        """검수 프롬프트에 성별 모호 명사 목록이 포함되어야 합니다."""
        desc = review_task_desc
        assert "friend" in desc
        assert "teacher" in desc
        assert "student" in desc

    def test_review_lists_gender_clear_nouns(self, review_task_desc):
        """검수 프롬프트에 성별 명확 명사 예시가 있어야 합니다."""
        desc = review_task_desc
        assert "brother" in desc or "sister" in desc

    def test_review_provides_fix_options(self, review_task_desc):
        """검수 프롬프트에 수정 방법 3가지가 포함되어야 합니다."""
        desc = review_task_desc
        # 수정 옵션: 명사 교체, 이름 추가, their 활용
        assert "sister" in desc or "brother" in desc  # 옵션 A
        assert "their" in desc                          # 옵션 C

    def test_review_five_steps_structure(self, review_task_desc):
        """검수 태스크가 5단계 구조를 가져야 합니다."""
        desc = review_task_desc
        assert "STEP 1" in desc
        assert "STEP 2" in desc
        assert "STEP 3" in desc
        assert "STEP 4" in desc
        assert "STEP 5" in desc


# ──────────────────────────────────────────────────────────────
# 5. 해설 태스크 구조 검증
# ──────────────────────────────────────────────────────────────
class TestExplanationTask:

    def test_explanation_has_three_sections(self):
        from subjects.english.agents import create_explainer_agent
        from subjects.english.tasks import explanation_task
        agent = create_explainer_agent()
        task = explanation_task(agent, context_tasks=[])
        desc = task.description
        assert "【핵심 어법】" in desc
        assert "【풀이 과정】" in desc
        assert "【최종 정답】" in desc

    def test_explanation_requires_wrong_answer_analysis(self):
        """해설에 오답 분석이 필수 포함되어야 합니다."""
        from subjects.english.agents import create_explainer_agent
        from subjects.english.tasks import explanation_task
        agent = create_explainer_agent()
        task = explanation_task(agent, context_tasks=[])
        assert "오답" in task.description


# ──────────────────────────────────────────────────────────────
# 6. 레지스트리 검증
# ──────────────────────────────────────────────────────────────
class TestEnglishRegistry:

    def test_english_in_registry(self):
        from subjects import list_subjects
        assert "english" in list_subjects()

    def test_math_still_in_registry(self):
        """영어 추가 후 수학이 사라지지 않았는지 확인 (회귀)."""
        from subjects import list_subjects
        assert "math" in list_subjects()

    def test_get_subject_english(self):
        from subjects import get_subject
        from subjects.english import EnglishSubject
        subject = get_subject("english")
        assert isinstance(subject, EnglishSubject)

    def test_get_subject_invalid_raises(self):
        from subjects import get_subject
        with pytest.raises(ValueError):
            get_subject("science")  # 아직 미등록


# ──────────────────────────────────────────────────────────────
# 7. cp949 인코딩 호환성 (em-dash 등 특수문자 금지)
# ──────────────────────────────────────────────────────────────
class TestCp949Compatibility:
    """
    터미널 cp949 환경에서 print() 시 인코딩 오류가 발생하는
    특수 유니코드 문자가 소스 파일에 없는지 검증합니다.

    위험 문자: em-dash (U+2014 —), en-dash (U+2013 –), 
               curved quotes (U+201C " U+201D "), ellipsis (U+2026 …)
    """

    DANGEROUS_CHARS = {
        0x2014: "em-dash (—)",
        0x2013: "en-dash (–)",
        0x201C: "left double quote (\u201c)",
        0x201D: "right double quote (\u201d)",
        0x2026: "ellipsis (…)",
    }

    TARGET_FILES = [
        "subjects/english/agents.py",
        "subjects/english/tasks.py",
        "subjects/english/__init__.py",
        "core/safety_review.py",
        "config/llm_config.py",
    ]

    @pytest.mark.parametrize("rel_path", TARGET_FILES)
    def test_no_cp949_incompatible_chars(self, rel_path):
        filepath = os.path.join(ROOT, rel_path)
        if not os.path.exists(filepath):
            pytest.skip(f"{rel_path} 파일이 없습니다")

        content = open(filepath, encoding="utf-8").read()
        found = []
        for code, name in self.DANGEROUS_CHARS.items():
            positions = [i for i, c in enumerate(content) if ord(c) == code]
            if positions:
                found.append(f"{name} at positions {positions[:3]}")

        assert not found, (
            f"{rel_path}에 cp949 호환 불가 문자 발견:\n" + "\n".join(found)
        )
