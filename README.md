Multi-hop Fact-Checking 시스템
연구 계획서

#0 개요 (Overview)
핵심 문제
1)	단일 문서만으로 진위 파악이 어려운 복잡한 주장(Complex Claims)에 대해 다단계(Multi-hop) 팩트체킹을 수행할 때, 기존 검색 방식(ChromaDB)의 아쉬운 정확도를 개선
2)	검색 근거가 부족해 추론 과정에서 발생하는 오류로 전체 파이프라인이 중단되는 시스템적 불안정성(블랙박스 추론 및 검색 안정성 부족) 해결
제안 방법의 핵심 아이디어
1)	검색기로 키워드 추출 및 클래스화가 적용된 ‘BM25 Retriever’ 활용
2)	‘1)’에 사용자의 복잡한 주장을 Question – Verify – Predict 의 단계적 프로그램으로 분해하는 ‘Program FC(Program-Guided Reasoning) 모델 결합
3)	추론 도중 검색 근거를 찾지 못한 경우 함수가 예외(Exception)를 던져 파이프라인을 중단시키는 대신 기본값(False)을 반환하도록 추론 구조 재설계
	전체 멀티홉 추론 흐름이 일관되게 실행되도록 안정성 향상
기대 효과
-	설명 가능성(Explainability): 추론 프로그램 자체가 산출물로 제공됨. 근거 추적과 디버깅이 용이해 추론 과정과 팩트체킹 결과에 대한 명확한 설명 가능성 확보.
-	데이터 처리 효율: 멀티 프로세싱 및 멀티 스레딩 방식 도입, 대규모 코퍼스 전처리 및 인덱싱 시간을 획기적으로 단축(약 1.5시간 내외)
-	평가 및 개선: Marco-F1과 Recall@10 지표가 포함된 Timestamp 기반 자동 로딩 인프라를 구축해 클래스 불균형 문제 해소. 지속적인 모델 개선 가능.
팀 구성
팀원
담당 모듈
역할 요약

송하현
Data	위키피디아 코퍼스 전처리
(멀티프로세싱/스레딩 최적화)

이주형
Retrieval	키워드 추출 및 클래스화가 적용된 
BM25 기반 검색 모듈 구현 + 인덱싱

박준형
Reasoning	Program FC Q-V-P 추론 모듈 구현 및 
예외 처리 안정화

정찬희
Verification-Eval	Macro-F1/Recall@10 평가 모듈 및 
Timestamp 기반 자동 로깅 시스템 구축


#1 문제 정의 (Problem Definition)
기존 검색 방식의 문제점
기존 ChromaDB와 같은 밀집 검색(Dense Retrieval) 방식은 문맥의 의미론적 유사도에 의존하기 때문에 팩트체킹에 필수적인 고유명사나 핵심 단어를 정확히 매칭하지 못함. 
이에 ‘유사도 함정’에 빠지기 쉬우며 결과적으로 아쉬운 정확도가 나타남.
예시) '라듐 발견자'를 찾을 때 의미 유사도만 높은 '라듐 걸스' 문서를 가져옴.
다단계(Multi-hop) 환경에서는 이러한 부정확한 검색 결과가 다음 추론 단계로 넘어가면 연쇄적인 오류를 발생.
기존 ChromaDB 검색 방식의 구체적인 실패 유형 및 비율은 다음과 같음.
 
