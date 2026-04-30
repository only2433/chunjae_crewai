"""
gui.py
───────
pywebview 기반 UI-백엔드 브리지 (API 클래스).

[Phase 3 업데이트]
- 모든 API 메서드에 subject_id 파라미터 추가
- subjects.get_subject(subject_id) 팩토리를 통해 과목 플러그인 동적 선택
- 영어(english) 과목 지원 추가

[하위 호환]
- subject_id 기본값 = "math" (기존 동작 유지)
"""

import os
import sys
import webview
import threading

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from subjects import get_subject
from core.pipeline import run_pipeline, run_exam_pipeline
from subjects.english.bbc_scraper import get_bbc_news_list, fetch_article
from subjects.english.ai_engine import generate_english_problems


class Api:
    def __init__(self):
        print("Chunjae EduCrew AI UI Initialized.")

    def _make_progress_callback(self):
        """pywebview JS 통신용 progress_callback을 생성합니다."""
        def progress_callback(stage, msg, status="active"):
            escaped_msg = str(msg).replace("'", "\\'").replace('"', '\\"').replace('\n', ' ')
            js_code = f"if(window.updateStageRealtime) window.updateStageRealtime({stage}, '{escaped_msg}', '{status}');"
            try:
                webview.windows[0].evaluate_js(js_code)
            except Exception as e:
                print("JS 통신 에러:", e)
        return progress_callback

    def generate_crew(self, grade: str, topic: str, use_fast: bool = False, subject_id: str = "math"):
        """JS에서 호출하여 CrewAI 1문제 파이프라인을 실행합니다.

        Args:
            grade: 학년 (e.g. "중1")
            topic: 단원/주제
            use_fast: True이면 GPT 빠른 모드
            subject_id: "math" | "english" (기본값: "math")
        """
        subject = get_subject(subject_id)
        mode = "빠른(GPT)" if use_fast else "로컬"
        print(f"\n[UI 요청] {subject.label} | {mode} | {grade} | {topic}")

        try:
            result = run_pipeline(
                subject=subject,
                grade=grade,
                topic=topic,
                progress_callback=self._make_progress_callback(),
                use_fast=use_fast
            )
            return result
        except Exception as e:
            return {"error": str(e), "problem": f"**오류 발생:** {str(e)}", "explanation": ""}

    def generate_exam(self, grade: str, topic: str, count: int = 10,
                      use_fast: bool = False, subject_id: str = "math"):
        """시험지 모드: 여러 문제를 생성하고 PDF로 저장합니다.

        Args:
            grade: 학년
            topic: 단원/주제
            count: 문제 수 (기본 10)
            use_fast: True이면 GPT 빠른 모드
            subject_id: "math" | "english"
        """
        subject = get_subject(subject_id)
        mode = "빠른(GPT)" if use_fast else "로컬"
        print(f"\n[시험지 요청] {subject.label} | {mode} | {grade} | {topic} | {count}문제")

        try:
            result = run_exam_pipeline(
                subject=subject,
                grade=grade,
                topic=topic,
                count=count,
                progress_callback=self._make_progress_callback(),
                with_explanation=False,
                use_fast=use_fast
            )
            return result
        except Exception as e:
            return {"error": str(e)}

    def generate_exam_full(self, grade: str, topic: str, count: int = 10,
                           use_fast: bool = False, subject_id: str = "math"):
        """시험지 모드 (해설 포함): 문제 + 해설/정답을 생성하고 PDF로 저장합니다.

        Args:
            grade: 학년
            topic: 단원/주제
            count: 문제 수 (기본 10)
            use_fast: True이면 GPT 빠른 모드
            subject_id: "math" | "english"
        """
        subject = get_subject(subject_id)
        mode = "빠른(GPT)" if use_fast else "로컬"
        print(f"\n[시험지+해설 요청] {subject.label} | {mode} | {grade} | {topic} | {count}문제")

        try:
            result = run_exam_pipeline(
                subject=subject,
                grade=grade,
                topic=topic,
                count=count,
                progress_callback=self._make_progress_callback(),
                with_explanation=True,
                use_fast=use_fast
            )
            return result
        except Exception as e:
            return {"error": str(e)}

    def open_pdf(self, pdf_path: str):
        """PDF 파일을 기본 프로그램으로 엽니다."""
        import subprocess
        try:
            subprocess.Popen(["start", "", pdf_path], shell=True)
            return True
        except Exception as e:
            print("PDF 열기 오류:", e)
            return False

    def get_subjects(self):
        """등록된 과목 목록을 UI에 반환합니다."""
        from subjects import list_subjects, get_subject as _gs
        result = []
        for sid in list_subjects():
            s = _gs(sid)
            result.append({
                "id":     s.subject_id,
                "label":  s.label,
                "grades": s.config.get("grade_options", []),
                "topics": s.config.get("topic_options", {})
            })
        return result

    # ── 영어 특화 API (BBC 뉴스 및 지문 기반 문제 생성) ──
    def fetch_bbc_news(self):
        """BBC 뉴스 목록을 가져옵니다."""
        print("[UI 요청] BBC 최신 뉴스 목록 가져오기")
        return get_bbc_news_list()

    def generate_english_set(self, grade: str, url: str, q_types: list):
        """선택한 BBC 뉴스와 문제 유형으로 영어 문제 세트를 생성합니다."""
        print(f"\n[영어 문제 세트 요청] {grade} | URL: {url} | 유형: {q_types}")
        
        # 1단계: 뉴스 기사 가져오기
        try:
            if self._make_progress_callback():
                self._make_progress_callback()(1, "BBC 기사 본문 수집 중...", "active")
            article_data = fetch_article(url)
            article_text = article_data['text']
            article_title = article_data['title']
        except Exception as e:
            return {"error": f"기사를 가져오는데 실패했습니다: {e}"}

        # 2단계: AI 엔진을 통한 문제 생성
        try:
            import threading
            import time
            stop_progress = False

            def progress_updater():
                phases = [
                    (1, "영어 지문 파싱 및 난이도 조절 중...", "active"),
                    (1, "선택된 유형별 문제 구조 설계 중...", "active"),
                    (1, "영어 문제 추출 및 생성 중...", "active"),
                    (1, "단어장 구성 및 상세 해설 생성 중...", "active")
                ]
                for phase_data in phases:
                    if stop_progress:
                        break
                    if self._make_progress_callback():
                        self._make_progress_callback()(*phase_data)
                    for _ in range(35): # 각 단계당 약 3.5초 대기
                        if stop_progress:
                            break
                        time.sleep(0.1)

            t = threading.Thread(target=progress_updater)
            t.start()
            
            try:
                result_data = generate_english_problems(article_text, grade, q_types)
            finally:
                stop_progress = True
                t.join()
            
            # PDF 생성
            from core.pdf_generator import generate_pdf_exam
            pdf_data = {
                "title": article_title,
                "passage": result_data.get("adapted_passage", article_text),
                "questions": result_data.get("questions", {}),
                "vocab": result_data.get("vocab", [])
            }
            pdf_path = generate_pdf_exam(
                problems_list=pdf_data,  # 영어의 경우 data_dict 로 사용됨
                grade=grade,
                topic="BBC News Reading",
                subject_id="english"
            )

            if self._make_progress_callback():
                self._make_progress_callback()(1, "문제 생성 및 PDF 저장 완료!", "done")

            return {
                "title": article_title,
                "passage": result_data.get("adapted_passage", article_text),
                "questions": result_data.get("questions", {}),
                "vocab": result_data.get("vocab", []),
                "pdf_path": pdf_path
            }
        except Exception as e:
            return {"error": f"문제 생성 중 오류가 발생했습니다: {e}"}


def start_gui():
    api = Api()
    ui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "index.html")

    webview.create_window(
        "Chunjae EduCrew AI",
        url=f"file://{ui_path}",
        js_api=api,
        width=1100,
        height=860,
        background_color='#fafafa'
    )
    webview.start()


if __name__ == "__main__":
    start_gui()
