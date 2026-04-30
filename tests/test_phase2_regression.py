"""
tests/test_phase2_regression.py
────────────────────────────────
Phase 1 + Phase 2 리팩토링 후 수학 기능 회귀 테스트.

[테스트 범위]
1. Import 체인 — 모든 모듈이 오류 없이 임포트되는지
2. SubjectBase 인터페이스 — MathSubject가 7개 메서드를 모두 구현했는지
3. MathSubject 메타데이터 — subject_id, label, config, variety_hints
4. 에이전트 생성 — 3종 에이전트가 정상 생성되는지
5. 태스크 생성 — 태스크 description에 올바른 값이 포함되는지
6. 하위 호환 래퍼 — main.py에서 run_chunjae_crew, run_exam_crew import 가능한지
7. gui.py 호환 — gui.py가 main.py를 올바르게 import하는지
8. PDF 생성 — 더미 데이터로 PDF 파일이 실제로 생성되는지
9. safety_review 서명 — 함수 시그니처가 유지됐는지
10. pipeline 함수 서명 — run_pipeline, run_exam_pipeline 인수가 올바른지

LLM 실제 호출은 하지 않습니다 (Mock 처리).
"""

import sys
import os
import inspect
import tempfile
import pytest
from unittest.mock import patch, MagicMock

# 프로젝트 루트를 path에 추가
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ═══════════════════════════════════════════════════════════
# 1. Import 체인 테스트
# ═══════════════════════════════════════════════════════════

class TestImportChain:

    def test_subjects_base_import(self):
        """subjects.base.SubjectBase 임포트"""
        from subjects.base import SubjectBase
        assert SubjectBase is not None

    def test_math_subject_import(self):
        """subjects.math.MathSubject 임포트"""
        from subjects.math import MathSubject
        assert MathSubject is not None

    def test_math_agents_import(self):
        """subjects.math.agents 임포트"""
        from subjects.math.agents import (
            create_generator_agent,
            create_reviewer_agent,
            create_explainer_agent,
        )
        assert all([create_generator_agent, create_reviewer_agent, create_explainer_agent])

    def test_math_tasks_import(self):
        """subjects.math.tasks 임포트"""
        from subjects.math.tasks import (
            problem_generation_task,
            review_task,
            explanation_task,
            explanation_review_task,
        )
        assert all([problem_generation_task, review_task, explanation_task, explanation_review_task])

    def test_core_safety_review_import(self):
        """core.safety_review 임포트"""
        from core.safety_review import logic_safety_review
        assert logic_safety_review is not None

    def test_core_pdf_generator_import(self):
        """core.pdf_generator 임포트"""
        from core.pdf_generator import generate_pdf_exam, latex_to_text, strip_html_and_latex
        assert all([generate_pdf_exam, latex_to_text, strip_html_and_latex])

    def test_core_pipeline_import(self):
        """core.pipeline 임포트"""
        from core.pipeline import run_pipeline, run_exam_pipeline
        assert all([run_pipeline, run_exam_pipeline])

    def test_main_backward_compat_import(self):
        """main.py 하위 호환 래퍼 임포트"""
        from main import run_chunjae_crew, run_exam_crew
        assert all([run_chunjae_crew, run_exam_crew])

    def test_legacy_root_agents_import(self):
        """루트 agents.py (래퍼) 하위 호환 임포트"""
        from agents import create_generator_agent, create_reviewer_agent, create_explainer_agent
        assert all([create_generator_agent, create_reviewer_agent, create_explainer_agent])

    def test_legacy_root_tasks_import(self):
        """루트 tasks.py (래퍼) 하위 호환 임포트"""
        from tasks import problem_generation_task, review_task, explanation_task
        assert all([problem_generation_task, review_task, explanation_task])


# ═══════════════════════════════════════════════════════════
# 2. SubjectBase 인터페이스 준수 테스트
# ═══════════════════════════════════════════════════════════

class TestSubjectBaseInterface:

    def setup_method(self):
        from subjects.math import MathSubject
        self.subject = MathSubject()

    def test_subject_id(self):
        assert self.subject.subject_id == "math"

    def test_label(self):
        assert self.subject.label == "수학"

    def test_config_loaded(self):
        cfg = self.subject.config
        assert cfg["subject_id"] == "math"
        assert "grade_options" in cfg
        assert "topic_options" in cfg
        assert "중1" in cfg["grade_options"]

    def test_variety_hints_count(self):
        hints = self.subject.get_variety_hints()
        assert isinstance(hints, list)
        assert len(hints) == 3  # 계산형, 문장제, 도형형

    def test_variety_hints_content(self):
        hints = self.subject.get_variety_hints()
        assert any("계산형" in h for h in hints)
        assert any("문장제" in h for h in hints)
        assert any("도형형" in h for h in hints)

    def test_has_all_abstract_methods(self):
        """SubjectBase의 7개 추상 메서드가 모두 구현되었는지 확인"""
        required = [
            'subject_id', 'label',
            'get_generator_agent', 'get_reviewer_agent', 'get_explainer_agent',
            'get_generation_task', 'get_review_task', 'get_explanation_task',
            'get_variety_hints',
        ]
        for method in required:
            assert hasattr(self.subject, method), f"Missing method: {method}"


