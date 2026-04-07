# BM25 (Paragraph-based) 작업 계획서

작성일: 2026-04-07
작성자: GitHub Copilot (대행)

목표: `data/processed/hover_with_gold_chunks/hover_with_gold.json` 데이터를 사용하여 문장 단위가 아닌 문단(Paragraph) 단위로 BM25 인덱스를 구축하고, 검색(리트리벌) 성능을 평가할 수 있도록 파이프라인을 설계·구현·인수인계한다.

**전제 조건**
- 레포가 로컬에 클론되어 있고 현재 브랜치는 `feature/data`이다.
- 개발 환경에 `rank-bm25`, `nltk` 등이 설치되어 있어야 한다. (`requirements.txt`에 추가 권장)
- 원본 데이터 파일: `data/processed/hover_with_gold_chunks/hover_with_gold.json` (아래에서는 `hover_with_gold.json`으로 표기)

---

**핵심 결정 사항**
- 데이터 단위: 문단(Paragraph)
  - 이유: 문단 단위는 문장보다 문맥을 잘 유지하므로 BM25의 유사도 산출 시 더 풍부한 토큰 분포를 제공할 수 있음.
  - 구현 방식: 기존 ‘sentence’ 추출 로직을 재사용하되, 문단 기준으로 텍스트를 묶어 `chunks` 리스트를 생성하도록 스크립트/함수를 추가.
  - 담당자 분리: 문단 추출(전처리)은 전처리 담당자에게 맡기거나, 자동화 스크립트를 제공하여 개발 팀이 직접 실행 가능하도록 한다.

---

**산출물(Deliverables)**
- `scripts/prepare_paragraphs.py` : `hover_with_gold.json` → paragraph-level `chunks` JSONL/JSON 파일 생성
- `scripts/build_bm25_index.py` : paragraph `chunks`를 읽어 `BM25Engine.build_index()` 실행 후 피클 인덱스 저장
- `src/data/chunker.py` 에 paragraph 모드(선택적) 함수 또는 `src/data/paragraph_chunker.py` 추가
- 평가 스크립트 `scripts/eval_retrieval.py` : Recall@k, MRR 등 계산
- 문서 `docs/PARAGRAPH_BM25_WORKPLAN.md` (본 문서), `docs/BM25_ENGINE_CHANGES.md` (이미 생성됨)
- requirements 업데이트: `rank-bm25`, `nltk`

---

**세부 작업 단계 (권장 순서, 각 단계의 산출물 포함)**

1) 준비 및 환경설정 (책임: 개발자)
- 작업 내용:
  - 가상환경 생성 및 의존성 설치
  - `requirements.txt`에 `rank-bm25`, `nltk` 항목 추가 (이미 로컬에 설치되어 있으면 건너뜀)
