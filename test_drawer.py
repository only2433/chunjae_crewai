import os
import re
import subprocess
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def run_python_illustrator_standalone(prob_text):
    prompt = f"""You are an expert Python data visualization engineer.
Your task is to write a Python script using `matplotlib` to draw a precise, professional mathematical diagram for the following elementary school math problem.
Problem: {prob_text}

Requirements:
1. The script MUST save the plot directly to exactly 'ui/problem_image.png' using `plt.savefig('ui/problem_image.png', bbox_inches='tight', dpi=300)`. Do NOT use `plt.show()`.
2. Support Korean font on Windows by adding:
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False
3. Make the drawing visually appealing, clean, and educational. Add simple colors.
4. Draw exact numeric labels if the problem has them. If it's a 3D shape like cylinder or cone, try to draw it cleanly with axis formatting turned off.
5. If drawing 3D geometry or using specific modules (like `numpy`), explicitly import them (e.g., `import numpy as np`, `from mpl_toolkits.mplot3d import Axes3D, art3d`).
6. Only output pure Python code inside a ```python ``` block. Do not write any other explanations.

Make sure the code is syntactically correct and imports all necessary modules."""
    
    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.1
        )
        output = response.choices[0].message.content
        match = re.search(r'```python\n(.*?)\n```', output, re.DOTALL)
        if not match: return None
        
        raw_code = match.group(1)
        
        # 안정성 강화 및 샌드박싱 로직 추가 (허용되지 않은 모듈 차단 및 메모리 누수 방지)
        forbidden_modules = ['os', 'sys', 'subprocess', 'shutil', 'requests', 'urllib', 'socket']
        filtered_lines = []
        for line in raw_code.split(chr(10)):
            if line.startswith('plt.rcParams'):
                continue
            
            is_forbidden = False
            for mod in forbidden_modules:
                if re.search(rf'\bimport\s+{mod}\b|\bfrom\s+{mod}\b', line):
                    print(f"⚠️ [보안 경고] 허용되지 않은 모듈 임포트 차단: {line.strip()}")
                    is_forbidden = True
                    break
            
            if not is_forbidden and "__import__" not in line and "eval(" not in line and "exec(" not in line:
                filtered_lines.append(line)
                
        indented_code = chr(10).join('    ' + line for line in filtered_lines)
        
        safe_code = f"""import matplotlib.pyplot as plt
import numpy as np
import traceback
import sys

# 한글 폰트 글로벌 세팅
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

try:
{indented_code}
except Exception as e:
    print('Error executing generated visualization code:')
    traceback.print_exc()
    sys.exit(1)
finally:
    plt.close('all')
"""
        script_path = "temp_drawer.py"
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(safe_code)
        
        if not os.path.exists("ui"):
            os.makedirs("ui")
            
        print(f"\n⚙️ 렌더링 코드 실행 준비 완료. (대상: {prob_text[:15]}...)")
        subprocess.run(["python", script_path], check=True, capture_output=True, timeout=15)
        
        if os.path.exists(script_path):
            os.remove(script_path)
            
        img_dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "problem_image.png")
        if os.path.exists(img_dest):
            return img_dest
        return None
    except subprocess.CalledProcessError as e:
        print(f"❌ 런타임 오류: {e}")
        if os.path.exists("temp_drawer.py"): os.remove("temp_drawer.py")
        return None
    except Exception as e:
        print(f"❌ 생성 에러: {e}")
        if os.path.exists("temp_drawer.py"): os.remove("temp_drawer.py")
        return None

if __name__ == "__main__":
    print("🚀 Matplotlib 파이썬 이미지 생성기 실전 테스트!!\n")
    
    test_1 = "어느 반 학생들의 좋아하는 과일을 조사했습니다. 사과 10명, 바나나 7명, 포도 5명, 귤 8명입니다. 막대그래프를 그려주세요."
    res_1 = run_python_illustrator_standalone(test_1)
    if res_1:
        print(f"✅ 테스트 1 (막대그래프) 성공! 이미지 경로: {res_1}")
        target_path_1 = res_1.replace(".png", "_bar.png")
        if os.path.exists(target_path_1):
            os.remove(target_path_1)
        os.rename(res_1, target_path_1)
            
    test_2 = "밑면의 반지름이 5cm이고 높이가 10cm인 원뿔을 그려주세요. 길이 표시를 명확히 해주세요."
    res_2 = run_python_illustrator_standalone(test_2)
    if res_2:
        print(f"✅ 테스트 2 (원뿔/3D) 성공! 이미지 경로: {res_2}")
        target_path_2 = res_2.replace(".png", "_cone.png")
        if os.path.exists(target_path_2):
            os.remove(target_path_2)
        os.rename(res_2, target_path_2)
