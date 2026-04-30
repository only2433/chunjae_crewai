"""
qwen3:4b LLM 호출 디버그 테스트
think=False / max_tokens 조합 확인
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crewai import LLM

def test_llm(label, llm):
    print(f"\n{'='*50}")
    print(f"[테스트] {label}")
    try:
        # LLM.call() 직접 호출
        resp = llm.call(
            messages=[{"role": "user", "content": "1+1은 얼마입니까? 한 줄로만 답하세요."}]
        )
        print(f"  ✅ 응답: {str(resp)[:200]}")
        return True
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        return False

# --- 조합 1: 기존 (think 없음, max_tokens 없음) ---
llm_old = LLM(
    model="ollama/qwen3:4b",
    temperature=0.7,
    base_url="http://localhost:11434"
)

# --- 조합 2: extra_body think=False ---
llm_no_think = LLM(
    model="ollama/qwen3:4b",
    temperature=0.7,
    max_tokens=500,
    base_url="http://localhost:11434",
    extra_body={"think": False}
)

# --- 조합 3: max_tokens만 제한 (think 없음) ---
llm_limited = LLM(
    model="ollama/qwen3:4b",
    temperature=0.7,
    max_tokens=500,
    base_url="http://localhost:11434"
)

# --- 조합 4: num_ctx 명시 + think=False ---
llm_ctx = LLM(
    model="ollama/qwen3:4b",
    temperature=0.7,
    max_tokens=500,
    base_url="http://localhost:11434",
    extra_body={"think": False, "options": {"num_ctx": 2048}}
)

results = {}
results["기존(제한 없음)"]             = test_llm("기존(제한 없음)", llm_old)
results["max_tokens=500, think=False"] = test_llm("max_tokens=500, think=False", llm_no_think)
results["max_tokens=500, think 없음"]  = test_llm("max_tokens=500, think 없음", llm_limited)
results["think=False + num_ctx=2048"]  = test_llm("think=False + num_ctx=2048", llm_ctx)

print("\n" + "="*50)
print("📊 결과 요약:")
for k, v in results.items():
    print(f"  {'✅' if v else '❌'} {k}")