• Syntax Error: 모든 hop에서 0% (검색 쿼리 형식 오류 없음)
• Semantic Error: 2-hop 29%, 3-hop 38%, 4-hop 77% (의미 기반 문서 매칭 불일치)
• Token Mismatch Error: 주요 키워드 누락으로 인한 오류
• Structure Error: 논리적 단계 구조 파악 실패
• Incorrect Execution: 부정확한 근거 선택 및 추론 오류의 결과는 홉 수가 증가할수록 의미론적 오류가 급격히 증가함을 보여주며, 순수 밀집 검색(Dense Retrieval) 방식만으로는 다단계 팩트체킹에 충분하지 않음을 입증
(출처: Fact-Checking Complex Claims with Program-Guided Reasoning)
블랙박스 추론의 문제
시스템이 어떠한 논리적 단계를 거쳐 최종 결론(TRUE/FALSE)에 도달했는지 명확한 검증 경로와 증거를 제시하지 못하는 문제 발생. 오답 발생 시 이것이 '검색 실패' 때문인지 '추론 오류' 때문인지 실패 지점의 추적과 디버깅이 어려움. 실무 응용 분야(뉴스 검증, 법률 분석 등)에서는 '어떤 근거로 이 판정을 내렸는지'에 대한 해석 가능성(Explainability)이 필수적. 추론 과정이 불명확한 블랙박스 모델은 신뢰도가 낮아 대안이 될 수 없음.
파이프라인 중단 문제
Program FC 기반의 하위 과제(Question-Verify) 실행 중 필요한 검색 근거를 찾지 못할 경우, 함수가 예외(Exception)를 던지면서 전체 평가 파이프라인의 작동이 완전히 중단됨. 이 문제가 발생하면 해당 주장에 대한 최종 판정 자체를 내릴 수 없어 멀티홉 평가 진행이 불가능한 수준의 심각한 시스템적 불안정을 초래.
실용성에 미치는 영향
•  성능 측면: ChromaDB의 부정확한 검색이 추론 단계로 흘러 들어가 
최종 판정의 오답률을 높이고 Macro-F1 정확도 저하.
•  운영 안정성 측면: 예외 발생 시 파이프라인이 중단되는 문제는 대규모 데이터(HoVer 테스트셋 등) 자동 일괄 처리 환경에서 시스템의 정상적인 운영 불가로 이어짐.
•  신뢰성 및 유지보수 측면: 블랙박스 구조로 인해 사용자는 결과를 신뢰할 수 없게 됨. 로깅 인프라가 없다면 오류(False Positive/Negative)에 대응하거나 지속적인 모델 개선(Iterative Improvement)이 원천적으로 불가능해짐.

#2 배경 및 기준 설정 (Background & Baseline Setting)
멀티홉 팩트체킹 연구 동향
기존의 팩트체킹 모델들은 복잡한 주장에 대한 다단계 추론 능력이 부족하고, 블랙박스 추론 및 데이터 효율성 문제를 겪음. 이러한 문제를 해결하기 위해 학계에서는 다양한 접근을 시도함. Jiang et al. (2020)은 다단계 사실 추출 및 검증을 위한 HoVer 데이터셋을 구축하였고, Pan et al. (2023)은 복잡한 주장을 프로그램 형태로 분해하여 추론 과정을 가시화하는 'Program-Guided Reasoning'을 제안함. 그 밖에도 LLM의 창발적 능력을 활용한 연구(Wei et al., 2022)나 검색-생성-비평을 결합한 Self-RAG(Asai et al., 2024) 등이 시도됨.
BM25와 ProgramFC
BM25
기존 벡터 기반 밀집 검색(ChromaDB Dense 검색) 방식이 문맥 정보에 치중하여 핵심 단어 매칭에서 아쉬운 정확도를 보이는 한계를 극복하기 위해 재조명됨. 본 연구에서는 키워드 추출 방식과 클래스화를 적용하여 상위-K 문서의 정밀도를 크게 향상시킨 베이스라인 검색기로 응용함.
ProgramFC (Program-Guided Reasoning)
기존 모델들의 블랙박스 추론 문제를 해결하기 위해 등장함. 주장(Claim)을 Question, Verify, Predict라는 하위 단계적 프로그램으로 분해하여 명시적인 자연어 중간 단계를 생성. Pan et al. (2023)에 따르면 Few-shot 만으로도 HoVer 데이터셋에서 기존 베이스라인보다 우수한 성능을 보이나, GPT-3.5 이상의 강력한 LLM 의존도 및 검색 근거 부재 시 파이프라인 중단이라는 한계 존재.
HoVer 데이터셋 특성 (송하현 담당)
•  데이터 규모: 약 600만 개 이상(15,517개 .bz2 파일)의 위키피디아 코퍼스 기반
•  증거 품질: 검토자 간 일치도 85% 이상인 Gold Evidence 세트가 주장별 매핑
•  주장의 복잡도: 2~4홉(Hop)의 다단계 탐색이 필요한 주장들
•  클래스 분포: SUPPORTED / NOT_SUPPORTED / NEI(Not Enough Information) 3개 클래스
평가 지표 선정 이유
Macro-F1
SUPPORTED / NOT_SUPPORTED / NEI 라벨 간 클래스 불균형 문제를 해결하기 위해 선택. 단순 정답률(Accuracy)만으로는 불균형한 데이터 환경에서 모델의 종합적이고 객관적인 성능 평가가 어려움.

