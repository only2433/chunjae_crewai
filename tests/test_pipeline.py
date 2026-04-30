"""
tests/test_pipeline.py
───────────────────────
수학 파이프라인 기본 동작 검증 (레거시 호환 테스트).

[업데이트 이력]
- Phase 1 이전: 루트 agents.py/tasks.py 직접 호출
- Phase 2 이후: subjects/math/ 플러그인 구조로 이관
- 현재 (Phase 3): subjects 레지스트리 팩토리 패턴 사용
"""

import sys
import os
import pytest
from unittest.mock import patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# 현재 구조: subjects/math/ 플러그인 사용
from subjects.math.agents import create_generator_agent, create_reviewer_agent, create_explainer_agent
from subjects.math.tasks import problem_generation_task, review_task, explanation_task
from crewai import Crew


def test_agent_initialization():
    """에이전트들이 정상적으로 생성되고 역할이 매핑되었는지 테스트"""
    g_agent = create_generator_agent()
    r_agent = create_reviewer_agent()
    e_agent = create_explainer_agent()

    # 수학 에이전트 역할 검증
    assert "수학" in g_agent.role or "출제" in g_agent.role or "math" in g_agent.role.lower()
    assert (
        "감수" in r_agent.role
        or "검수" in r_agent.role
        or "검증" in r_agent.role
        or "reviewer" in r_agent.role.lower()
    )
    assert "해설" in e_agent.role or "explainer" in e_agent.role.lower()

    assert g_agent.llm is not None


def test_task_pipeline_setup():
    """태스크들이 정상적으로 생성되고 에이전트와 연결되었는지 테스트"""
    g_agent = create_generator_agent()
    # Phase 2 이후: grade 파라미터 필수
    task1 = problem_generation_task(g_agent, "분수의 덧셈", grade="중1")

    assert task1.agent == g_agent
    assert "분수의 덧셈" in task1.description


@patch('crewai.Crew.kickoff')
def test_crew_orchestration(mock_kickoff):
    """크루 조립 및 kickoff 호출 검증 테스트 (LLM 요금을 방지하기 위해 Mock 처리)"""
    mock_kickoff.return_value = "Mocked 팩트체크 완료 및 해설 산출물"

    g_agent = create_generator_agent()
    r_agent = create_reviewer_agent()
    e_agent = create_explainer_agent()

    task1 = problem_generation_task(g_agent, "테스트 서브젝트", grade="중1")
    task2 = review_task(r_agent, [task1], grade="중1")
    task3 = explanation_task(e_agent, [task2])

    crew = Crew(
        agents=[g_agent, r_agent, e_agent],
        tasks=[task1, task2, task3]
    )

    result = str(crew.kickoff())
    assert mock_kickoff.called
    assert "Mocked" in result
