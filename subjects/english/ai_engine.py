import json
import re
import time
import httpx
from openai import OpenAI
import os

DEFAULT_MODEL = "gpt-4o-mini" # User wants to keep using gpt-4o-mini or gpt-4o, let's stick to gpt-4o-mini for cost/speed unless it needs 4o. I'll use gpt-4o-mini as default, or whatever is passed.

def _get_client():
    http_client = httpx.Client(verify=False)
    api_key = os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=api_key, http_client=http_client)

def _call_gpt(client, prompt: str, temperature: float = 0.4, max_tokens: int = 4096) -> str:
    """OpenAI GPT API 호출"""
    for attempt in range(3):
        try:
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant for English teachers. You generate JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="gpt-4o-mini", # Will use gpt-4o-mini for english as per previous discussions if possible, or gpt-4o.
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            if "429" in err or "rate" in err.lower() or "limit" in err.lower():
                wait = 5 * (attempt + 1)
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("OpenAI API 호출 실패")

def _parse_json(raw: str):
    raw = re.sub(r"^```(?:json)?\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        arr = re.search(r"\[.*\]", raw, re.DOTALL)
        obj = re.search(r"\{.*\}", raw, re.DOTALL)
        for m in [arr, obj]:
            if m:
                try: return json.loads(m.group(0))
                except Exception: pass
        raise ValueError("AI 응답 형식이 올바르지 않습니다.")

def generate_english_problems(text: str, level: str, q_types: list) -> dict:
    """문제 + 단어장 단일 호출"""
    client = _get_client()
    
    labels = {
        "blank":      "blank fill-in",
        "topic":      "topic objective choice",
        "grammar":    "grammar correction",
        "true_false": "true/false content check",
        "vocab":      "vocab meaning definition",
    }
    
    # 분배 로직: 10문제를 요청된 유형 개수만큼 최대한 균등하게 나눔
    total_q = 10
    counts = {t: total_q // len(q_types) for t in q_types}
    for i in range(total_q % len(q_types)):
        counts[q_types[i]] += 1
        
    type_desc = "\n".join(f"- {labels[t]}: GENERATE EXACTLY {counts[t]} QUESTIONS." for t in q_types)

    # 요청된 유형에 대해서만 JSON 템플릿을 생성합니다.
    json_examples = []
    if "blank" in counts:
        json_examples.append(f'  "blank": [ /* You MUST generate EXACTLY {counts["blank"]} objects here */\n    {{ "instruction": "다음 빈칸에 알맞은 것을 고르시오.", "question": "The AI tool was designed to _______ the data.", "choices": ["① analyze", "② ignore", "③ delete", "④ create", "⑤ copy"], "answer": "① analyze", "explanation": "한국어 해설" }}\n  ]')
    if "topic" in counts:
        json_examples.append(f'  "topic": [ /* You MUST generate EXACTLY {counts["topic"]} objects here */\n    {{ "instruction": "다음 글의 주제로 가장 적절한 것은?", "question": "이 글의 메인 주제는 무엇인가?", "choices": ["①...", "②...", "③...", "④...", "⑤..."], "answer": "...", "explanation": "한국어 해설" }}\n  ]')
    if "grammar" in counts:
        json_examples.append(f'  "grammar": [ /* You MUST generate EXACTLY {counts["grammar"]} objects here */\n    {{ "instruction": "다음 중 어법상 틀린 것을 고르시오.", "question": "The software *are* being updated.", "choices": ["① is", "② are", "③ were", "④ be", "⑤ been"], "answer": "② are", "explanation": "한국어 해설 (오답인 이유 설명)" }}\n  ]')
    if "true_false" in counts:
        json_examples.append(f'  "true_false": [ /* You MUST generate EXACTLY {counts["true_false"]} objects here */\n    {{ "instruction": "다음 문장이 윗글의 내용과 일치하면 T, 일치하지 않으면 F를 고르시오.", "question": "The AI tool is only used by police.", "answer": "T", "explanation": "한국어 해설" }}\n  ]')
    if "vocab" in counts:
        json_examples.append(f'  "vocab": [ /* You MUST generate EXACTLY {counts["vocab"]} objects here */\n    {{ "instruction": "다음 밑줄 친 단어의 문맥상 의미로 가장 적절한 것은?", "question": "The system caused a huge <u>controversy</u>.", "choices": ["① 논란", "② 평화", "③ 기쁨", "④ 슬픔", "⑤ 이익"], "answer": "① 논란", "explanation": "한국어 해설" }}\n  ]')

    json_fields_str = ",\n".join(json_examples)

    prompt = f"""
You are an expert English teacher with 20 years of experience, specializing in the '{level}' level for Korean middle school students.

Based on the raw news article provided below, you must perform the following tasks:
1. Adapt/Extract a suitable reading passage (10-20 sentences). It must be well-structured with clear paragraph breaks (use \n\n for paragraphs).
2. Generate EXACTLY 10 test questions in total, strictly adhering to this exact distribution:
{type_desc}
3. Create a vocabulary list of exactly 10 essential words from the adapted passage.

RAW ARTICLE:
\"\"\"
{text[:4000]}
\"\"\"

Return ONLY a valid JSON object with the following structure:
{{
  "adapted_passage": "The adapted/summarized English passage with proper \\n\\n paragraph breaks...",
{json_fields_str},
  "vocab_list": [
    {{
      "word": "vocabulary_word",
      "pos": "noun",
      "definition_en": "English definition",
      "definition_ko": "한국어 뜻",
      "example": "A new example sentence."
    }}
  ]
}}

CRITICAL RULES - FAILURE IS NOT AN OPTION:
1. You MUST generate the EXACT NUMBER of questions requested for EACH type in the arrays above. The total MUST sum to exactly 10!
2. Do not just output 1 example per array! Fill the arrays with the requested count!
3. For "grammar" questions: You MUST intentionally introduce exactly ONE grammatical error in the `question` sentence. The choices must list 5 parts of the sentence, including the error. The `answer` MUST be the grammatically INCORRECT choice. The explanation must explain why it is wrong.
4. For "blank" and "grammar", the `question` field MUST be an EXACT English sentence taken from your `adapted_passage`. ABSOLUTELY NO KOREAN in the `question` field!
5. For "vocab" questions: The `question` field MUST be the exact English sentence from the passage. You MUST enclose the target vocabulary word in `<u>` and `</u>` HTML tags (e.g. "The system caused a huge <u>controversy</u>.").
6. For "blank" and "grammar", the `choices` MUST be entirely in English. For "vocab", choices can be Korean meanings.
7. `adapted_passage` MUST be between 10 to 20 sentences and include at least 2 paragraph breaks (\\n\\n).
8. The reading level must perfectly match '{level}' students.
"""

    raw = _call_gpt(client, prompt, temperature=0.3, max_tokens=6000)
    data = _parse_json(raw)

    questions = {k: v for k, v in data.items() if k not in ["vocab_list", "adapted_passage"] and isinstance(v, list)}
    vocab = data.get("vocab_list", [])
    adapted_passage = data.get("adapted_passage", text)

    return {"questions": questions, "vocab": vocab, "adapted_passage": adapted_passage}

