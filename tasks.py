"""
tasks.py (루트) — 하위 호환성 래퍼
────────────────────────────────────
[경고] 이 파일은 Phase 1 리팩토링으로 인해 더 이상 직접 사용하지 않습니다.
       실제 구현은 subjects/math/tasks.py 로 이관되었습니다.

       이 파일은 기존 외부 임포트 코드와의 호환성을 위해 유지합니다.
       새 코드는 반드시 subjects/math/tasks.py 를 import 하세요.
"""

# subjects/math/tasks.py 로 위임 (re-export)
from subjects.math.tasks import (
    problem_generation_task,
    review_task,
    explanation_task,
    explanation_review_task,
)

__all__ = [
    "problem_generation_task",
    "review_task",
    "explanation_task",
    "explanation_review_task",
]