Recall@10
검색 모듈(Retrieval)의 성능을 객관적으로 평가하기 위해 도입. 초기 검색 단계에서 관련 문서를 상위 10개 안에 포함시키지 못하면(Recall@10 = 0) 이후 추론 모듈이 정상적으로 작동할 수 없으므로, 증거 수집 견고성을 측정하는 핵심 지표로 사용.

#3 제안 방법 (Proposed Method)
전체 시스템 파이프라인
전체 파이프라인은 아래 4개의 모듈이 순차적으로 연결된 아키텍처로 구성됩니다.
입력 (Claim) → BM25 검색 → ProgramFC 추론 → 평가 및 로깅 → 최종 판정 (TRUE/FALSE/NEI)
        ↓                    ↓
    Top-K 문서         Question→Verify→Predict
    (Recall@10)        (명시적 단계)
•  입력: 검증할 팩트체킹 주장(Claim)
•  Retrieval (이주형): BM25 검색 엔진을 통해 Top-K 관련 문서를 반환
•  Reasoning (박준형): Program FC를 활용하여 Question → Verify → Predict 순서로 증거 분석 및 추론 수행
•  Verification-Eval (정찬희): Macro-F1과 Recall@10 메트릭으로 성능 평가 및 로그 기록
•  출력: 최종 판정(TRUE/FALSE/NEI) + 명시적 추론 프로그램 + Timestamp 기반 검증 보고서

시스템 파이프라인 예시
입력(Claim)
    ↓ "Skagen Painter Peder Severin Kroyer favored naturalism along with Theodor Esbern Philipsen and Kristian Zahrtmann." 
┌─────────────────────────────┐
│  Question (질문 생성)        │  LLM 활용
├─────────────────────────────┤
│  Verify (검증)              │  근거 수집
│  → BM25로 문서 검색         │  (Recall@10)
│  → 관련성 평가               │
#1 id=wiki::Kristian_Zahrtmann::0 — score=51.2569 (문장: Kristian Zahrtmann이 Peder Severin Kroyer 등과 함께 자연주의를 선호했다는 설명 — 매우 직접적으로 일치) 
#2 id=wiki::Peder_Severin_Krøyer::0 — score=21.0158 (문장: Peder Severin Kroyer 소개 — 관련 인물 이름이 직접 포함)
#3 id=wiki::Kristian_Zahrtmann::17 — score=20.0431 (같은 문서의 다른 문장)
#4 id=wiki::Peder_Severin_Krøyer::25 — score=19.6105 (같은 인물의 다른 문장, ‘작품 목록’ 등) #5 id=wiki::Peder_Severin_Krøyer::40 — score=19.1703 (메타/미디어 관련 문장)
├─────────────────────────────┤
│  Predict (예측)              │  최종 판정
│  → 근거 기반 판정            │  TRUE/FALSE
│  → 명시적 단계 기록          │
└─────────────────────────────┘
    ↓
추론 결과(Black-box 문제 해결)

BM25 검색 모듈 (담당자: 이주형)
기존 ChromaDB 기반 밀집 검색(Dense Retrieval)의 부족한 정확도를 극복하기 위해 구현. 단순 문맥 유사도 비교를 넘어 팩트체킹에 핵심적인 단어들을 솎아내는 '키워드 추출 방식'과 이를 체계화하는 '클래스화 기법'을 적용해 상위-K(Top-K) 문서 검색의 정밀도 향상. 추가로 ChromaDB Dense 검색을 하이브리드 방식의 보조로 활용하여 BM25의 단점을 보완하는 방향으로 검색기를 구축.

ProgramFC 추론 모듈 (담당자: 박준형)
복잡한 주장을 한 번에 판정하지 않고, Question, Verify, Predict라는 단계적 프로그램으로 분해하여 더 안정적으로 검증하도록 설계. 핵심 개선점은 '예외 처리 안정화(Exception Handling)'. 기존에는 검색 근거를 찾지 못하면 함수가 오류를 발생시켜 파이프라인 전체가 멈췄으나, 근거 부족 시 기본값인 False를 반환하도록 재설계 진행. 이를 통해 대규모 멀티홉 평가 데이터셋에서도 중간 오류로 인해 
흐름이 끊기지 않고 끝까지 완료되는 전체 추론 흐름의 안정성을 확보.

