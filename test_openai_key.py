import os
import urllib.request
import urllib.error
import json
from dotenv import load_dotenv

# .env 로드
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key or api_key == "your_api_key_here" or api_key == "미리_발급받으신_키를_여기에_넣어주세요":
    print("ERROR: .env 파일에 유효한 OPENAI_API_KEY가 설정되지 않은 것 같습니다.")
    exit(1)

url = "https://api.openai.com/v1/models"
req = urllib.request.Request(url)
req.add_header("Authorization", f"Bearer {api_key}")

try:
    # 모델 리스트 API 호출
    with urllib.request.urlopen(req) as response:
        if response.status == 200:
            data = json.loads(response.read().decode('utf-8'))
            print("=========================================")
            print("✅ SUCCESS: OpenAI API 키가 정상 작동합니다!")
            print(f"✅ 사용 가능한 모델 목록 추출 성공 (총 {len(data.get('data', []))}개 확인)")
            print("=========================================")
except urllib.error.HTTPError as e:
    print("=========================================")
    print(f"❌ FAILED: API 키 검증 실패")
    print(f"❌ 사유: {e.code} {e.reason}")
    print("=========================================")
    exit(1)
except Exception as e:
    print("=========================================")
    print(f"❌ FAILED: 알 수 없는 오류 발생 -> {e}")
    print("=========================================")
    exit(1)
