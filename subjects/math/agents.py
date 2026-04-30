"""
subjects/math/agents.py
────────────────────────
수학 과목 전용 에이전트 페르소나 정의.

[주의] 기존 루트의 agents.py를 이 파일로 이관한 것입니다.
       기존 agents.py는 하위 호환성을 위해 잠시 유지됩니다.
       새 코드는 반드시 이 파일을 import 하세요.

사용 예:
    from subjects.math.agents import create_generator_agent, create_reviewer_agent, create_explainer_agent
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from crewai import Agent
from config.llm_config import local_qwen_llm, reviewer_llm, fast_llm, explainer_llm


def create_generator_agent(use_fast: bool = False) -> Agent:
    """수학 문제 출제 에이전트를 생성합니다.

    Args:
        use_fast: True이면 gpt-4o-mini(빠른 모드), False이면 qwen3:4b(로컬) 사용.
    """
    llm = fast_llm if use_fast else local_qwen_llm
    label = "GPT (빠른 모드)" if use_fast else "로컬 모델"
    return Agent(
        role="중학 수학 교과서/문제집 출제 마스터",
        goal="주어진 단원과 성취 기준에 맞추어 시중 수학익힘책 스타일의 간결하고 정확한 실전 수학 문항 1개 생성",
        backstory=(
            "당신은 대한민국 천재교육 중학 교과서 개발팀의 수석 집필진입니다. "
            "유치한 동화책 스타일이나 억지스러운 대화체를 극도로 혐오하며, "
            "오직 수학적 사고력만을 묻는 명확, 간결, 깔끔한 실전형 문제만을 집필합니다."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm  # use_fast=True → gpt-4o-mini, False → qwen3:4b
    )


def create_reviewer_agent() -> Agent:
    """수학 문제 검수 에이전트를 생성합니다. 항상 GPT를 사용합니다."""
    return Agent(
        role="수학 검증 전문가 및 문제 교정관",
        goal=(
            "로컬 AI가 생성한 수학 문제를 받아 반드시 직접 끝까지 풀어보고, "
            "① 문제가 논리적으로 성립하는지, "
            "② 객관식인 경우 계산한 정답이 보기 5개 안에 실제로 포함되어 있는지 "
            "수학적으로 엄밀하게 검증한 뒤, 오류가 있으면 즉시 수정하여 완벽한 문제로 교정"
        ),
        backstory=(
            "당신은 대한민국 수능 출제 경력 20년의 베테랑 수학 검증 위원입니다. "
            "AI가 만든 문제는 반드시 오류가 있다고 가정하고 시작합니다. "
            "객관식 문제를 받으면 가장 먼저 직접 계산하여 정답을 구하고, "
            "그 정답이 1~5번 보기 중 어디에 있는지 확인합니다. "
            "보기에 정답이 없으면 보기를 즉시 수정합니다. "
            "문제가 답을 이미 지문에 포함하거나(자기모순), 숫자가 서로 맞지 않으면(수치 불일치) 문제 전체를 재작성합니다. "
            "절대 불완전한 문제를 통과시키지 않습니다."
        ),
        verbose=True,
        allow_delegation=False,
        llm=reviewer_llm  # 검수는 항상 GPT
    )


def create_explainer_agent(use_fast: bool = False) -> Agent:
    """수학 해설 작성 에이전트를 생성합니다.

    Args:
        use_fast: True이면 gpt-4o-mini(빠른 모드), False이면 해설 전용 로컬 모델 사용.
    """
    llm = fast_llm if use_fast else explainer_llm  # 해설 전용 LLM (temperature=0.5)
    return Agent(
        role="친절한 오답노트 해설가",
        goal="감수를 통과하여 확정된 수학 문제를 보고, 중학생 눈높이에 맞춘 핵심 개념 + 풀이 과정 + 최종 정답을 간결하게 3단계로 정리",
        backstory=(
            "당신은 밀크T 중학의 스타 강사입니다. "
            "군더더기 없이 핵심만 짚어 주는 명쾌한 2~3단계 해설을 씁니다. "
            "불필요한 인사말이나 반복 설명 없이 바로 풀이로 들어갑니다."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm
    )
