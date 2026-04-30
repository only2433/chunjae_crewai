"""
subjects/math/tasks.py
───────────────────────
수학 과목 전용 태스크 프롬프트 정의.

[주의] 기존 루트의 tasks.py를 이 파일로 이관한 것입니다.
       기존 tasks.py는 하위 호환성을 위해 잠시 유지됩니다.
       새 코드는 반드시 이 파일을 import 하세요.

사용 예:
    from subjects.math.tasks import (
        problem_generation_task,
        review_task,
        explanation_task,
        explanation_review_task,
    )
"""

from crewai import Task


def problem_generation_task(agent, math_topic: str, grade: str, variety_hint: str = "", generated_so_far: list = None) -> Task:
    """수학 문제 출제 태스크를 반환합니다.

    Args:
        agent: 출제 에이전트 인스턴스
        math_topic: 수학 단원/주제
        grade: 학년 (e.g. '중1')
        variety_hint: 문제 소재 방향 힌트 (시험지 순환용)
        generated_so_far: 이미 생성된 문제 텍스트 목록 (중복 방지용)
    """
    variety_instruction = (
        f"\n[문제 소재 방향 - 반드시 따를 것]\n{variety_hint}"
    ) if variety_hint else ""

    # 이미 생성된 문제 목록을 프롬프트에 주입 (중복 방지)
    dedup_block = ""
    if generated_so_far:
        prev_list = "\n".join(
            f"  - {p[:120].strip()}..." for p in generated_so_far
        )
        dedup_block = (
            f"\n\n[ALREADY GENERATED - DO NOT DUPLICATE]\n"
            f"The following {len(generated_so_far)} problem(s) have already been created for this exam. "
            f"Your new problem MUST be on a DIFFERENT situation, scenario, and numbers:\n"
            f"{prev_list}\n"
            f"If your new problem is similar to ANY of the above (same situation, same numbers), REWRITE it completely."
        )

    return Task(
        description=(
            f"You must write exactly ONE middle school {grade} math problem on the topic '{math_topic}'.\n\n"
            f"[FORM - RANDOMLY CHOOSE ONE]\n"
            f"Randomly select either MULTIPLE_CHOICE (5 options) or SHORT_ANSWER.\n"
            f"- If MULTIPLE_CHOICE: provide exactly 5 answer choices. You MUST label them with circled numbers ①, ②, ③, ④, ⑤. Do NOT use 1. 2. 3. 4. 5.\n"
            f"  Example format:\n"
            f"  ① Option 1\n  ② Option 2\n  ③ Option 3\n  ④ Option 4\n  ⑤ Option 5\n"
            f"- If SHORT_ANSWER: only present the question clearly.\n\n"
            f"[STYLE] Write in Korean. Use concise textbook style (like Chunjae Edu). No childish storytelling.\n"
            f"[COUNT] Only 1 question. No sub-questions.\n"
            f"[UNITS] No commas between numbers and units. e.g. 5cm (O), 5, cm (X)\n"
            f"[MATH NOTATION] ALL mathematical formulas, fractions, and expressions MUST be wrapped in LaTeX delimiters $...$.\n"
            f"  e.g., Do NOT write (\\frac{{25\\pi}}{{3}}). You MUST write $\\frac{{25\\pi}}{{3}}$.\n"
            f"  Use standard Korean notation for recurring decimals using LaTeX dots, e.g., $0.\\dot{{5}}$ or $0.\\dot{{1}}2\\dot{{3}}$. Do NOT use parentheses like $0.2(5)$.\n"
            f"[RESTRICTION] EXTREMELY IMPORTANT: Do NOT include the answer, hints, or calculation steps in the problem text itself. The problem must ONLY present the question and the choices. If you reveal the answer or say '호의 길이는 ~ 입니다' inside the problem description, the entire test becomes invalid.\n"
            f"[LANGUAGE] Write 100% in Korean."
            f"{variety_instruction}"
            f"{dedup_block}"
        ),
        expected_output=f"One Korean middle school math problem in either multiple-choice (with 5 options) or short-answer format.",
        agent=agent
    )


