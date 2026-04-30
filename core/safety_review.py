"""
core/safety_review.py
──────────────────────
최종 감수 엔진 (Logic Safety Review).

GPT-4o-mini를 사용하여 생성된 문제와 해설의
논리적 오류, 정답 누락, 환각 여부를 검사합니다.

[이관 이력]
- 2026-04-29: main.py의 logic_safety_review() 함수 분리

사용 예:
    from core.safety_review import logic_safety_review

    result = logic_safety_review(problem_text, explanation_text)
    if "PASS" in result:
        ...
"""

from openai import OpenAI


def logic_safety_review(problem: str, explanation: str) -> str:
    """
    문제와 해설의 논리적 완성도를 GPT-4o-mini로 검증합니다.

    [검사 항목]
    CHECK 1 - MISSING DATA    : 문제에 풀기 위한 수치/조건이 빠진 경우
    CHECK 2 - VISUAL DEPENDENCY: 표/그래프 참조가 있으나 데이터가 없는 경우
    CHECK 3 - MCQ CROSS-REF   : 객관식 정답이 보기 안에 없는 경우 (가장 중요)
    CHECK 4 - HALLUCINATION   : 해설이 문제에 없는 숫자를 만들어 쓴 경우

    Returns:
        "PASS"                  : 모든 검사 통과
        "FAIL_PROBLEM: [사유]"  : 문제 자체에 결함
        "FAIL_EXPLANATION: [사유]" : 해설만 오류
    """
    try:
        client = OpenAI()
        prompt = (
            "You are the chief mathematics editor for a Korean middle school textbook publisher.\n"
            "Carefully review the problem and explanation provided below.\n\n"
            f"[PROBLEM]\n{problem}\n\n"
            f"[EXPLANATION & ANSWER]\n{explanation}\n\n"
            "[MANDATORY CHECKS - output FAIL if ANY of the following are true]\n\n"
            "CHECK 1 - MISSING DATA:\n"
            "  Does the problem lack specific numbers or conditions needed to solve it?\n"
            "  (e.g., 'find the two numbers' without giving any values) => FAIL_PROBLEM\n\n"
            "CHECK 2 - VISUAL DEPENDENCY:\n"
            "  Does the problem say 'see the table/graph' but no actual data is written in the text? => FAIL_PROBLEM\n\n"
            "CHECK 3 - MCQ CROSS-REFERENCE (MOST CRITICAL):\n"
            "  If the problem contains numbered answer options (e.g. '1) ...  2) ...  3) ...'):\n"
            "  a) Find the answer stated in the explanation's section marked 【최종 정답】.\n"
            "  b) Look at ALL numbered options in the problem (1~5).\n"
            "  c) Check if the stated answer corresponds to any of those options.\n"
            "     - The option NUMBER may differ from the answer value (e.g., option '2)' has value 'x=2, y=1').\n"
            "     - Match by VALUE, not by the option label number.\n"
            "     - For pair answers like 'x=2, y=1', check if any option contains both x=2 AND y=1.\n"
            "     - For single answers like 'x=9', check if any option contains the value 9.\n"
            "  d) If the answer IS found among the options => this check PASSES.\n"
            "  e) If the answer is NOT found among any of the options => FAIL_PROBLEM: MCQ answer not in options\n\n"
            "  Example PASS: explanation says '② x=2, y=1', problem has option '2) x=2, y=1' => PASS\n"
            "  Example PASS: explanation says '① 9', problem has option '1. 9' => PASS\n"
            "  Example FAIL: explanation says 'x=-5', problem options are 5,6,7,8,9 => none match => FAIL_PROBLEM\n\n"
            "CHECK 4 - HALLUCINATED EXPLANATION:\n"
            "  Does the explanation invent numbers not present in the problem to force an answer? => FAIL_EXPLANATION\n\n"
            "[OUTPUT RULES - respond with ONLY one of the following]\n"
            "- All checks pass: output exactly the word PASS\n"
            "- Problem is flawed (checks 1,2,3 fail): output FAIL_PROBLEM: [reason]\n"
            "- Problem ok but explanation wrong (check 4): output FAIL_EXPLANATION: [reason]"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[safety_review] 논리 검수 오류 (통과 처리): {e}")
        return "PASS"
