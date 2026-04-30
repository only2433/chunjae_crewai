"""
core/pdf_generator.py
──────────────────────
PDF 시험지 생성 엔진.

reportlab을 사용하여 과목별 레이아웃으로 PDF를 생성합니다.

[지원 레이아웃]
- math  : 수학 시험지 (표지 + 문제 + 해설)
- english: (Phase 3) 영어 시험지 (지문 박스 + 2단 구성)

[이관 이력]
- 2026-04-29: main.py의 generate_pdf_exam() 함수 분리

사용 예:
    from core.pdf_generator import generate_pdf_exam

    pdf_path = generate_pdf_exam(
        problems_list=[{"problem": "...", "explanation": "..."}],
        grade="중1",
        topic="소인수분해",
        subject_id="math"   # 레이아웃 분기용
    )
"""

import os
import re as _re


# ── LaTeX → 유니코드 변환 (PDF 출력용) ─────────────────────────────────────

def latex_to_text(text: str) -> str:
    """LaTeX 수식 표현을 읽기 쉬운 유니코드/텍스트로 변환합니다 (PDF용)."""

    # 위첨자(제곱) 유니코드 변환
    SUP_MAP = {
        '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
        '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
        '-': '⁻', 'n': 'ⁿ', 'm': 'ᵐ', 'k': 'ᵏ',
        '+': '⁺', 'x': 'ˣ'
    }

    def to_superscript(s):
        return ''.join(SUP_MAP.get(c, c) for c in s)

    # ^{...} 또는 ^단일문자 → 유니코드 위첨자
    text = _re.sub(r'\^\{([^}]+)\}', lambda m: to_superscript(m.group(1)), text)
    text = _re.sub(r'\^(\d)', lambda m: to_superscript(m.group(1)), text)

    # _{n} → _n
    text = _re.sub(r'_\{([^}]+)\}', r'_\1', text)

    # \frac{a}{b} → a/b
    text = _re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1/\2', text)

    # \sqrt{x} → √x
    text = _re.sub(r'\\sqrt\{([^}]+)\}', r'√(\1)', text)
    text = _re.sub(r'\\sqrt\b', '√', text)

    # 기호 변환
    replacements = [
        (r'\\geq', '≥'), (r'\\leq', '≤'), (r'\\neq', '≠'),
        (r'\\ge\b', '≥'), (r'\\le\b', '≤'),
        (r'\\times', '×'), (r'\\div', '÷'), (r'\\cdot', '·'),
        (r'\\pm', '±'), (r'\\mp', '∓'),
        (r'\\infty', '∞'), (r'\\pi', 'π'),
        (r'\\alpha', 'α'), (r'\\beta', 'β'), (r'\\theta', 'θ'),
        (r'\\rightarrow', '→'), (r'\\leftarrow', '←'),
        (r'\\Rightarrow', '⇒'), (r'\\Leftrightarrow', '⟺'),
        (r'\\because', '∵'), (r'\\therefore', '∴'),
        (r'\\left\(', '('), (r'\\right\)', ')'),
        (r'\\left\[', '['), (r'\\right\]', ']'),
        (r'\\approx', '≈'), (r'\\sim', '∼'), (r'\\equiv', '≡'), (r'\\propto', '∝'),
        (r'\^\\circ', '°'), (r'\\circ', '°'), (r'\^\s*°', '°'),
        (r'\\angle', '∠'), (r'\\triangle', '△'), (r'\\square', '□'),
        (r'\\quad', ' '), (r'\\qquad', '  '),
        (r'\\[,\s;!]', ' ')
    ]
    for pattern, replacement in replacements:
        text = _re.sub(pattern, replacement, text)

    # $...$ 인라인 수식 → 달러 기호 제거
    text = _re.sub(r'\$\$(.+?)\$\$', r'\1', text, flags=_re.DOTALL)
    text = _re.sub(r'\$(.+?)\$', r'\1', text)

    # 남은 백슬래시 명령어 & 중괄호 제거
    text = _re.sub(r'\\[a-zA-Z]+', '', text)
    text = text.replace('{', '').replace('}', '')

    return text


