"""
subjects/english/tasks.py
──────────────────────────
영어 과목 전용 태스크 프롬프트 정의.

[v2 주요 개선]
- 출제 태스크: 성별 모호성 금지 규칙 추가 (friend/teacher 단독 사용 시 대명사 문제 금지)
- 검수 태스크: STEP 3에 "성별 모호성" 전용 체크 추가 (GENDER AMBIGUITY CHECK)
- 검수 태스크: 보기 중복 정답 탐지 로직 강화
- 해설 태스크: "오답 보기가 왜 틀렸는가"를 반드시 포함하도록 강제

[태스크 구성]
- problem_generation_task : 문제 출제 (문법형/어휘형/독해형 순환)
- review_task             : 문제 검수 (원어민 감수 + 정답 보기 교차 검증)
- explanation_task        : 해설 작성 (어법 해설 + 오답 분석)
"""

from crewai import Task


def problem_generation_task(agent, topic: str, grade: str, variety_hint: str = "", generated_so_far: list = None) -> Task:
    """영어 문제 출제 태스크를 반환합니다.

    Args:
        agent: 출제 에이전트 인스턴스
        topic: 영어 단원/주제 (e.g. "관계대명사")
        grade: 학년 (e.g. "중3")
        variety_hint: 문제 유형 힌트 (문법형/어휘형/독해형 순환)
        generated_so_far: 이미 생성된 문제 텍스트 목록 (중복 방지용)
    """
    variety_instruction = (
        f"\n[문제 유형 지시 - 반드시 따를 것]\n{variety_hint}"
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
            f"Your new problem MUST use a COMPLETELY DIFFERENT sentence, scenario, and structure:\n"
            f"{prev_list}\n"
            f"If your new problem uses the same sentence pattern or the same key nouns as any above, REWRITE it."
        )

    return Task(
        description=(
            f"Create exactly ONE English multiple-choice problem for {grade} students "
            f"on the topic '{topic}'.\n\n"

            f"[PROBLEM FORMAT - MANDATORY]\n"
            f"Choose EITHER:\n"
            f"  A. MULTIPLE CHOICE (5 options): Write a question, then list 5 answer choices labeled ①②③④⑤.\n"
            f"  B. FILL-IN-THE-BLANK: Write an English sentence with ONE blank (____), "
            f"then provide 5 answer choices labeled ①②③④⑤.\n\n"
            
            f"[CRITICAL: BLANK RULE]\n"
            f"If you use FILL-IN-THE-BLANK, you MUST include EXACTLY ONE blank (____) where the answer should go.\n"
            f"DO NOT write the correct answer inside the sentence itself!\n"
            f"  BAD: 'This is my sister. Her name is Sarah.' (Answer is exposed!)\n"
            f"  GOOD: 'This is my sister. ____ name is Sarah.'\n\n"

            f"[STYLE RULES]\n"
            f"- Write the problem instructions (e.g. '다음 빈칸에 알맞은 것은?') in KOREAN.\n"
            f"- [CRITICAL] The actual sentences and passages to be solved MUST BE IN ENGLISH.\n"
            f"  DO NOT translate the English sentences into Korean!\n"
            f"  BAD: 'Minji는 테디베어를 가지고 있습니다.' (Korean sentence - FORBIDDEN!)\n"
            f"  GOOD: 'Minji has a teddy bear.' (English sentence - REQUIRED!)\n"
            f"- Language level: appropriate for Korean {grade} middle school students.\n"
            f"- Vocabulary: strictly within 2015 Korean middle school English curriculum.\n"
            f"- If using a reading passage, limit to 3-5 sentences maximum.\n"
            f"- Do NOT include the answer or hints in the problem.\n"
            f"- Do NOT write sub-questions. Only 1 question.\n\n"

            f"[GENDER CLARITY RULE - CRITICAL FOR PRONOUN QUESTIONS]\n"
            f"If the question involves selecting a possessive pronoun (his / her / their / its),\n"
            f"the sentence context MUST make gender 100% unambiguous.\n"
            f"FORBIDDEN: Using gender-neutral nouns (friend, teacher, student, classmate, person, doctor, neighbor)\n"
            f"ALONE as the antecedent for his/her choice.\n"
            f"Example of BAD problem (FORBIDDEN): 'This is my friend. ____ name is Alex.' → his or her BOTH valid!\n"
            f"Example of GOOD problem: 'This is my brother. ____ name is David.' → His only\n"
            f"Example of GOOD problem: 'This is Ms. Kim, my teacher. ____ class is fun.' → Her only\n"
            f"If you cannot clearly determine the gender from context, use 'their' or change the topic.\n\n"

            f"[MCQ SELF-CHECK BEFORE OUTPUT]\n"
            f"Before writing your answer, ask yourself:\n"
            f"  Q1. Are there TWO or more options that could BOTH be grammatically correct? If yes → REWRITE.\n"
            f"  Q2. Is the correct answer obviously the only right one? If not → REWRITE.\n"
            f"  Q3. Does the question context clearly support only ONE answer? If not → REWRITE.\n\n"

            f"[ABSOLUTE PROHIBITIONS]\n"
            f"- Never include the answer key (정답, 답, Answer:) in the problem text.\n"
            f"- Never use vocabulary beyond the grade level.\n"
            f"- All English text MUST be grammatically correct.\n"
            f"- Never create a pronoun fill-in-blank with an ambiguous gender antecedent.\n"
            f"- Never expose the correct answer inside the question sentence."
            f"{variety_instruction}"
        ),
        expected_output=(
            f"One Korean-instruction English problem for {grade} students. "
            f"If it is a pronoun question (his/her), the gender context MUST be unambiguous. "
            f"Format: multiple-choice or fill-in-the-blank with options ①②③④⑤. Ensure the blank (____) exists."
        ),
        agent=agent
    )


