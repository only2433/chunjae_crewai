"""
CrewAI Agent 레벨 디버그 테스트
단순 llm.call()이 아닌 실제 Agent + Crew 실행으로 확인
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["OTEL_SDK_DISABLED"] = "true"

from crewai import Agent, Task, Crew, Process, LLM

BASE_URL = "http://localhost:11434"

configs = {
    "A. 기존(제한없음)": LLM(
        model="ollama/qwen3:4b", temperature=0.7,
        base_url=BASE_URL
    ),
    "B. max_tokens=500, think=False": LLM(
        model="ollama/qwen3:4b", temperature=0.7,
        max_tokens=500, base_url=BASE_URL,
        extra_body={"think": False}
    ),
    "C. max_tokens=800, think=False": LLM(
        model="ollama/qwen3:4b", temperature=0.7,
        max_tokens=800, base_url=BASE_URL,
        extra_body={"think": False}
    ),
    "D. max_tokens=1200 (넉넉)": LLM(
        model="ollama/qwen3:4b", temperature=0.7,
        max_tokens=1200, base_url=BASE_URL,
    ),
}

TASK_DESC = """
중1 수학 일차방정식 단원에서 객관식 1문제를 출제하세요.
- 보기 5개 (①②③④⑤) 포함
- 한국어로 작성
- 오직 문제만 출력 (해설 없음)
"""

print("=" * 60)
print("CrewAI Agent 레벨 테스트 시작")
print("=" * 60)

for label, llm in configs.items():
    print(f"\n▶ [{label}] 테스트 중...")
    try:
        agent = Agent(
            role="수학 출제자",
            goal="수학 문제 1개 출제",
            backstory="중학 수학 교사입니다.",
            verbose=False,
            allow_delegation=False,
            llm=llm
        )
        task = Task(
            description=TASK_DESC,
            expected_output="객관식 수학 문제 1개 (보기 5개 포함)",
            agent=agent
        )
        crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
        result = crew.kickoff()
        out = str(result)[:150].replace('\n', ' ')
        print(f"  ✅ 성공 | 출력: {out}...")
    except Exception as e:
        print(f"  ❌ 실패 | 오류: {e}")

print("\n" + "=" * 60)
print("테스트 완료")