def strip_html_and_latex(text: str) -> str:
    """HTML 태그 제거 + LaTeX → 유니코드 변환 + 마커 정리 (PDF 출력용)."""
    text = _re.sub(r'<[^>]+>', '', text)
    text = (text.replace('【핵심 개념】', '[핵심 개념]')
                .replace('【풀이 과정】', '[풀이 과정]')
                .replace('【최종 정답】', '[최종 정답]'))
    text = latex_to_text(text)
    return text.strip()


# ── 수학 PDF 생성 ────────────────────────────────────────────────────────────

def generate_pdf_exam(
    problems_list: list,
    grade: str,
    topic: str,
    subject_id: str = "math",
    output_dir: str = None
) -> str:
    """
    문제 목록을 PDF 시험지로 생성합니다.

    Args:
        problems_list: [{"problem": str, "explanation": str}, ...] 형태의 목록
        grade: 학년 (e.g. "중1")
        topic: 단원 (e.g. "소인수분해")
        subject_id: 과목 식별자 — 레이아웃 분기용 ("math" | "english")
        output_dir: PDF 저장 디렉토리. None이면 ui/ 폴더 자동 선택.

    Returns:
        생성된 PDF 파일의 절대 경로 (실패 시 빈 문자열)
    """
    if subject_id == "english":
        return _generate_english_pdf(problems_list, grade, topic, output_dir)
    return _generate_math_pdf(problems_list, grade, topic, output_dir)


