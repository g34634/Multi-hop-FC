import re
import datetime
import os

class ProgramExecutor:
    def __init__(self):
        self.state = {}

    def execute_step(self, step_text):
        # 변수 분리 및 치환 로직
        if " = " in step_text:
            var_name, action_part = step_text.split(" = ")
            var_name = var_name.strip()
        else:
            action_part = step_text
            var_name = "label"

        for key, val in self.state.items():
            action_part = action_part.replace(f"{{{key}}}", str(val))

        # Mock 실행 로직
        if "Question" in action_part:
            result = "Christopher Nolan"
        elif "Verify" in action_part:
            result = True if "James Cameron" in action_part else False
        elif "Predict" in action_part:
            result = "REFUTES" if "False" in str(self.state.values()) else "SUPPORTS"
        else:
            result = None
        
        self.state[var_name] = result
        return var_name, result

if __name__ == "__main__":
    executor = ProgramExecutor()
    program = [
        'answer_1 = Question("Who directed the film Interstellar?")',
        'fact_1 = Verify("James Cameron was born in Canada.")',
        'fact_2 = Verify("{answer_1} was born in Canada.")',
        'label = Predict(fact_1 and fact_2)'
    ]

    # 실행 및 로그 내용 구성
    log_content = "--- Verification Execution Log ---\n"
    for s in program:
        v, r = executor.execute_step(s)
        log_line = f"Step: {s} \n=> {v}: {r}\n"
        print(log_line) # 터미널에도 출력
        log_content += log_line

    # [로그 저장 로직]
    os.makedirs("outputs/logs", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = f"outputs/logs/{timestamp}_verification.log"
    
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(log_content)
    
    print(f"✅ 로그가 저장되었습니다: {log_path}")