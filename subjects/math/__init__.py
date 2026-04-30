"""
subjects/math/__init__.py  (MathSubject 클래스)
────────────────────────────────────────────────
SubjectBase를 구현한 수학 과목 플러그인.

사용 예:
    from subjects.math import MathSubject

    subject = MathSubject()
    generator = subject.get_generator_agent()
    task      = subject.get_generation_task(generator, grade="중1", topic="소인수분해")
"""

import json
import os
from subjects.base import SubjectBase
from subjects.math.agents import (
    create_generator_agent,
    create_reviewer_agent,
    create_explainer_agent,
)
from subjects.math.tasks import (
    problem_generation_task,
    review_task,
    explanation_task,
    explanation_review_task,
)


class MathSubject(SubjectBase):
    """수학 과목 플러그인."""

    def __init__(self):
        _cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(_cfg_path, encoding="utf-8") as f:
            self._config = json.load(f)

    # ── 메타데이터 ────────────────────────────────────────────────

    @property
    def subject_id(self) -> str:
        return self._config["subject_id"]  # "math"

    @property
    def label(self) -> str:
        return self._config["label"]  # "수학"

    @property
    def config(self) -> dict:
        """config.json 전체 데이터를 반환합니다."""
        return self._config

    # ── 에이전트 팩토리 ──────────────────────────────────────────

    def get_generator_agent(self, use_fast: bool = False):
        return create_generator_agent(use_fast=use_fast)

    def get_reviewer_agent(self):
        return create_reviewer_agent()

    def get_explainer_agent(self, use_fast: bool = False):
        return create_explainer_agent(use_fast=use_fast)

    # ── 태스크 팩토리 ────────────────────────────────────────────

    def get_generation_task(self, agent, grade: str, topic: str, variety_hint: str = "", generated_so_far: list = None):
        return problem_generation_task(agent, topic, grade, variety_hint=variety_hint, generated_so_far=generated_so_far)

    def get_review_task(self, agent, context_tasks: list, grade: str, generated_so_far: list = None):
        return review_task(agent, context_tasks, grade)

    def get_explanation_task(self, agent, context_tasks: list):
        return explanation_task(agent, context_tasks)

    def get_explanation_review_task(self, agent, context_tasks: list):
        """해설 교정 태스크 (수학 전용 확장 메서드)."""
        return explanation_review_task(agent, context_tasks)

    # ── 다양성 힌트 ─────────────────────────────────────────────

    def get_variety_hints(self) -> list:
        return [
            "계산형: 수식을 바로 풀면 되는 순수 계산 문제로 만들어 주세요.",
            "문장제: 실생활 소재(물건 구매, 속력, 나이 등)를 배경으로 한 이야기 문제로 만들어 주세요.",
            "도형형: 삼각형, 사각형 등 도형의 넓이·둘레·각도를 소재로 한 문제로 만들어 주세요.",
        ]