def review_task(agent, context_tasks: list, grade: str, generated_so_far: list = None) -> Task:
    """영어 문제 검수 태스크를 반환합니다.

    Args:
        agent: 검수 에이전트 인스턴스
        context_tasks: 이전 태스크 목록 (출제 태스크 포함)
        grade: 학년
        generated_so_far: 이미 생성된 문제 텍스트 목록 (중복 검사용)
    """
    dup_check = ""
    if generated_so_far:
        prev_list = "\n".join(f"  - {p[:120].strip()}..." for p in generated_so_far)
        dup_check = (
            f"\n\n=== STEP 0: DUPLICATION CHECK ===\n"
            f"Check if the problem is extremely similar or identical in structure/vocabulary "
            f"to any of these previously generated problems:\n{prev_list}\n"
            f"If it IS a duplicate, DO NOT fix it. Output exactly the word 'REJECT'.\n"
        )

    return Task(
        description=(
            f"You are a native English speaker and senior English education expert.\n"
            f"Review the English problem created for Korean {grade} middle school students.\n"
            f"Assume it CONTAINS errors. Be strict. Follow ALL steps below.\n"
            f"{dup_check}\n"
            f"=== STEP 1: GRAMMAR & SPELLING CHECK ===\n"
            f"Read every English word carefully.\n"
            f"Fix any grammar mistakes, spelling errors, or unnatural expressions.\n"
            f"If the problem is fundamentally flawed and cannot be fixed simply, output exactly the word 'REJECT'.\n\n"
            f"=== STEP 1.5: ENGLISH PASSAGE CHECK ===\n"
            f"The actual reading passage or sentences for the problem MUST be written in ENGLISH.\n"
            f"If the main problem sentences are written in Korean (e.g. 'Minji는 제 어린이입니다.'), output exactly the word 'REJECT'.\n\n"
            f"=== STEP 2: CURRICULUM LEVEL CHECK ===\n"
            f"Verify vocabulary and grammar structures are appropriate for {grade}.\n"
            f"Simplify if too advanced. Adjust if too simple for the topic.\n\n"
            f"=== STEP 3: GENDER AMBIGUITY CHECK (MOST CRITICAL FOR PRONOUN QUESTIONS) ===\n"
            f"If the problem asks students to choose a possessive pronoun (his / her / their / its):\n\n"
            f"  a) Identify the ANTECEDENT (the noun the blank refers to).\n"
            f"  b) Ask: Is the gender of this noun 100% clear from the sentence alone?\n"
            f"     - CLEAR MALE: brother, father, grandfather, Mr. [Name], uncle, king, son, husband\n"
            f"     - CLEAR FEMALE: sister, mother, grandmother, Ms./Mrs./Miss [Name], aunt, queen, daughter, wife\n"
            f"     - GENDER-NEUTRAL (AMBIGUOUS): friend, teacher, student, classmate, person, neighbor, doctor,\n"
            f"       cousin, child, colleague, manager, boss - these make 'his' AND 'her' BOTH valid!\n"
            f"  c) If the antecedent is gender-neutral AND the options include both 'his' and 'her':\n"
            f"     → MANDATORY FIX: Modify the sentence to make the gender explicit.\n"
            f"       Option 1: Replace the noun (e.g., 'friend' → 'sister')\n"
            f"       Option 2: Add a gender-clarifying name (e.g., 'friend Tom' or 'friend Sarah')\n"
            f"       Option 3: Use 'their' as the intended correct answer (gender-neutral singular)\n"
            f"     → Do NOT keep the problem as-is. Fix it. If you cannot fix it, output exactly the word 'REJECT'.\n\n"
            f"  EXAMPLES OF FORBIDDEN (must fix):\n"
            f"  BAD: 'This is my friend. ____ name is Alex.' (his OR her both valid)\n"
            f"  BAD: 'This is my teacher. ____ class is fun.' (teacher is gender-neutral)\n"
            f"  BAD: 'This is my cousin. ____ hobby is reading.' (cousin is gender-neutral)\n\n"
            f"  EXAMPLES OF ACCEPTABLE:\n"
            f"  GOOD: 'This is my brother. ____ name is David.' (brother = male → His only)\n"
            f"  GOOD: 'This is Ms. Kim. ____ class is fun.' (Ms. = female → Her only)\n"
            f"  GOOD: 'This is my friend Alex. ____ hobby is reading.' (name Alex contextually male → His)\n\n"
            f"=== STEP 4: MCQ UNIQUE ANSWER VERIFICATION ===\n"
            f"For multiple-choice with options ①②③④⑤:\n"
            f"  a) Determine the ONE correct answer yourself, independently.\n"
            f"  b) Verify ONLY ONE of the 5 options is correct. If two or more are valid → REWRITE.\n"
            f"  c) Ensure the correct answer is present in the 5 options. If not → REWRITE.\n"
            f"  d) Make the 4 wrong options plausible but clearly incorrect.\n"
            f"  e) If it is impossible to fix the options to have exactly one correct answer, output exactly the word 'REJECT'.\n\n"
            f"=== STEP 5: CLARITY & BLANK VERIFICATION ===\n"
            f"Is the question clear? Can a student understand what's being asked?\n"
            f"CRITICAL: If the question requires the student to fill in a blank, ensure the blank (____) ACTUALLY EXISTS.\n"
            f"If the answer word is already written inside the sentence (e.g. 'This is my sister. Her name is Sarah.'), REPLACE the answer word with a blank (____) so the student has something to solve.\n"
            f"Remove any answer disclosures (정답:, 답:, Answer:) from the problem text.\n\n"
            f"=== OUTPUT FORMAT ===\n"
            f"If the problem was duplicated or unfixable, output ONLY the word 'REJECT'.\n"
            f"Otherwise, output ONLY the final corrected problem text with corrected options.\n"
            f"Do NOT include your review comments or reasoning.\n"
            f"The output must be ready to show to a student as-is."
        ),
        expected_output=(
            "The word 'REJECT' if unfixable or duplicate, OR "
            "The final corrected English problem for students. "
            "Gender-unambiguous, single correct answer, no answer key in text."
        ),
        agent=agent,
        context=context_tasks
    )


