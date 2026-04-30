import os
from dotenv import load_dotenv
from crewai import LLM

load_dotenv()

# 1. 출제용 로컬 모델 (에이전트 1)
#    ⚠️ qwen3:4b + CrewAI: max_tokens 설정 시 Thinking 토큰이 소비되어
#       "Final Answer:" 생성 실패 → max_tokens 설정 금지
local_qwen_llm = LLM(
    model="ollama/qwen3:4b",
    temperature=0.7,
    base_url="http://localhost:11434"
    # max_tokens 금지 - qwen3 think 토큰 충돌
)

# 1-b. 해설 전용 로컬 모델 (에이전트 3)
#      속도 최적화는 agents.py backstory/goal 프롬프트로 유도
explainer_llm = LLM(
    model="ollama/qwen3:4b",
    temperature=0.5,           # 정확성 우선
    base_url="http://localhost:11434"
    # max_tokens 금지 - 동일 이유
)

openai_api_key = os.getenv("OPENAI_API_KEY")
_valid_key = (
    openai_api_key
    and openai_api_key != "your_api_key_here"
    and openai_api_key != "예시_키"
)

# 2. 검수용 (에이전트 2/4) - 무조건 GPT
if _valid_key:
    reviewer_llm = LLM(
        model="gpt-4o-mini",
        temperature=0.1,
        api_key=openai_api_key
    )
else:
    print("[경고] OPENAI_API_KEY가 설정되지 않아, 감수관도 로컬을 임시 사용합니다.")
    reviewer_llm = local_qwen_llm

# 3. 빠른 모드용 GPT (use_fast=True 시 출제+해설 모두 GPT 사용)
if _valid_key:
    fast_llm = LLM(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=openai_api_key
    )
else:
    fast_llm = local_qwen_llm  # fallback