def _generate_math_pdf(problems_list: list, grade: str, topic: str, output_dir: str = None) -> str:
    """수학 전용 PDF 생성 (표지 + 문제 + 해설)."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        # 한글 폰트 등록
        font_path = r"C:\Windows\Fonts\malgun.ttf"
        font_bold_path = r"C:\Windows\Fonts\malgunbd.ttf"
        pdfmetrics.registerFont(TTFont("Malgun", font_path))
        pdfmetrics.registerFont(TTFont("MalgunBold", font_bold_path))

        if output_dir is None:
            # core/pdf_generator.py 기준으로 상위 두 단계 → 프로젝트 루트/ui
            _here = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(os.path.dirname(_here), "ui")

        os.makedirs(output_dir, exist_ok=True)
        pdf_path = os.path.join(output_dir, "exam_output.pdf")

        doc = SimpleDocTemplate(
            pdf_path, pagesize=A4,
            leftMargin=2.5 * cm, rightMargin=2.5 * cm,
            topMargin=2.5 * cm, bottomMargin=2.5 * cm
        )

        style_title  = ParagraphStyle("Title",  fontName="MalgunBold", fontSize=18, spaceAfter=6,  leading=26, textColor=colors.HexColor("#18181b"))
        style_sub    = ParagraphStyle("Sub",    fontName="Malgun",     fontSize=11, spaceAfter=16, leading=17, textColor=colors.HexColor("#71717a"))
        style_qnum   = ParagraphStyle("QNum",   fontName="MalgunBold", fontSize=13, spaceAfter=6,  leading=20, textColor=colors.HexColor("#2563eb"))
        style_body   = ParagraphStyle("Body",   fontName="Malgun",     fontSize=12, spaceAfter=4,  leading=20, textColor=colors.HexColor("#18181b"))
        style_answer = ParagraphStyle("Answer", fontName="MalgunBold", fontSize=11, spaceAfter=4,  leading=18, textColor=colors.HexColor("#16a34a"), leftIndent=12)

        story = []

        # 표지
        story.append(Spacer(1, 1 * cm))
        story.append(Paragraph(f"{grade} 수학 단원 평가", style_title))
        story.append(Paragraph(f"단원: {topic}  |  문항 수: {len(problems_list)}문제", style_sub))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=20))
        story.append(Paragraph("이름: ________________________  점수: ________", style_body))
        story.append(Spacer(1, 0.8 * cm))

        # 문제 섹션
        story.append(Paragraph("■ 문제", style_qnum))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e4e4e7"), spaceAfter=10))

        for idx, item in enumerate(problems_list, 1):
            prob_text = strip_html_and_latex(item.get("problem", ""))
            story.append(Paragraph(f"문제 {idx}.", style_qnum))
            
            img_path = item.get("image")
            if img_path:
                from reportlab.platypus import Image
                abs_img_path = os.path.join(output_dir, img_path)
                if os.path.exists(abs_img_path):
                    try:
                        story.append(Spacer(1, 0.2 * cm))
                        story.append(Image(abs_img_path, width=10*cm, height=8*cm, kind='proportional'))
                        story.append(Spacer(1, 0.2 * cm))
                    except Exception as e:
                        print(f"PDF 이미지 삽입 오류: {e}")

            for line in prob_text.split('\n'):
                line = line.strip()
                if line:
                    story.append(Paragraph(line, style_body))
            story.append(Spacer(1, 0.6 * cm))

        # 해설 섹션 (새 페이지)
        story.append(PageBreak())
        story.append(Paragraph("■ 정답 및 해설", style_qnum))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e4e4e7"), spaceAfter=10))

        for idx, item in enumerate(problems_list, 1):
            exp_text = strip_html_and_latex(item.get("explanation", ""))
            story.append(Paragraph(f"문제 {idx} 해설", style_qnum))
            for line in exp_text.split('\n'):
                line = line.strip()
                if line:
                    if '[최종 정답]' in line:
                        story.append(Paragraph(line, style_answer))
                    else:
                        story.append(Paragraph(line, style_body))
            story.append(Spacer(1, 0.5 * cm))
            story.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor("#f4f4f5"), spaceAfter=6))

        doc.build(story)
        return pdf_path

    except Exception as e:
        print(f"[pdf_generator] 수학 PDF 생성 오류: {e}")
        return ""


def _generate_english_pdf(data_dict: dict, grade: str, topic: str, output_dir: str = None) -> str:
    """
    영어 전용 PDF 생성.
    data_dict 에는 title, passage, questions, vocab 가 포함되어 있습니다.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, PageBreak
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        font_path = r"C:\Windows\Fonts\malgun.ttf"
        font_bold_path = r"C:\Windows\Fonts\malgunbd.ttf"
        pdfmetrics.registerFont(TTFont("Malgun", font_path))
        pdfmetrics.registerFont(TTFont("MalgunBold", font_bold_path))

        if output_dir is None:
            _here = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(os.path.dirname(_here), "ui")

        os.makedirs(output_dir, exist_ok=True)
        pdf_path = os.path.join(output_dir, "english_exam_output.pdf")

        doc = SimpleDocTemplate(
            pdf_path, pagesize=A4,
            leftMargin=2.5 * cm, rightMargin=2.5 * cm,
            topMargin=2.5 * cm, bottomMargin=2.5 * cm
        )

        style_title  = ParagraphStyle("Title",  fontName="MalgunBold", fontSize=18, spaceAfter=6,  leading=26, textColor=colors.HexColor("#18181b"))
        style_sub    = ParagraphStyle("Sub",    fontName="Malgun",     fontSize=11, spaceAfter=16, leading=17, textColor=colors.HexColor("#71717a"))
        style_qnum   = ParagraphStyle("QNum",   fontName="MalgunBold", fontSize=13, spaceAfter=6,  leading=20, textColor=colors.HexColor("#16a34a"))
        style_body   = ParagraphStyle("Body",   fontName="Malgun",     fontSize=12, spaceAfter=4,  leading=20, textColor=colors.HexColor("#18181b"))
        style_passage= ParagraphStyle("Passage", fontName="Malgun",     fontSize=11, spaceAfter=6,  leading=18, textColor=colors.HexColor("#3f3f46"), leftIndent=10, rightIndent=10, backColor=colors.HexColor("#f4f4f5"), borderPadding=10)
        style_answer = ParagraphStyle("Answer", fontName="MalgunBold", fontSize=11, spaceAfter=4,  leading=18, textColor=colors.HexColor("#16a34a"), leftIndent=12)

        story = []

        title = data_dict.get("title", "BBC News Article")
        passage = data_dict.get("passage", "")
        questions_dict = data_dict.get("questions", {})
        vocab_list = data_dict.get("vocab", [])

        # 표지 및 제목
        story.append(Spacer(1, 1 * cm))
        story.append(Paragraph(f"{grade} 영어 독해 평가", style_title))
        story.append(Paragraph(f"출처: {title}", style_sub))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#16a34a"), spaceAfter=20))
        story.append(Paragraph("이름: ________________________  점수: ________", style_body))
        story.append(Spacer(1, 0.8 * cm))

        # 본문 지문
        story.append(Paragraph("■ 읽기 지문", style_qnum))
        for p in passage.split('\n\n'):
            if p.strip():
                story.append(Paragraph(strip_html_and_latex(p), style_passage))
        story.append(Spacer(1, 0.6 * cm))

        # 문제 목록화
        flat_questions = []
        for q_type, q_list in questions_dict.items():
            flat_questions.extend(q_list)

        # 문제 섹션
        story.append(Paragraph("■ 문제", style_qnum))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e4e4e7"), spaceAfter=10))

        for idx, q in enumerate(flat_questions, 1):
            story.append(Paragraph(f"[{idx}번] {strip_html_and_latex(q.get('instruction', ''))}", style_qnum))
            if q.get('question') and q.get('question') != '...':
                q_text = strip_html_and_latex(q['question'].replace('<u>', '').replace('</u>', ''))
                story.append(Paragraph(q_text, style_body))
            
            choices = q.get('choices', [])
            if choices:
                for c_idx, c_text in enumerate(choices, 1):
                    story.append(Paragraph(f"   ({c_idx}) {strip_html_and_latex(c_text)}", style_body))
            story.append(Spacer(1, 0.6 * cm))

        # 해설 섹션 (새 페이지)
        story.append(PageBreak())
        story.append(Paragraph("■ 정답 및 해설", style_qnum))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e4e4e7"), spaceAfter=10))

        for idx, q in enumerate(flat_questions, 1):
            story.append(Paragraph(f"[{idx}번] 정답: {strip_html_and_latex(str(q.get('answer', '')))}", style_answer))
            exp = q.get('explanation', '')
            if exp:
                story.append(Paragraph(f"해설: {strip_html_and_latex(exp)}", style_body))
            story.append(Spacer(1, 0.4 * cm))
            story.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor("#f4f4f5"), spaceAfter=6))

        # 단어장 섹션
        pos_map = {
            'verb': '동사', 'noun': '명사', 'adjective': '형용사', 'adverb': '부사',
            'pronoun': '대명사', 'preposition': '전치사', 'conjunction': '접속사', 'interjection': '감탄사'
        }
        if vocab_list:
            story.append(Spacer(1, 0.5 * cm))
            story.append(Paragraph("■ 필수 단어장", style_qnum))
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e4e4e7"), spaceAfter=10))
            for v in vocab_list:
                pos = v.get('pos', '').lower()
                kor_pos = pos_map.get(pos, v.get('pos', ''))
                line = f"{v.get('word', '')} ({kor_pos}): {v.get('definition_ko', '')}"
                story.append(Paragraph(strip_html_and_latex(line), style_body))

        doc.build(story)
        return pdf_path

    except Exception as e:
        print(f"[pdf_generator] 영어 PDF 생성 오류: {e}")
        return ""