def explanation_task(agent, context_tasks: list) -> Task:
    """영어 해설 작성 태스크를 반환합니다.

    Args:
        agent: 해설 에이전트 인스턴스
        context_tasks: 이전 태스크 목록 (검수 태스크 포함)
    """
    return Task(
        description=(
            "Write a structured explanation for the confirmed English problem.\n\n"
            "You MUST use EXACTLY the following 3 section markers in order:\n\n"
            "【핵심 어법】\n"
            "(Write 1~2 sentences explaining the KEY grammar rule or vocabulary meaning "
            "needed to solve this problem. Include a short English example.)\n\n"
            "【풀이 과정】\n"
            "(Explain step by step. Use ①②③ numbered format.\n"
            " ① 문제의 핵심: 빈칸/질문의 핵심이 무엇인지 (문법 포인트 명시)\n"
            " ② 정답 분석: 왜 정답 보기가 맞는지 (문법 근거 제시)\n"
            " ③ 오답 분석: 나머지 보기가 왜 틀렸는지 각 1줄씩\n"
            "   예시: ③ 오답: ② Her → 남성 명사이므로 불가. ③ Their → 복수형이므로 불가.\n\n"
            " IF the question involves gender/pronoun context:\n"
            "   Explicitly state WHAT word in the sentence indicates the gender,\n"
            "   and why that makes the answer unambiguous.)\n\n"
            "【최종 정답】\n"
            "(State the answer clearly. Write the option number AND the answer word.\n"
            " e.g. '① His')\n\n"
            "[STRICT PROHIBITIONS]\n"
            "- NEVER write greetings, disclaimers, or meta-commentary.\n"
            "- NEVER skip any of the 3 section markers.\n"
            "- NEVER exceed 18 lines total.\n"
            "- NEVER accept a problem where his/her BOTH could be correct - "
            "if you notice this, state in 【풀이 과정】 that the antecedent is "
            "gender-ambiguous and both ①② could be correct.\n\n"
            "[LANGUAGE]\n"
            "- All Korean for explanations.\n"
            "- Keep English words (his, her, etc.) in English, not translated.\n"
            "- Correct answer must exactly match one of the problem's 5 options."
        ),
        expected_output=(
            "A structured Korean explanation with exactly 3 sections: "
            "【핵심 어법】, 【풀이 과정】 (with oops analysis per wrong option), and 【최종 정답】."
        ),
        agent=agent,
        context=context_tasks
    )
