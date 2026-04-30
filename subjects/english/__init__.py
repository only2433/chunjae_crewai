"""
subjects/english/__init__.py  (EnglishSubject 클래스)
──────────────────────────────────────────────────────
SubjectBase를 구현한 영어 과목 플러그인.

사용 예:
    from subjects.english import EnglishSubject

    subject = EnglishSubject()
    generator = subject.get_generator_agent()
    task = subject.get_generation_task(generator, grade="중3", topic="관계대명사")
"""

import json
import os
from subjects.base import SubjectBase
from subjects.english.agents import (
    create_generator_agent,
    create_reviewer_agent,
    create_explainer_agent,
)
from subjects.english.tasks import (
    problem_generation_task,
    review_task,
    explanation_task,
)


class EnglishSubject(SubjectBase):
    """영어 과목 플러그인."""

    def __init__(self):
        _cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(_cfg_path, encoding="utf-8") as f:
            self._config = json.load(f)

    # ── 메타데이터 ────────────────────────────────────────────────

    @property
    def subject_id(self) -> str:
        return self._config["subject_id"]  # "english"

    @property
    def label(self) -> str:
        return self._config["label"]  # "영어"

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
        return review_task(agent, context_tasks, grade, generated_so_far)

    def get_explanation_task(self, agent, context_tasks: list):
        return explanation_task(agent, context_tasks)

    # ── 다양성 힌트 ─────────────────────────────────────────────

    def get_variety_hints(self) -> list:
        return [
            "문법형: 문법 규칙(어형 변화, 어순, 시제 등)을 직접 묻는 문제로 만들어 주세요. "
            "빈칸에 들어갈 알맞은 형태의 단어를 고르는 유형이 대표적입니다.",

            "어휘형: 주어진 문장의 문맥에 맞는 단어/숙어를 고르는 문제로 만들어 주세요. "
            "동의어 교체 또는 빈칸 완성 형태를 활용하세요.",

            "독해형: 3~5문장의 짧은 영어 지문을 제시하고, 주제·요지·세부내용·빈칸 추론 중 "
            "하나를 묻는 문제로 만들어 주세요.",
        ]