데이터 전처리 및 인덱싱 (담당자: 송하현)
총 15,517개의 위키피디아 .bz2 압축 파일을 순차적으로 처리할 경우 약 4.3시간이 걸리는 병목을 기술적으로 해결. 파일 단위 분할 로드 + CPU 멀티 프로세싱(Multi-processing)을 적용하여 텍스트 정규화 및 토크나이징 전처리 시간을 약 1.5시간으로 단축. 전처리 완료 데이터는 Parquet 형식으로 저장되며, BM25 인덱스 생성 작업에는 멀티 스레딩(Multi-threading) 방식을 적용하여 30분 내외로 완료하도록 최적화. 중간 실패 시 복구 가능하도록 단계별 저장 로직도 구현.

#4 데이터셋 및 평가 설정 (Dataset & Evaluation Setup)
HoVer 데이터셋 구성
HoVer 데이터셋은 SUPPORTED와 NOT_SUPPORTED 두 가지 클래스로 구성.
HoVer Dataset (18,171개 Claims)
│
├─ SUPPORTED: 11,023 (60.66%)
│
└─ NOT_SUPPORTED: 7,148 (39.34%)

홉(Hop) 분포
├─ 2-hop: 9,052 (49.82%)
├─ 3-hop: 6,084 (33.48%)
└─ 4-hop: 3,035 (16.70%)
 

본  팀은 기존 HoVer의 훈련(Train) 데이터를 기반으로 테스트셋으로 정제하여 활용.
 
테스트 세트 정의
기존 HoVer 벤치마크는 2~4홉(Hop)의 다단계 탐색이 필요한 주장들로 이루어져 있으나, 현재 연구팀의 테스트셋은 1~2홉 주장을 포함하여 구성되어 있음. 현재 통합 평가 모듈에서는 파이프라인 작동 확인을 위해 우선 10개의 HoVer 데이터셋 샘플을 대상으로 평가를 수행하여 성공적인 작동을 검증 완료한 상태.
Gold Evidence 매핑
데이터 전처리 과정에서 HoVer 훈련 데이터를 테스트셋으로 정제하며 정답 증거(Golden evidence)를 맵핑. 이때 검토자 간의 일치도(Agreement)가 85% 이상인 신뢰도 높은 증거 세트만을 각 주장당 식별하여 매핑하는 방식으로 검증 및 구축.
최종 데이터 형식
15,517개의 위키피디아 .bz2 압축 파일(약 600만 문서 이상)은 파일 단위로 분할 로드되어 텍스트 정규화 및 토크나이징 전처리를 거친 뒤 Parquet 형식으로 저장. 저장된 Parquet 데이터를 기반으로 모든 문서의 가중치를 계산하여 BM25 검색기용 인덱스를 생성, 작업 중단 시 복구가 가능하도록 단계별 저장 구조를 갖추고 있음.
#5 실험 설계 (Experiment Design)
실험 조건 (총 4가지)
•  실험 1 (Retrieval 성능): BM25 단독(기준선) vs BM25 + Dense 결합(변형) 
— Top-K 정확도 비교
•  실험 2 (Reasoning 성능): Gold 검색 결과를 Program FC에 직접 입력하는 조건(상한선 측정)
•  실험 3 (완전 시스템): BM25 검색 → Program FC 추론 → 평가로 이어지는 전체 파이프라인
•  실험 4 (홉 깊이 비교): 1홉 vs 2홉 주장 조건으로 나누어 다단계 추론 견고성 비교

