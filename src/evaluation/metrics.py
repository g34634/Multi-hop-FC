import numpy as np
from sklearn.metrics import f1_score
import datetime
import os

class FactCheckingEvaluator:
    def __init__(self):
        self.all_preds = []
        self.all_golds = []
        self.ret_hits = 0

    def add(self, pred, gold, ret_docs, gold_docs):
        self.all_preds.append(pred)
        self.all_golds.append(gold)
        if any(d in ret_docs[:10] for d in gold_docs):
            self.ret_hits += 1

    def report(self):
        f1 = f1_score(self.all_golds, self.all_preds, average='macro')
        recall = self.ret_hits / len(self.all_golds) if self.all_golds else 0
        
        report_text = "\n📊 최종 평가 보고서\n"
        report_text += f"✅ Macro-F1 Score: {f1:.4f}\n"
        report_text += f"🔍 Retrieval Recall@10: {recall:.4f}\n"
        
        print(report_text) # 터미널 출력
        return report_text

if __name__ == "__main__":
    evaluator = FactCheckingEvaluator()
    evaluator.add("REFUTES", "REFUTES", ["Doc1"], ["Doc1"]) # 샘플 데이터
    
    report_content = evaluator.report()

    # [로그 저장 로직]
    os.makedirs("outputs/logs", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = f"outputs/logs/{timestamp}_metrics.log"
    
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print(f"✅ 평가지표 결과가 저장되었습니다: {log_path}")