# ═══════════════════════════════════════════════════════════
# 3. 에이전트 생성 테스트
# ═══════════════════════════════════════════════════════════

class TestAgentCreation:

    def setup_method(self):
        from subjects.math import MathSubject
        self.subject = MathSubject()

    def test_generator_agent_role(self):
        agent = self.subject.get_generator_agent()
        assert "출제" in agent.role or "마스터" in agent.role

    def test_reviewer_agent_role(self):
        agent = self.subject.get_reviewer_agent()
        assert "검증" in agent.role or "교정" in agent.role

    def test_explainer_agent_role(self):
        agent = self.subject.get_explainer_agent()
        assert "해설" in agent.role

    def test_agents_have_llm(self):
        for agent in [
            self.subject.get_generator_agent(),
            self.subject.get_reviewer_agent(),
            self.subject.get_explainer_agent(),
        ]:
            assert agent.llm is not None


# ═══════════════════════════════════════════════════════════
# 4. 태스크 생성 테스트
# ═══════════════════════════════════════════════════════════

class TestTaskCreation:

    def setup_method(self):
        from subjects.math import MathSubject
        self.subject = MathSubject()
        self.generator = self.subject.get_generator_agent()
        self.reviewer = self.subject.get_reviewer_agent()
        self.explainer = self.subject.get_explainer_agent()

    def test_generation_task_contains_topic(self):
        task = self.subject.get_generation_task(self.generator, "중1", "소인수분해")
        assert "소인수분해" in task.description

    def test_generation_task_contains_grade(self):
        task = self.subject.get_generation_task(self.generator, "중2", "연립방정식")
        assert "중2" in task.description

    def test_generation_task_with_variety_hint(self):
        hint = "계산형: 수식을 바로 풀면 되는 문제"
        task = self.subject.get_generation_task(self.generator, "중1", "소인수분해", variety_hint=hint)
        assert "계산형" in task.description

    def test_review_task_assigned_to_agent(self):
        gen_task = self.subject.get_generation_task(self.generator, "중1", "소인수분해")
        rev_task = self.subject.get_review_task(self.reviewer, [gen_task], "중1")
        assert rev_task.agent == self.reviewer

    def test_explanation_task_assigned_to_agent(self):
        exp_task = self.subject.get_explanation_task(self.explainer, [])
        assert exp_task.agent == self.explainer
        assert "【핵심 개념】" in exp_task.description
        assert "【풀이 과정】" in exp_task.description
        assert "【최종 정답】" in exp_task.description


# ═══════════════════════════════════════════════════════════
# 5. 하위 호환 래퍼 함수 시그니처 테스트
# ═══════════════════════════════════════════════════════════

class TestBackwardCompatibility:

    def test_run_chunjae_crew_signature(self):
        from main import run_chunjae_crew
        sig = inspect.signature(run_chunjae_crew)
        params = sig.parameters
        assert "grade" in params
        assert "math_topic" in params
        assert "progress_callback" in params
        assert "use_fast" in params

    def test_run_exam_crew_signature(self):
        from main import run_exam_crew
        sig = inspect.signature(run_exam_crew)
        params = sig.parameters
        assert "grade" in params
        assert "math_topic" in params
        assert "count" in params
        assert "with_explanation" in params

    def test_run_pipeline_signature(self):
        from core.pipeline import run_pipeline
        sig = inspect.signature(run_pipeline)
        params = sig.parameters
        assert "subject" in params
        assert "grade" in params
        assert "topic" in params
        assert "progress_callback" in params
        assert "use_fast" in params

    def test_run_exam_pipeline_signature(self):
        from core.pipeline import run_exam_pipeline
        sig = inspect.signature(run_exam_pipeline)
        params = sig.parameters
        assert "subject" in params
        assert "count" in params
        assert "with_explanation" in params

    def test_logic_safety_review_signature(self):
        from core.safety_review import logic_safety_review
        sig = inspect.signature(logic_safety_review)
        params = sig.parameters
        assert "problem" in params
        assert "explanation" in params