def review_task(agent, context_tasks: list, grade: str) -> Task:
    """수학 문제 검수 태스크를 반환합니다.

    Args:
        agent: 검수 에이전트 인스턴스
        context_tasks: 이전 태스크 목록 (출제 태스크 포함)
        grade: 학년
    """
    return Task(
        description=(
            f"You are reviewing a math problem created by a local AI. Assume it contains errors. Follow ALL steps below.\n\n"

            f"=== STEP 1: SOLVE THE PROBLEM YOURSELF ===\n"
            f"Read the problem carefully. Calculate the correct answer yourself, step by step.\n"
            f"Write down each calculation step internally to verify you have the right answer.\n\n"

            f"=== STEP 2: VALIDATE THE PROBLEM ===\n"
            f"Check these issues (fix them if found):\n"
            f"A) SELF-CONTRADICTION: Does the question ask for a value already stated in the problem?\n"
            f"   e.g. 'Minsoo HAS 5 candies... How many does Minsoo have?' → REWRITE the problem.\n"
            f"B) NUMERICAL INCONSISTENCY: Do all numbers in the problem agree with each other?\n"
            f"   e.g. 'A=5, B=8, total=20' but 5+8=13≠20 → REWRITE the problem.\n"
            f"C) UNSOLVABLE: Are conditions missing or contradictory? → REWRITE the problem.\n\n"

            f"=== STEP 3: VERIFY MCQ OPTIONS (MOST CRITICAL) ===\n"
            f"If this is a multiple-choice problem with options 1~5:\n"
            f"- Your calculated answer from STEP 1: does it EXACTLY match one of the 5 options?\n"
            f"- If YES: proceed to output.\n"
            f"- If NO: you MUST rewrite the 5 options so that the correct answer is included.\n"
            f"  Do NOT change the problem itself - only fix the options.\n"
            f"  Make sure the 4 wrong options are plausible (not obviously wrong).\n\n"

            f"=== STEP 4: LEVEL & FORMAT CHECK ===\n"
            f"Confirm the problem is appropriate for middle school {grade} level.\n"
            f"Verify math notation: Recurring decimals MUST use dots over the digits (e.g. $0.\\dot{{5}}$ or $0.\\dot{{1}}\\dot{{2}}$). If it uses parentheses like $0.2(5)$, fix it to $0.2\\dot{{5}}$.\n"
            f"Remove any accidentally included answers, hints, or solutions.\n\n"

            f"=== OUTPUT FORMAT ===\n"
            f"Output ONLY the final corrected problem text.\n"
            f"If MCQ, include the corrected 5 options formatted with ①, ②, ③, ④, ⑤.\n"
            f"CRITICAL: If the problem text contains any answer disclosure (e.g. '정답:', '답:', 'Answer:', '해답:', '호의 길이는 ~ 입니다', '넓이는 ~ 입니다'),\n"
            f"DELETE that line entirely. The problem output must NEVER contain the answer or calculation steps inside the problem description.\n"
            f"CRITICAL MATH NOTATION: Ensure ALL LaTeX like \\frac is properly wrapped in $...$.\n"
            f"Do NOT include your calculation process or review comments in the output."
        ),
        expected_output=(
            "The final, corrected Korean math problem with verified MCQ options "
            "(if applicable). No review commentary, no calculation steps shown."
        ),
        agent=agent,
        context=context_tasks
    )


def explanation_task(agent, context_tasks: list) -> Task:
    """수학 해설 작성 태스크를 반환합니다.

    Args:
        agent: 해설 에이전트 인스턴스
        context_tasks: 이전 태스크 목록 (검수 태스크 포함)
    """
    return Task(
        description=(
            "Write a structured and visually clear explanation for the confirmed math problem.\n\n"
            "You MUST use EXACTLY the following 3 section markers in order:\n\n"
            "【핵심 개념】\n"
            "(Write 1~3 sentences explaining the key formula or rule needed to solve this problem.)\n\n"
            "【풀이 과정】\n"
            "(Write step-by-step calculation. Use ① ② ③ for each step. Max 6 steps.\n"
            " Each step on its own line. Do NOT repeat steps. Do NOT second-guess or write meta-commentary.\n"
            " Example format:\n"
            " ① 주어진 조건 정리: $2x + 4 = 10$\n"
            " ② 이항: $2x = 10 - 4 = 6$\n"
            " ③ 양변을 2로 나누면: $x = 3$)\n\n"
            "【최종 정답】\n"
            "(State the answer clearly. For MCQ, write the option number AND value. e.g. '② x = 3')\n\n"
            "[STRICT PROHIBITIONS]\n"
            "- NEVER write greetings, meta-commentary, or self-doubt ('I think there may be an error', 'Let me reconsider').\n"
            "- NEVER skip the section markers 【핵심 개념】 【풀이 과정】 【최종 정답】.\n"
            "- NEVER write more than 12 lines total.\n\n"
            "[LANGUAGE] 100% Korean only.\n"
            "[MATH] All formulas must use LaTeX syntax ($...$). Recurring decimals MUST use \\dot{{}} (e.g., $0.\\dot{{5}}$), NOT parentheses.\n"
            "[UNITS] No English units. Use $cm^2$, $cm^3$ etc."
        ),
        expected_output=(
            "A structured Korean explanation with exactly 3 sections marked as "
            "【핵심 개념】, 【풀이 과정】, and 【최종 정답】."
        ),
        agent=agent,
        context=context_tasks
    )


def explanation_review_task(agent, context_tasks: list) -> Task:
    """해설 교정 태스크를 반환합니다 (해설 검수 전용).

    Args:
        agent: 검수 에이전트 인스턴스
        context_tasks: 이전 태스크 목록
    """
    return Task(
        description=(
            "Proofread the explanation text written by the explainer agent.\n"
            "1. Fix any leftover LaTeX symbol artifacts.\n"
            "2. Correct any foreign language text or typos (hallucination symptoms).\n"
            "3. Verify the answer is correct by recalculating. Fix if wrong.\n"
            "[OUTPUT RULE] Output ONLY the corrected final explanation text. No review comments."
        ),
        expected_output="Clean, natural Korean explanation text with all errors corrected.",
        agent=agent,
        context=context_tasks
    )
