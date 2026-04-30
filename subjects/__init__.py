"""
subjects/__init__.py  — 과목 레지스트리 & 팩토리
───────────────────────────────────────────────────
새 과목 플러그인을 이 레지스트리에 등록하면
gui.py와 pipeline.py가 자동으로 인식합니다.

사용 예:
    from subjects import get_subject, list_subjects

    subject = get_subject("math")    # MathSubject()
    subject = get_subject("english") # EnglishSubject()

    all_ids = list_subjects()        # ["math", "english"]
"""

from subjects.math import MathSubject
from subjects.english import EnglishSubject

# ── 레지스트리: subject_id → Subject 클래스 ────────────────────────────────
# 새 과목 추가 시: 이 딕셔너리에만 등록하면 됩니다.
_REGISTRY = {
    "math":    MathSubject,
    "english": EnglishSubject,
    # "science": ScienceSubject,  # Phase 4 예정
}


def get_subject(subject_id: str):
    """
    subject_id에 해당하는 SubjectBase 인스턴스를 반환합니다.

    Args:
        subject_id: "math" | "english"

    Returns:
        SubjectBase 구현체 인스턴스

    Raises:
        ValueError: 등록되지 않은 subject_id인 경우
    """
    cls = _REGISTRY.get(subject_id)
    if cls is None:
        raise ValueError(
            f"알 수 없는 과목 ID: '{subject_id}'. "
            f"사용 가능한 과목: {list(_REGISTRY.keys())}"
        )
    return cls()


def list_subjects() -> list:
    """등록된 모든 subject_id 목록을 반환합니다."""
    return list(_REGISTRY.keys())
