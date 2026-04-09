# 🔍 Multi-hop Fact-Checking (RAG-based)

본 프로젝트는 복잡한 주장의 진위 여부를 판단하기 위해 여러 문서에서 근거를 찾아 결합하는 **Multi-hop Retrieval-Augmented Generation (RAG)** 기반의 팩트체킹 시스템입니다. **ChromaDB(Vector)**와 **BM25(Lexical)**를 혼합한 하이브리드 리트리버를 통해 정밀한 근거를 추출하고, 최신 LLM을 활용하여 논리적 추론을 수행합니다.

---


### 🛠 Tech Stack
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-000000?style=for-the-badge&logo=google-cloud&logoColor=white)](https://www.trychroma.com/)
[![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![Scikit-Learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![BM25](https://img.shields.io/badge/BM25-Ranking-blue?style=for-the-badge)](https://en.wikipedia.org/wiki/Okapi_BM25)
[![LangChain](https://img.shields.io/badge/LangChain-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://www.langchain.com/)


### 🧠 Inference Engine
[![OpenAI GPT--4o](https://img.shields.io/badge/OpenAI_GPT--4o-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com/)
[![Qwen3 8B](https://img.shields.io/badge/Qwen3--8B-611AD1?style=for-the-badge)](https://github.com/QwenLM/Qwen)



### 🤝 Collaboration Tools
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/)
[![Google Cloud](https://img.shields.io/badge/Google_Cloud-4285F4?style=for-the-badge&logo=google-cloud&logoColor=white)](https://cloud.google.com/)
[![Notion](https://img.shields.io/badge/Notion-000000?style=for-the-badge&logo=notion&logoColor=white)](https://www.notion.so/)
[![Discord](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/)

---

## 🏗️ System Architecture & Pipeline

본 프로젝트는 `src/` 하위의 모듈별 역할 분담을 통해 체계적인 팩트체킹 파이프라인을 구축하였습니다.

| 모듈 (Module) | 역할 (Task) | 상세 내용 |
| :--- | :--- | :--- |
| **`retrieval`** | **Hybrid Retrieval** | **ChromaDB** 벡터 검색과 **BM25** 키워드 검색을 결합하여 관련 문서 추출 |
| **`reasoning`** | **Multi-hop Logic** | 검색된 단서들을 연결하여 주장의 진위를 따지는 **중간 논리 체인** 생성 |
| **`verification`** | **Final Decision** | 추출된 근거와 추론 과정을 바탕으로 최종 라벨(`SUPPORTED`, `NOT_SUPPORTED`) 확정 |
| **`evaluation`** | **Metric Analysis** | `Recall@k` (검색 정확도) 및 `Macro-F1` (추론 정확도) 통계 산출 및 시각화 |
| **`common`** | **Infrastructure** | API Key, BM25 파라미터 등 프로젝트 전반의 **Configuration** 관리 |
| **`app`** | **System Entry** | 전체 파이프라인 구동 및 인터페이스 제공 |

---

## 📊 Core Performance Metrics (Current)

테스트셋(89 samples)에 대한 현재 시스템의 성능 지표입니다.

* **Retrieval (Recall@10): `0.8090`**
  * 하이브리드 검색을 통해 10개 문서 내에 81% 확률로 정답 근거를 포함함.
* **Reasoning (Macro-F1): `0.5169`**
  * 최종 판별 성능. 현재 LLM의 추론 로직 고도화를 통해 개선 중인 지표입니다.

---

## 📂 Directory Map

```bash
.
├── chroma_db/          # 벡터 스토어 데이터 저장소 (Chroma)
├── data/               # HoVer, FEVEROUS 등 벤치마크 데이터셋
├── docs/               # 시스템 설계 문서 및 API 명세
├── outputs/            # 실험 결과 및 Evaluation 리포트 (CSV, TXT)
└── src/                # 메인 소스 코드 디렉토리
    ├── retrieval/      # BM25 & ChromaDB 하이브리드 검색 엔진
    ├── reasoning/      # Multi-hop 추론 및 CoT 프롬프트 엔진
    ├── verification/   # 최종 진위 검증 로직
    ├── evaluation/     # 통합 평가 및 지표 산출 스크립트
    └── common/         # 공통 Util 및 Config 설정
