"""
core/pipeline.py
─────────────────
CrewAI 파이프라인 오케스트레이터.

과목(Subject) 플러그인과 무관하게 동일한 흐름으로
출제 → 검수 → 해설 → 최종감수 파이프라인을 실행합니다.

[이관 이력]
- 2026-04-29: main.py의 run_chunjae_crew(), run_exam_crew(),
              run_python_illustrator() 함수 분리

[현재 지원 과목]
- 수학 (MathSubject) — subjects/math/
- 영어 (EnglishSubject) — subjects/english/ [Phase 3 예정]

사용 예:
    from subjects.math import MathSubject
    from core.pipeline import run_pipeline, run_exam_pipeline

    subject = MathSubject()
    result = run_pipeline(subject, grade="중1", topic="소인수분해")
    # result: {"problem": ..., "explanation": ..., "image": ...}

    exam   = run_exam_pipeline(subject, grade="중1", topic="소인수분해", count=10)
    # exam: {"problems": [...], "pdf_path": ..., "count": 10}
"""

import os
import re
import subprocess
import concurrent.futures
from crewai import Crew, Process
from openai import OpenAI

from core.safety_review import logic_safety_review
from core.pdf_generator import generate_pdf_exam


# ── 정답 누출 방지 패턴 (공통) ──────────────────────────────────────────────

_ANSWER_PATTERN = re.compile(
    r'^\s*(정답|답|Answer|Correct Answer|해답|풀이)\s*[:：].*$',
    re.IGNORECASE | re.MULTILINE
)


def _remove_answer_leak(text: str) -> str:
    """문제 텍스트에서 정답 누출 행을 제거하고 연속 빈 줄을 정리합니다."""
    text = _ANSWER_PATTERN.sub('', text).strip()
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


# ── 그래프/도형 이미지 생성 (수학 전용) ─────────────────────────────────────