기대 성능
•  완전 통합 시스템 (BM25 → ProgramFC): 최종 목표 Macro-F1 Score 65~75%
•  BM25 단독 (기준선): 가장 낮은 성능 예상 (문맥 정보 부족)
•  ProgramFC + Gold 검색: 상한선(Upper Bound) 수준의 Macro-F1 및 Accuracy 기대
Retrieval (Recall@10): HoVer 2-hop 77.13% / 3-hop 59.17% / 4-hop 49.93%
Reasoning (Macro-F1): HoVer 2-hop 69.36% / 3-hop 60.63% / 4-hop 59.16% (N=1 기준)
Ablation Study 목표
1)	각 컴포넌트(BM25 검색 모듈, Program FC 추론 모듈)의 개별 기여도를 분석하고 성능 병목 지점을 파악하여 최적화하는 것. 
2)	BM25에 Dense 검색을 추가했을 때 검색 성능 향상폭을 측정하고, Gold 검색 결과를 넣은 추론 성능과 실제 검색 결과를 넣은 통합 추론 성능을 비교함으로써 '검색 실패'가 '추론 오류'로 이어지는 오류 전파를 파악하는 것.
제어 변수
독립 변수 (조작 변인)
•  검색 방식 (BM25 단독 vs BM25+Dense)
•  추론 입력 데이터 질 (실제 검색 결과 vs Gold 검색 결과)
•  주장의 복잡도 (1홉 vs 2홉)
통제 변수
•  전처리가 완료된 HoVer 테스트 데이터셋 동일 환경
•  Scikit-learn 기반의 Macro-F1 및 Recall@10 평가 지표 동일 적용
•  ProgramFC의 예외 처리(오류 안정화) 로직 항상 켜둔 상태 유지

#6 개발 계획 (Development Plan)
팀원별 역할
•  송하현: Data — 위키 코퍼스 전처리, 문장의 문단화
•  이주형: Retrieval — BM25 검색기 구현, ChromaDB를 이용한 하이브리드 구현
•  박준형: Reasoning — Program FC 기반 추론 담당
•  정찬희: Verification-Eval — 통합 평가 모듈 구축, 공통 코드 관리

현재 확인된 사항
•  Data 모듈: 코퍼스 전처리 약 1.5시간 소요, BM25 인덱싱 약 30분 소요
•  Verification-Eval 모듈: 10개 샘플 데이터로 파이프라인 작동 1차 검증 완료

#7 기준 비교 및 성공 기준 (Baseline Comparison & Success Criteria)
기준선 (Baseline)
•  Retrieval 기준: 단순 문장 수준의 BM25 기반 검색
•  Reasoning 기준: Gold 검색 결과를 그대로 입력받는 ProgramFC 단독 추론
핵심 성공 기준
•  통합 파이프라인(BM25 → ProgramFC) 최종 목표: Macro-F1 Score 65~75% 달성
•  통합 시스템 성능이 각 모듈 단독 성능을 능가
모듈별 성공 기준
•  Retrieval 모듈 (Recall@10): 2-hop 77.13% / 3-hop 59.17% / 4-hop 49.93% — 키워드 추출 및 BM25 클래스화를 통해 상위-K 검색 정밀도 및 정확도 향상 달성
•  Reasoning 모듈 (Macro-F1): 2-hop 69.36% / 3-hop 60.63% / 4-hop 59.16% — 예외 처리 안정화로 멀티홉 추론 중단 방지, 전체 파이프라인 흐름 안정적 완료 달성
•  Verification-Eval 모듈: Macro-F1 도입 + Timestamp 기반 자동 로깅으로 Iterative Improvement 인프라 완성
실패 기준
•  치명적 실패 1: Recall@10 = 0 (검색 모듈이 관련 문서를 전혀 찾지 못하는 상태)
•  치명적 실패 2: 예외 처리 미흡으로 전체 파이프라인 중단

#8 검증 및 오류 분석 (Validation & Error Analysis)
예상 오류 유형 (5가지)
•  검색 실패: BM25 검색기에서 관련 문서를 찾지 못해 Recall@10 = 0이 되는 오류
•  순위 오류: 관련 문서는 검색되나 Top-10 밖으로 순위가 밀려나는 오류
•  추론 오류: 예외 처리로 인해 실제로 거짓(False)인 경우와 증거 부족(Evidence missing) 상태가 동일하게 처리되어 판단이 부정확해지는 문제
•  데이터셋 편향: HoVer 테스트셋 자체가 특정 도메인에 편향되어 있을 가능성
•  모듈 불일치: 각 모듈 간 입력/출력 형식의 차이로 인해 발생하는 오류
오류 분석 방법
Timestamp 기반의 자동 로깅 시스템을 활용하여 검증 리포트를 자동 생성하고 오류를 추적. 오답 케이스를 거짓 양성(False Positive)과 거짓 음성(False Negative)으로 분류하여 상세 분석 로그를 출력하는 방식으로 분석을 진행.
모델 개선 방향 (Iterative Improvement)
자동 로깅 인프라를 활용하여 추론 로그와 평가지표를 실시간으로 축적하고, 반복적으로 모델을 개선. 분석 과정에서 발견된 'False vs Evidence Missing' 구분 불가 한계를 극복하기 위해 이후 모듈에서는 두 상태를 별도로 구분하는 상태 체계를 재설계하여 추론 안정성과 정확도를 동시에 높일 계획.
신뢰성 검증
•  검토자 간 일치도 85% 이상인 Gold Evidence 데이터만 매핑 사용
•  Scikit-learn 기반 통합 평가 모듈(Macro-F1, Recall@10)로 객관적 지표 산출 보장