- 명령 예시:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install rank-bm25 nltk
```
- 완료 조건: `scripts/test_bm25.py`가 성공적으로 실행되어 BM25 동작이 확인됨.

2) 데이터 확인 (책임: 전처리 담당자 or 개발자 협업)
- 작업 내용:
  - `hover_with_gold.json` 파일 구조 확인 (각 항목에 `claim`, `uid`, `gold_chunk_ids`, `context_text` 또는 문장 리스트 존재 여부).
  - 문단 추출 정책 결정: (a) 원문에서 빈 줄로 분리, (b) N개의 문장을 묶음, (c) 문단 경계 메타데이터 사용 등.
- 산출물: 문단 추출 규약 문서(간단히 한 줄로 정리) 및 샘플 10개 문단 JSON.

3) 문단 추출 스크립트 구현 (책임: 전처리 담당자 또는 개발자)
- 파일: `scripts/prepare_paragraphs.py`
- 기능:
  - 입력: `data/processed/hover_with_gold_chunks/hover_with_gold.json`
  - 출력: `data/interim/paragraph_chunks.jsonl` 또는 `data/processed/paragraph_chunks.json`
  - 각 chunk 형식: `{"id": "<uid>-p<idx>", "text": "<paragraph text>", "metadata": {"source_uid": <uid>, ...}}`
- 고려사항:
  - 문단이 너무 길면(예: >1000 chars) 내부에서 추가 분할 규칙 적용
  - 메타데이터(원문 id, offset, 원문 문장 수 등) 포함

4) Chunker/데이터 파이프라인 통합 (책임: 개발자)
- 작업 내용:
  - `src/data/chunker.py` 또는 새로운 모듈에 paragraph 모드 지원 함수 추가
  - `BM25Retriever.build_from_chunks`에서 paragraph chunks를 그대로 사용 가능하도록 보장
- 테스트: `scripts/prepare_paragraphs.py` 출력 파일을 로컬에서 불러 `BM25Engine.build_index()`로 인덱스 생성 테스트

5) BM25 인덱스 빌드 스크립트 (책임: 개발자)
- 파일: `scripts/build_bm25_index.py`
- 기능:
  - 입력: `data/interim/paragraph_chunks.jsonl`
  - 동작: 파일을 읽어 `BM25Engine.build_index(chunks)` 호출, 인덱스 저장
- 출력: `data/processed/bm25_paragraph_index.pkl`

6) 평가 (책임: 개발자 / 평가 담당자)
- 파일: `scripts/eval_retrieval.py`
- 기능:
  - 입력: `hover_with_gold.json`의 검증용 subset (또는 train/test split)
  - 동작: 각 claim에 대해 문단 BM25 검색, gold chunk id와 비교하여 Recall@1/3/5/10, MRR 계산
- 측정 항목: Recall@k(1,3,5,10), MRR, latency(쿼리당 평균 응답시간), 인덱스 빌드 시간
- 완료 조건: 성능 지표 테이블(문단 vs 기존 sentence 기준 비교)

7) 최적화 및 운영화 (책임: 개발자)
- 고려사항:
  - 인덱스 크기와 메모리 사용량 (대규모 데이터인 경우 메모리 기반 BM25는 비효율적일 수 있음)
  - 디스크 기반 저장/부분 로딩이나 외부 검색엔진(ElasticSearch, Whoosh) 고려
  - 인덱스 파라미터 튜닝: `k1`, `b`

8) 문서화 및 인수인계 (책임: 개발자)
- 산출물:
  - `docs/PARAGRAPH_BM25_WORKPLAN.md` (본 문서)
  - 실행 가이드(명령어), 평가 결과, 필요한 환경변수 목록
  - 간단한 handoff 체크리스트: (데이터 경로, 스크립트 위치, contact)

---

**역할 제안 (권장)**
- 전처리 담당자: 원본 텍스트에서 paragraph 추출 스크립트 작성 및 샘플 검증
- 개발자(혹은 통합 담당자): paragraph chunks를 받아 `BM25` 인덱스 빌드/저장/질의 파이프라인에 통합, 평가 스크립트 작성
- 리뷰어/품질 담당자: 평가 지표 확인 및 PR 리뷰

---

**실행 예시(간단)**
1) 문단 생성 (전처리 담당자)
```bash
PYTHONPATH=. python3 scripts/prepare_paragraphs.py \
  --input data/processed/hover_with_gold_chunks/hover_with_gold.json \
  --output data/interim/paragraph_chunks.jsonl
```

2) 인덱스 빌드 (개발자)
```bash
PYTHONPATH=. python3 scripts/build_bm25_index.py \
  --chunks data/interim/paragraph_chunks.jsonl \
  --out data/processed/bm25_paragraph_index.pkl
```

3) 평가 실행
```bash
PYTHONPATH=. python3 scripts/eval_retrieval.py \
  --index data/processed/bm25_paragraph_index.pkl \
  --testset data/processed/hover_with_gold_chunks/hover_with_gold.json
```

---

**수용 기준(최종)**
- paragraph 기반 BM25 인덱스를 빌드하고 로컬에서 쿼리할 수 있다.
- 평가 스크립트로 Recall@k(1,3,5) 및 MRR 값을 산출할 수 있다.
- 문단/문장 방식 간 성능 비교 보고서가 제공된다.
- 실행 방법과 의존성(패키지 목록)이 문서화되어 있어 다른 엔지니어가 재현 가능하다.

---

필요하시면 제가 다음 작업을 바로 진행하겠습니다:
- `scripts/prepare_paragraphs.py` 템플릿 스크립트 생성
- `scripts/build_bm25_index.py` 생성 및 통합 테스트 실행
- `scripts/eval_retrieval.py` 기본 구현 및 간단한 성능 리포트 생성

원하시는 다음 작업을 한 줄로 알려주세요.