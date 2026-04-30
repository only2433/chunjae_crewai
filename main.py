"""
main.py — 진입점 & 하위 호환성 래퍼
──────────────────────────────────────
[Phase 2 리팩토링 이후]

실제 비즈니스 로직은 모두 core/ 와 subjects/ 로 이관되었습니다.
이 파일은 아래 두 가지 역할만 수행합니다:

1. **진입점**: `python main.py` 직접 실행 시 수학 단일 문제 생성 테스트
2. **하위 호환 래퍼**: gui.py 가 `run_chunjae_crew`, `run_exam_crew`를
   `main.py`에서 import 하므로, 해당 함수를 re-export 합니다.

[이관 내역]
- logic_safety_review()  → core/safety_review.py
- generate_pdf_exam()    → core/pdf_generator.py
- run_chunjae_crew()     → core/pipeline.py :: run_pipeline()
- run_exam_crew()        → core/pipeline.py :: run_exam_pipeline()
- run_python_illustrator() → core/pipeline.py (내부 함수)
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from subjects.math import MathSubject
from core.pipeline import run_pipeline, run_exam_pipeline
from core.safety_review import logic_safety_review       # 하위 호환
from core.pdf_generator import generate_pdf_exam          # 하위 호환


# ── 하위 호환 래퍼 함수 (gui.py 가 이 이름으로 import) ──────────────────────

def run_chunjae_crew(grade="중1", math_topic="소인수분해", progress_callback=None, use_fast=False):
    """
    [하위 호환 래퍼]
    내부적으로 core.pipeline.run_pipeline(MathSubject(), ...) 을 호출합니다.
    """
    subject = MathSubject()
    return run_pipeline(
        subject=subject,
        grade=grade,
        topic=math_topic,
        progress_callback=progress_callback,
        use_fast=use_fast
    )


def run_exam_crew(grade="중1", math_topic="소인수분해", count=10,
                  progress_callback=None, with_explanation=False, use_fast=False):
    """
    [하위 호환 래퍼]
    내부적으로 core.pipeline.run_exam_pipeline(MathSubject(), ...) 을 호출합니다.
    """
    subject = MathSubject()
    return run_exam_pipeline(
        subject=subject,
        grade=grade,
        topic=math_topic,
        count=count,
        progress_callback=progress_callback,
        with_explanation=with_explanation,
        use_fast=use_fast
    )


# ── 직접 실행 시 테스트 ──────────────────────────────────────────────────────

if __name__ == "__main__":
    res = run_chunjae_crew("중1", "소인수분해")
    print("\n문제:\n", res.get("problem"))
    print("\n해설:\n", res.get("explanation"))
