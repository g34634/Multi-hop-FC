# PARAGRAPH BM25 - 변경 요약 (2026-04-07)

이 문서는 `PARAGRAPH_BM25_WORKPLAN.md`에 추가로 덧붙이는 변경 요약입니다. PR과 인수인계에 사용할 수 있도록 작업 항목과 구현 결과를 간결히 정리했습니다.

작성일: 2026-04-07
작성자: 이주형 (수정 및 자동화 보조: GitHub Copilot)

## 변경된 파일(추가/수정)
- src/retrieval/bm25_engine.py (수정)
  - `bm25_k1`, `bm25_b`, `bm25_index_path` 런타임 폴백 추가
  - `Config` 직접 임포트 제거(테스트시 HF_TOKEN 예외 회피)
- scripts/test_bm25.py (추가)
- scripts/build_bm25_index.py (추가)
- scripts/spotcheck_paragraph_bm25.py (추가)
- scripts/query_bm25.py (추가)
- tests/test_bm25_engine.py (추가)
- docs/BM25_ENGINE_CHANGES.md (추가)
- docs/BM25_TESTING.md (추가)
- requirements.txt (수정): rank-bm25, nltk, pytest 항목 추가

## 구현된 기능(요약)
- BM25 엔진의 독립 실행성 확보: 별도 Config 환경 없이 BM25 초기화 가능
- 청크(json/jsonl)로부터 BM25 인덱스(피클) 생성/저장/로드
- 스팟체크용 문단 샘플러 및 검증 스크립트
- 쿼리용 CLI로 직접 테스트 가능한 도구 제공
- 간단한 단위 테스트와 테스트 가이드 문서화

## 검증 결과(요약)
- 소규모(수백 청크) 데이터에서 인덱스 빌드 및 쿼리 정상 동작 확인
- 샘플 기반 스팟체크에서 top-5 내 gold chunk 포함 비율(샘플에서 100% 확인)

## 권장 후속 작업
- `PARAGRAPH_BM25_WORKPLAN.md`에 본 파일의 요약 내용을 병합(문서 업데이트)
- `prepare_paragraphs.py` 및 `eval_retrieval.py` 구현 (전처리 담당자와 협업)
- `--max_chunks` 옵션 및 인덱스 메타 저장 기능 추가
- PR 생성: `feature/retrieval` 브랜치에서 변경사항 검토 후 병합

---

파일 목록과 변경 사항은 로컬에서 확인 가능하며, 요청 시 PR 템플릿과 커밋 메시지 추천안을 추가로 생성해 드립니다.
