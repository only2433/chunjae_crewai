"""
subjects/base.py
────────────────
모든 과목 플러그인이 구현해야 하는 추상 인터페이스(SubjectBase).

새 과목을 추가할 때는 이 클래스를 상속하고
7개의 추상 메서드를 모두 구현해야 합니다.

사용 예:
    from subjects.math import MathSubject
    subject = MathSubject()
    agent = subject.get_generator_agent()
"""

from abc import ABC, abstractmethod


class SubjectBase(ABC):
    """과목 플러그인 추상 기반 클래스."""

    # ── 과목 메타데이터 ────────────────────────────────────────────

    @property
    @abstractmethod
    def subject_id(self) -> str:
        """과목 식별자 (소문자 영어). e.g. 'math', 'english'"""
        pass

    @property
    @abstractmethod
    def label(self) -> str:
        """UI 표시명 (한국어). e.g. '수학', '영어'"""
        pass

    # ── 에이전트 팩토리 ──────────────────────────────────────────

    @abstractmethod
    def get_generator_agent(self, use_fast: bool = False):
        """
        문제 출제 에이전트를 반환합니다.

        Args:
            use_fast: True이면 GPT(빠른 모드), False이면 로컬 모델 사용.
        Returns:
            crewai.Agent 인스턴스
        """
        pass

    @abstractmethod
    def get_reviewer_agent(self):
        """
        문제 검수 에이전트를 반환합니다.
        검수는 항상 GPT를 사용합니다.

        Returns:
            crewai.Agent 인스턴스
        """
        pass

    @abstractmethod
    def get_explainer_agent(self, use_fast: bool = False):
        """
        해설 작성 에이전트를 반환합니다.

        Args:
            use_fast: True이면 GPT(빠른 모드), False이면 로컬 모델 사용.
        Returns:
            crewai.Agent 인스턴스
        """
        pass

    # ── 태스크 팩토리 ────────────────────────────────────────────

    @abstractmethod
    def get_generation_task(self, agent, grade: str, topic: str, variety_hint: str = "", generated_so_far: list = None):
        """
        문제 출제 태스크를 반환합니다.

        Args:
            agent: 출제 에이전트 인스턴스
            grade: 학년. e.g. '중1', '고2'
            topic: 단원/주제. e.g. '소인수분해', '관계대명사'
            variety_hint: 문제 유형 힌트 (시험지 순환용). e.g. '계산형', '독해형'
            generated_so_far: 이미 생성된 문제 텍스트 목록 (중복 방지용)
        Returns:
            crewai.Task 인스턴스
        """
        pass

    @abstractmethod
    def get_review_task(self, agent, context_tasks: list, grade: str, generated_so_far: list = None):
        """
        문제 검수 태스크를 반환합니다.

        Args:
            agent: 검수 에이전트 인스턴스
            context_tasks: 이전 태스크 목록 (출제 태스크 포함)
            grade: 학년
            generated_so_far: 이미 생성된 문제 텍스트 목록 (중복 및 오류 검수용)
        Returns:
            crewai.Task 인스턴스
        """
        pass

    @abstractmethod
    def get_explanation_task(self, agent, context_tasks: list):
        """
        해설 작성 태스크를 반환합니다.

        Args:
            agent: 해설 에이전트 인스턴스
            context_tasks: 이전 태스크 목록 (검수 태스크 포함)
        Returns:
            crewai.Task 인스턴스
        """
        pass

    # ── 다양성 힌트 ─────────────────────────────────────────────

    @abstractmethod
    def get_variety_hints(self) -> list:
        """
        시험지 일괄 생성 시 사용할 문제 유형 순환 힌트 목록을 반환합니다.

        Returns:
            list[str]: 힌트 문자열 목록 (순서대로 순환됨)
        
        예시 (수학):
            [
                "계산형: 수식을 바로 풀면 되는 순수 계산 문제로 만들어 주세요.",
                "문장제: 실생활 소재를 배경으로 한 이야기 문제로 만들어 주세요.",
                "도형형: 삼각형, 사각형 등 도형 문제로 만들어 주세요.",
            ]
        """
        pass