def _run_python_illustrator(prob_text: str, force_draw: bool = False, filename: str = "ui/problem_image.png") -> str | None:
    """
    문제 텍스트를 분석하여 matplotlib 시각화 코드를 GPT-4o로 생성하고,
    서브프로세스로 실행하여 이미지를 저장합니다.

    Args:
        prob_text: 분석할 문제 텍스트
        force_draw: True이면 판단을 무시하고 무조건 그림을 그리도록 강제
        filename: 저장할 파일 경로 (기본값: "ui/problem_image.png")

    Returns:
        filename — 이미지 생성 성공
        "NO_IMAGE_NEEDED"   — 시각화 불필요
        None                — 생성 실패
    """
    prompt = f"""You are an expert Python data visualization engineer.
Your task is to evaluate the following middle school math problem and draw a precise mathematical diagram using `matplotlib` ONLY IF it's highly beneficial (e.g., geometry, coordinates, graphs, statistics).

Problem: {prob_text}

Requirements:
1. **DECISION**: If the problem is purely algebraic, equations, simple arithmetic, or does not heavily rely on visual intuition (e.g., 'sum of two numbers is 15', polynomials, inequalities), you MUST reply exactly with the string: \"NO_IMAGE_NEEDED\" and nothing else.
2. If visualization is needed, strictly follow these drawing rules:
   - The script MUST save the plot directly to exactly '{filename}' using `plt.savefig('{filename}', bbox_inches='tight', dpi=300)`. Do NOT use `plt.show()`.
   - Support Korean font on Windows by adding: `import matplotlib.pyplot as plt`, `plt.rcParams['font.family'] = 'Malgun Gothic'`, `plt.rcParams['axes.unicode_minus'] = False`
   - Make the drawing visually appealing and extremely clear. **DO NOT FILL SOLID COLORS in geometric shapes (no facecolors).** For 3D geometries (cube, cylinder), leave the faces completely transparent (e.g., `facecolor='none'` or `fill=False`) and draw ONLY the outlines(edges) with solid black lines. Hidden edges should be drawn with dashed lines (`linestyle='dashed'`).
   - **CRITICAL WARNING FOR SPOILERS**: ONLY draw and label the numbers that are EXPLICITLY given in the problem. Do NOT solve the problem!
   - **DO NOT USE `mplot3d` OR `Axes3D` AT ALL**: Draws 3D geometries as 2D orthographic projections using simple 2D transparent lines and shapes (`matplotlib.patches.Polygon`, `Line2D`, `fill=False`).
   - Only output pure Python code inside a ```python ``` block. Do not write any other explanations.

Make sure the code is syntactically correct and imports all necessary modules."""

    if force_draw:
        prompt += "\n\nCRITICAL INSTRUCTION: The user has explicitly checked the 'Include Image' option. You MUST NOT output 'NO_IMAGE_NEEDED'. You MUST write a python script to draw the most relevant geometric or mathematical diagram for this problem."

    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.1
        )
        output = response.choices[0].message.content

        if "NO_IMAGE_NEEDED" in output:
            print("[pipeline] 시각화 불필요 판단 — 이미지 생략")
            return "NO_IMAGE_NEEDED"

        match = re.search(r'```python\n(.*?)\n```', output, re.DOTALL)
        if not match:
            return None

        raw_code = match.group(1)

        # 보안: 허용되지 않은 모듈 import 차단
        forbidden_modules = ['os', 'sys', 'subprocess', 'shutil', 'requests', 'urllib', 'socket']
        filtered_lines = []
        for line in raw_code.split('\n'):
            if line.startswith('plt.rcParams'):
                continue
            is_forbidden = any(
                re.search(rf'\bimport\s+{mod}\b|\bfrom\s+{mod}\b', line)
                for mod in forbidden_modules
            )
            if is_forbidden:
                print(f"[pipeline][보안] 차단된 모듈 import: {line.strip()}")
                continue
            if "__import__" not in line and "eval(" not in line and "exec(" not in line:
                filtered_lines.append(line)

        indented_code = '\n'.join('    ' + line for line in filtered_lines)

        safe_code = f"""import matplotlib.pyplot as plt
import numpy as np
import traceback
import sys

plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

try:
{indented_code}
except Exception as e:
    print('시각화 코드 실행 오류:')
    traceback.print_exc()
    sys.exit(1)
finally:
    plt.close('all')
"""
        script_path = "temp_drawer.py"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(safe_code)

        os.makedirs("ui", exist_ok=True)
        subprocess.run(["python", script_path], check=True, capture_output=True, timeout=15)

        if os.path.exists(script_path):
            os.remove(script_path)

        img_dest = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), filename)
        if os.path.exists(img_dest):
            # return path relative to ui folder since that's how it's used in HTML
            # e.g., if filename is "ui/problem_image_0.png", return "problem_image_0.png"
            return os.path.basename(filename)
        return None

    except subprocess.CalledProcessError as e:
        print(f"[pipeline] 시각화 스크립트 실행 오류: {e.stderr.decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"[pipeline] 시각화 생성 오류: {e}")
    finally:
        if os.path.exists(script_path):
            os.remove(script_path)
    return None


# ── HTML 렌더링: 해설 섹션 마커 변환 ────────────────────────────────────────

def _render_explanation_html(final_explanation: str) -> str:
    """
    【핵심 개념】 【풀이 과정】 【최종 정답】 마커를
    UI 렌더링용 HTML 박스로 변환합니다.
    """
    def wrap_section(marker, content, style):
        content_html = content.strip().replace('\n', '<br>')
        return (
            f'<div style="{style}">'
            f'<div style="font-weight:700; font-size:15px; margin-bottom:8px;">{marker}</div>'
            f'<div style="line-height:1.9; font-size:15px;">{content_html}</div>'
            f'</div>'
        )

    sections = re.split(r'(【[^】]+】)', final_explanation)
    rendered = ''
    i = 0
    while i < len(sections):
        part = sections[i].strip()
        if part == '【핵심 개념】' and i + 1 < len(sections):
            rendered += wrap_section(
                '💡 핵심 개념', sections[i + 1],
                'background:#f0f4f8; border-left:4px solid #6b7280; border-radius:8px; padding:14px 18px; margin:12px 0;'
            )
            i += 2
        elif part == '【풀이 과정】' and i + 1 < len(sections):
            rendered += wrap_section(
                '📝 풀이 과정', sections[i + 1],
                'background:#f0fdf4; border:2px solid #22c55e; border-radius:8px; padding:14px 18px; margin:12px 0;'
            )
            i += 2
        elif part == '【최종 정답】' and i + 1 < len(sections):
            ans_text = sections[i + 1].strip()
            ans_html = ans_text.replace('\n', '<br>')
            rendered += (
                f'<div style="background:linear-gradient(135deg,#34c759,#28a745);color:white;'
                f'padding:14px 24px;border-radius:12px;font-size:18px;font-weight:700;'
                f'margin-top:16px;display:inline-block;box-shadow:0 4px 12px rgba(40,167,69,0.25);'
                f'letter-spacing:0.5px;line-height:1.6;">🎯 최종 정답: {ans_html}</div>'
            )
            i += 2
        else:
            if part:
                match = re.search(r'(최종\s*정답\s*[:\s\n]*)(.*)', part, flags=re.DOTALL)
                if match:
                    ans_html = match.group(2).strip().replace('\n', '<br>')
                    rendered += part[:match.start()]
                    rendered += (
                        f'<div style="background:linear-gradient(135deg,#34c759,#28a745);color:white;'
                        f'padding:14px 24px;border-radius:12px;font-size:18px;font-weight:700;'
                        f'margin-top:16px;display:inline-block;">🎯 최종 정답: {ans_html}</div>'
                    )
                else:
                    rendered += part
            i += 1

    return rendered if rendered.strip() else final_explanation


# ── 1문제 생성 파이프라인 ────────────────────────────────────────────────────

def run_pipeline(subject, grade: str, topic: str, progress_callback=None, use_fast: bool = False, require_image: bool = False) -> dict:
    """
    1문제 생성 전체 파이프라인을 실행합니다.
    (출제 → 검수 → 해설 → 시각화 → 최종감수)

    Args:
        subject: SubjectBase 구현체 (e.g. MathSubject())
        grade: 학년 (e.g. "중1")
        topic: 단원/주제 (e.g. "소인수분해")
        progress_callback: (stage, msg, status) 형태의 UI 알림 콜백
        use_fast: True이면 출제/해설도 GPT-4o-mini 사용
        require_image: True이면 도형 시각화 에이전트를 강제 실행

    Returns:
        {"problem": str, "explanation": str, "image": str | None}
    """
    def notify(stage, msg, status="active"):
        if progress_callback:
            progress_callback(stage, msg, status)

    mode_label = "빠른 모드 (GPT)" if use_fast else "로컬 모드"
    print(f"\n[pipeline] {subject.label} | {mode_label} | {grade} | '{topic}'\n" + "=" * 60)

    generator = subject.get_generator_agent(use_fast=use_fast)
    reviewer  = subject.get_reviewer_agent()
    explainer = subject.get_explainer_agent(use_fast=use_fast)

    final_problem = ""
    final_explanation = ""
    img_path = None

    for attempt in range(3):
        print(f"\n[pipeline] 종합 생성 파이프라인 (시도 {attempt + 1}/3)")

        # ── 1단계: 문제 출제 ─────────────────────────────────────
        task1 = subject.get_generation_task(generator, grade, topic)
        crew_generate = Crew(agents=[generator], tasks=[task1], process=Process.sequential, verbose=True)
        crew_generate.kickoff()
        notify(1, f"문제 출제 완료 (시도 {attempt + 1})", "done")

        # ── 2단계: 문제 검수 ─────────────────────────────────────
        notify(2, "OpenAI 감수관이 문제 검증 중...", "active")
        task2 = subject.get_review_task(reviewer, [task1], grade)
        crew_review = Crew(agents=[reviewer], tasks=[task2], process=Process.sequential, verbose=True)
        crew_review.kickoff()
        notify(2, "OpenAI 감수관 검증 완료", "done")

        try:
            final_problem = task2.output.raw if hasattr(task2.output, 'raw') else str(task2.output)
        except Exception:
            final_problem = str(task2.output)

        final_problem = _remove_answer_leak(final_problem)
        notify(2, "문제 기초 감수 통과 완료", "done")

        # ── 3단계: 해설 + 4단계: 최종감수 (내부 루프) ───────────
        def run_explanation_crew(prob_text):
            task3 = subject.get_explanation_task(explainer, [])
            task3.description = (
                f"다음은 검수가 완료된 최종 {subject.label} 문제입니다.\n\n[확정 문제]:\n{prob_text}\n\n---\n"
                + task3.description
            )
            crew_phase2 = Crew(agents=[explainer], tasks=[task3], process=Process.sequential, verbose=True)
            crew_phase2.kickoff()
            try:
                ans = task3.output.raw if hasattr(task3.output, 'raw') else str(task3.output)
            except Exception:
                ans = str(task3.output)
            ans = ans.replace('```latex', '').replace('```math', '').replace('```', '')
            return ans.strip()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            # 이미지 생성과 해설 생성을 병렬 실행 (체크박스가 켜진 경우에만 강제 실행)
            future_image = None
            if require_image and subject.subject_id == "math":
                future_image = executor.submit(lambda: _run_python_illustrator(final_problem, force_draw=True))

            problem_passed = False
            for exp_attempt in range(3):
                notify(3, f"해설 작성 중... (시도 {exp_attempt + 1})", "active")
                final_explanation = run_explanation_crew(final_problem)

                notify(3, "해설 작성 완료. 최종 감수 대기", "done")
                notify(4, "논리성 및 환각 여부 최종 검사 중...", "active")
                review_result = logic_safety_review(final_problem, final_explanation)

                if "PASS" in review_result.upper():
                    print("[pipeline] 종합 검수 통과!")
                    notify(4, "완벽! 모든 감수 통과 완료", "done")
                    problem_passed = True
                    break
                elif "FAIL_EXPLANATION" in review_result.upper() and exp_attempt < 2:
                    print(f"[pipeline] 해설 오류: {review_result}")
                    notify(4, f"해설 오류 적발 (재작성): {review_result[:40]}...", "error")
                else:
                    print(f"[pipeline] 문제 치명적 결함: {review_result}")
                    notify(4, f"문제 결함 적발 (재출제): {review_result[:40]}...", "error")
                    break

            if future_image:
                img_path = future_image.result()
            else:
                img_path = None

        if problem_passed or attempt == 2:
            break

    # LaTeX 변환 (UI MathJax용)
    if final_problem:
        final_problem = final_problem.replace('\\[', '$$').replace('\\]', '$$').replace('\\(', '$').replace('\\)', '$')
    if final_explanation:
        final_explanation = final_explanation.replace('\\[', '$$').replace('\\]', '$$').replace('\\(', '$').replace('\\)', '$')
        final_explanation = final_explanation.replace("**", "")
        final_explanation = _render_explanation_html(final_explanation)

    return {
        "problem": final_problem.strip(),
        "explanation": final_explanation.strip(),
        "image": img_path if img_path != "NO_IMAGE_NEEDED" else None
    }


# ── 시험지 일괄 생성 파이프라인 ─────────────────────────────────────────────

def run_exam_pipeline(
    subject,
    grade: str,
    topic: str,
    count: int = 10,
    progress_callback=None,
    with_explanation: bool = False,
    use_fast: bool = False,
    require_image: bool = False
) -> dict:
    """
    시험지 모드: count개의 문제를 순차 생성 후 PDF로 반환합니다.

    Args:
        subject: SubjectBase 구현체
        grade: 학년
        topic: 단원/주제
        count: 생성할 문제 수 (기본 10)
        progress_callback: UI 알림 콜백
        with_explanation: True이면 해설/정답도 PDF에 포함
        use_fast: True이면 출제/해설도 GPT 사용

    Returns:
        {"problems": [...], "pdf_path": str, "count": int, "with_explanation": bool}
    """
    def notify(stage, msg, status="active"):
        if progress_callback:
            progress_callback(stage, msg, status)

    variety_hints = subject.get_variety_hints()
    generator = subject.get_generator_agent(use_fast=use_fast)
    reviewer  = subject.get_reviewer_agent()
    explainer = subject.get_explainer_agent(use_fast=use_fast) if with_explanation else None

    problems_list = []
    generated_so_far = []  # 중복 방지: 생성된 문제 텍스트 누적 목록

    for i in range(count):
        hint = variety_hints[i % len(variety_hints)]
        type_label = ['계산형', '문장제', '도형형'][i % 3] if subject.subject_id == "math" else f"유형{(i % len(variety_hints)) + 1}"

        print(f"\n{'=' * 60}")
        print(f"[pipeline] 문제 {i + 1}/{count} 생성 중... [{type_label}]")

        final_problem = ""
        problem_passed = False

        for attempt in range(3):  # 최대 3번 재시도
            notify(1, f"문제 {i + 1}/{count} 출제 중... (시도 {attempt+1})", "active")

            # 출제 (이미 생성된 문제 목록 전달 → 중복 방지)
            task1 = subject.get_generation_task(
                generator, grade, topic,
                variety_hint=hint,
                generated_so_far=generated_so_far if generated_so_far else None
            )
            crew_gen = Crew(agents=[generator], tasks=[task1], process=Process.sequential, verbose=False)
            crew_gen.kickoff()
            
            notify(1, f"문제 {i + 1}/{count} 출제 완료", "done")

            notify(2, f"문제 {i + 1}/{count} 검수 중... (GPT)", "active")

            # 검수
            task2 = subject.get_review_task(
                reviewer, [task1], grade,
                generated_so_far=generated_so_far if generated_so_far else None
            )
            crew_rev = Crew(agents=[reviewer], tasks=[task2], process=Process.sequential, verbose=False)
            crew_rev.kickoff()

            try:
                final_problem = task2.output.raw if hasattr(task2.output, 'raw') else str(task2.output)
            except Exception:
                final_problem = str(task2.output)

            # 검수관이 중복/치명적 오류로 REJECT한 경우 재시도
            if "REJECT" in final_problem.upper()[:50]:  # 맨 앞에 REJECT가 있는 경우
                print(f"[pipeline] 문제 {i + 1} 검수관 반려 (중복 또는 오류). 재출제합니다...")
                notify(2, f"문제 {i + 1} 검수 반려, 재출제 중...", "error")
                continue

            # 통과한 경우 루프 종료
            notify(2, f"문제 {i + 1}/{count} 검수 완료", "done")
            final_problem = _remove_answer_leak(final_problem)
            problem_passed = True
            break
        
        # 3번 시도해도 실패하면 어쩔 수 없이 마지막 결과 사용하되 REJECT 문자열만 제거
        if "REJECT" in final_problem.upper():
            final_problem = final_problem.replace("REJECT", "").strip()

        # 누적 목록에 추가 (앞 100자만 저장해 프롬프트 길이 관리)
        generated_so_far.append(final_problem[:200])

        # 해설 생성 (with_explanation 모드)
        final_explanation = ""
        img_path = None
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_image = None
            if require_image and subject.subject_id == "math":
                import uuid
                unique_filename = f"ui/problem_image_{uuid.uuid4().hex[:8]}.png"
                future_image = executor.submit(lambda: _run_python_illustrator(final_problem, force_draw=True, filename=unique_filename))

            if with_explanation and explainer:
                notify(3, f"문제 {i + 1}/{count} 해설 생성 중...", "active")
                try:
                    task3 = subject.get_explanation_task(explainer, [])
                    task3.description = (
                        f"다음은 검수가 완료된 최종 {subject.label} 문제입니다.\n\n[확정 문제]:\n{final_problem}\n\n---\n"
                        + task3.description
                    )
                    crew_exp = Crew(agents=[explainer], tasks=[task3], process=Process.sequential, verbose=False)
                    crew_exp.kickoff()
                    raw_exp = task3.output.raw if hasattr(task3.output, 'raw') else str(task3.output)
                    import re as _re
                    final_explanation = _re.sub(r'<[^>]+>', '', raw_exp).strip()
                except Exception as e:
                    print(f"[pipeline] 해설 생성 오류 (문제 {i + 1}): {e}")
                notify(3, f"문제 {i + 1}/{count} 해설 완료", "done")
                
            if future_image:
                img_path = future_image.result()

        notify(1, f"문제 {i + 1}/{count} 완료", "done")
        problems_list.append({"problem": final_problem, "explanation": final_explanation, "image": img_path, "number": i + 1})


    # PDF 생성
    notify(2, "PDF 생성 중...", "active")
    pdf_path = generate_pdf_exam(problems_list, grade, topic, subject_id=subject.subject_id)
    mode_label = f"{count}문제 + 해설" if with_explanation else f"{count}문제"
    notify(2, f"시험지 완성! ({mode_label})", "done")

    return {
        "problems": problems_list,
        "pdf_path": pdf_path,
        "count": count,
        "with_explanation": with_explanation
    }