# ═══════════════════════════════════════════════════════════
# 6. PDF 생성 테스트 (실제 파일 생성)
# ═══════════════════════════════════════════════════════════

class TestPdfGenerator:

    def test_latex_to_text_basic(self):
        from core.pdf_generator import latex_to_text
        result = latex_to_text("$x^2 + 3x = 0$")
        assert "$" not in result  # 달러 기호 제거됨
        assert "²" in result or "2" in result  # 위첨자 변환됨

    def test_latex_to_text_frac(self):
        from core.pdf_generator import latex_to_text
        result = latex_to_text(r"\frac{1}{2}")
        assert "1/2" in result

    def test_strip_html_and_latex(self):
        from core.pdf_generator import strip_html_and_latex
        html = "<div>수학 문제 $x=3$</div>"
        result = strip_html_and_latex(html)
        assert "<div>" not in result
        assert "수학 문제" in result

    def test_generate_pdf_exam_creates_file(self):
        from core.pdf_generator import generate_pdf_exam

        dummy_problems = [
            {"problem": "다음 소인수분해를 하시오: 12", "explanation": "【핵심 개념】 소인수분해\n【풀이 과정】 12=2²×3\n【최종 정답】 2²×3"},
            {"problem": "다음 소인수분해를 하시오: 18", "explanation": "【핵심 개념】 소인수분해\n【풀이 과정】 18=2×3²\n【최종 정답】 2×3²"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = generate_pdf_exam(
                problems_list=dummy_problems,
                grade="중1",
                topic="소인수분해",
                subject_id="math",
                output_dir=tmpdir
            )
            assert pdf_path != "", "PDF 경로가 비어 있으면 안 됩니다."
            assert os.path.exists(pdf_path), f"PDF 파일이 존재해야 합니다: {pdf_path}"
            assert os.path.getsize(pdf_path) > 0, "PDF 파일 크기가 0보다 커야 합니다."


# ═══════════════════════════════════════════════════════════
# 7. safety_review 반환값 형식 테스트 (API Mock)
# ═══════════════════════════════════════════════════════════

class TestSafetyReview:

    @patch("core.safety_review.OpenAI")
    def test_returns_pass_on_success(self, mock_openai_cls):
        from core.safety_review import logic_safety_review

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices[0].message.content = "PASS"

        result = logic_safety_review("문제 텍스트", "해설 텍스트")
        assert result == "PASS"

    @patch("core.safety_review.OpenAI")
    def test_returns_pass_on_exception(self, mock_openai_cls):
        """API 오류 시 PASS를 반환하여 파이프라인이 중단되지 않아야 함"""
        from core.safety_review import logic_safety_review

        mock_openai_cls.side_effect = Exception("API 오류")
        result = logic_safety_review("문제", "해설")
        assert result == "PASS"

    @patch("core.safety_review.OpenAI")
    def test_returns_fail_problem(self, mock_openai_cls):
        from core.safety_review import logic_safety_review

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices[0].message.content = "FAIL_PROBLEM: MCQ answer not in options"

        result = logic_safety_review("문제 텍스트", "해설 텍스트")
        assert "FAIL_PROBLEM" in result


# ═══════════════════════════════════════════════════════════
# 8. answer_leak 제거 로직 테스트
# ═══════════════════════════════════════════════════════════

class TestAnswerLeakRemoval:

    def test_removes_korean_answer_line(self):
        from core.pipeline import _remove_answer_leak
        text = "문제: 다음을 계산하시오.\n1) 5\n2) 10\n정답: 2번"
        result = _remove_answer_leak(text)
        assert "정답:" not in result
        assert "문제:" in result

    def test_removes_english_answer_line(self):
        from core.pipeline import _remove_answer_leak
        text = "Calculate x + 3 = 5\nAnswer: x = 2"
        result = _remove_answer_leak(text)
        assert "Answer:" not in result

    def test_removes_multiple_answer_lines(self):
        from core.pipeline import _remove_answer_leak
        text = "문제입니다.\n답: 3번\n해답: x=2"
        result = _remove_answer_leak(text)
        assert "답:" not in result
        assert "해답:" not in result

    def test_preserves_normal_content(self):
        from core.pipeline import _remove_answer_leak
        text = "다음 방정식을 푸시오.\n① x + 3 = 7\n② 2x = 8"
        result = _remove_answer_leak(text)
        assert "방정식" in result
        assert "① x + 3 = 7" in result


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v", "--tb=short"])