#9 인사이트 (Insights)
학술적 인사이트
•  멀티홉 팩트체킹 분야 기여: 기존 팩트체킹 모델의 블랙박스 추론 한계를 극복. 복잡한 주장을 Question-Verify-Predict의 단계적 프로그램으로 분해함으로써 검증 경로와 명시적 추론 근거를 제시하는 해석 가능성(Explainability)을 확보할 수 있음을 확인.
•  새로운 발견: 예외 발생 시 기본값(False)을 반환하도록 설계하여 시스템 안정성은 높였으나, 이 방식이 '실제로 거짓(False)인 경우'와 '단순히 검색 근거를 찾지 못한 경우(Evidence missing)'를 구별하지 못하게 만든다는 새로운 논리적 한계를 발견.
기술적 개선점
•  Retrieval 측면: 키워드 추출 + 클래스화 적용 BM25 검색기 도입으로 상위 검색 문서의 정밀도 향상.
•  Data 처리 혁신: 순차 처리(4.3시간) → 멀티프로세스/스레드(전처리 1.5시간, 인덱싱 30분)로 획기적 단축, 중간 실패 시 단계별 복구 가능 파이프라인 구축.
•  Eval 프레임워크: Macro-F1 + Recall@10 도입 및 가상 환경 격리/의존성 충돌 해결로 안정적인 평가 시스템을 구축.
실무 적용 파급 효과
•  Iterative Improvement 인프라: Timestamp 기반으로 추론 로그와 평가 지표가 실시간 자동 축적. 서비스 운영 중에도 오답 케이스(False Positive/Negative)를 추적하고 지속적인 모델 성능 개선.
•  실무 데이터 처리 효율성: 멀티프로세스/스레드 기반 전처리 기법과 키워드 추출 방식이 결합된 검색 엔진 아키텍처를 실제 응용 서비스(뉴스 검증, 법률 분석 등)에 활용해 레이턴시 감소 기대.
한계점과 향후 개선 방향
현재 설계의 제약 (한계점)
'예외 발생 시 기본값(False) 반환' 로직으로 인해 '진짜 거짓인 주장'과 '문서가 없어 판별할 수 없는 주장(Missing)'이 섞여 결과가 오염되는 제약 존재.
향후 개선 방향
False와 Evidence Missing을 명확히 구분하는 새로운 상태 체계를 별도로 재설계하여 추론 파이프라인의 시스템적 안정성과 판정 정확도를 모두 확보하는 방향으로 발전 목표.

#10 참고 문헌 (References)
Pan, L. et al. (2023)
Fact-checking complex claims with program-guided reasoning. Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers), pp. 6981–7004.   ▶ 핵심 추론 모듈(ProgramFC) 아키텍처의 기반 논문. Q-V-P 단계적 프로그램 분해를 통한 팩트체킹 방법론 제시.
Jiang, M. et al. (2020)
HoVer: A dataset for many-hop fact extraction and claim verification. Findings of the Association for Computational Linguistics: EMNLP 2020, pp. 3295–3309.   ▶ 베이스라인 벤치마크 및 검증용 테스트 데이터로 사용되는 HoVer 데이터셋을 처음으로 구축한 논문.
Wei, J. et al. (2022)
Emergent abilities of large language models. arXiv preprint arXiv:2206.07682.   ▶ LLM이 규모가 커짐에 따라 보여주는 창발적 추론 능력을 다룬 논문. 거대 모델 의존성 관련 학술적 배경 연구로 활용.
Asai, A. et al. (2024)
Self-RAG: Learning to retrieve, generate, and critique for self-improved generation. The Twelfth International Conference on Learning Representations.   ▶ 검색-생성-비평을 결합한 최신 멀티홉 RAG 시스템 연구 동향 참고를 위해 인용.
<img width="472" height="697" alt="image" src="https://github.com/user-attachments/assets/a10d3939-7052-491d-ad70-c7cd72067052" />
