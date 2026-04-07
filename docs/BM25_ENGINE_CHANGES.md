# BM25 Engine 변경 기록 (인수인계용)

작성일: 2026-04-07
작성자: GitHub Copilot (작업 대행)

이 문서는 `feature/data` 브랜치 작업 중 `BM25` 관련으로 변경한 내용과 이유, 테스트 방법, 다음 단계 등을 정리한 인수인계 문서입니다.

---

## 요약
- `src/retrieval/bm25_engine.py`에 안전한 기본값(fallback)을 추가하여, 원래 `Config`에 정의되지 않은 경우에도 BM25 엔진이 동작하도록 수정했습니다.
- 테스트용 스크립트 `scripts/test_bm25.py`를 추가하여 간단한 샘플 문서들로 인덱스 빌드/쿼리 동작을 확인할 수 있게 했습니다.
- 모듈 임포트 시 `src.common.config.Config`의 환경변수 검사(HF_TOKEN)로 인해 테스트가 실패하는 문제를 우회하기 위해 `bm25_engine.py`에서 `Config`를 직접 임포트하지 않도록 변경하고, 타입 애너테이션을 제거했습니다.

---

## 변경된 파일
- `src/retrieval/bm25_engine.py`
  - 추가/수정 내용:
    - `bm25_k1`, `bm25_b`, `bm25_index_path` 속성이 `Config`에 없을 경우의 기본값을 설정하도록 추가.
    - 모듈 최상단에서 `from src.common.config import Config` 임포트를 제거(환경변수 검사에 의해 임포트 시 예외 발생 우회).
    - `__init__`의 타입 애너테이션(`config: Config`)을 제거.
  - 이유: 테스트 및 외부 통합 시 `Config` 클래스가 HF_TOKEN 체크 등으로 예외를 발생시키는 경우가 있어, BM25 엔진 자체를 독립적으로 초기화/테스트할 수 있게 하기 위함.

- `scripts/test_bm25.py`
  - 간단한 샘플 `chunks`로 BM25 인덱스를 만들고 쿼리하는 스모크 테스트 스크립트 추가.
  - 이 스크립트는 레포 루트를 `PYTHONPATH`로 설정한 상태에서 실행해야 `src` 패키지 임포트가 정상 동작합니다.

- `docs/BM25_ENGINE_CHANGES.md`
  - (이 파일) 변경 사항 기록 및 실행/테스트 가이드 포함.

---

## 변경 상세 및 이유
1. 기본값 추가 (bm25_k1, bm25_b, bm25_index_path)
   - 코드 위치: `BM25Engine.__init__`
   - 동작: `Config` 객체에 `bm25_k1`/`bm25_b`/`bm25_index_path` 속성이 없으면 기본값(1.5, 0.75, `data/processed/bm25_index.pkl`)을 동적으로 설정합니다.
   - 이유: 원본 `Config`에 해당 필드가 없을 경우 AttributeError나 KeyError 없이 엔진을 사용하도록 하기 위함.

2. `Config` 임포트 제거 및 타입 애너테이션 제거
   - 코드 위치: 파일 최상단 및 `__init__` 시그니처
   - 이유: `src/common/config.py`는 모듈 로드 시 환경변수 `HF_TOKEN`을 검사하고 값이 없으면 예외를 발생시킵니다. 단위 테스트나 간단한 스모크 테스트를 위해 BM25 모듈을 임포트할 때 이 예외를 회피해야 했습니다. 따라서 상단 임포트를 제거하고 타입 힌트를 삭제했습니다.
   - 메모: 이 변경은 정적 타입 검사나 코드 문서화에 영향을 줄 수 있으므로, 이후 통합 시 타입 힌트를 복원하는 방법을 고민할 수 있습니다(예: TYPE_CHECKING 블록 사용).

3. 테스트 스크립트 추가
   - 경로: `scripts/test_bm25.py`
   - 기능: 샘플 문서 5개로 인덱스를 빌드하고 쿼리를 실행, 빌드/쿼리 소요 시간 표시 및 결과를 출력.
   - 실행 전제: `PYTHONPATH=.` 로 레포 루트를 파이썬 경로에 포함해야 `src` 패키지 임포트가 해소됩니다.

---

## 테스트/실행 방법 (로컬)
1. 필수 패키지 설치 (가상환경 권장):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# 추가로 필요한 패키지
pip install rank-bm25 nltk
```

2. (선택) `nltk` 초기화 (현재 코드는 PorterStemmer만 사용하므로 필수는 아님):

```bash
python -c "import nltk; nltk.download('punkt')"
```

3. 스모크 테스트 실행:

```bash
cd "$(pwd)/Multi-hop-FC"  # 레포 루트로 이동
PYTHONPATH=. python3 scripts/test_bm25.py
```

참고: 이전 시도에서 `HF_TOKEN` 환경변수로 인한 `Config` 예외가 발생했으나, 상기 변경으로 인해 테스트 스크립트는 이제 `Config`를 직접 임포트하지 않으므로 `HF_TOKEN`이 없어도 실행 가능해야 합니다.

---

## 현재 상태 및 결과 요약
- 레포 복제: 완료 (로컬 `feature/data` 브랜치와 동기화됨).
- 스크립트 추가: 완료 (`scripts/test_bm25.py`).
- 직접 실행: 초기 실행 시 `ModuleNotFoundError: No module named 'src'` 발생 — `PYTHONPATH=.` 설정 필요.
- 두 번째 실행 시 `HF_TOKEN` 검사로 인해 `src.common.config`에서 예외 발생 — 이 문제를 완화하기 위해 `bm25_engine.py`에서 `Config` 직접 임포트를 제거함.
- 최종 테스트 실행은 취소/중단되어(터미널 호출이 취소됨) 성공 여부는 아직 완전 확인되지 않았습니다.

---

## 권장되는 다음 단계
- (권장) `bm25_engine.py`에서 `Config` 타입 참조를 안전하게 유지하려면 `typing.TYPE_CHECKING`을 활용하여 런타임에 임포트되지 않게 하세요. 예:

```py
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.common.config import Config
```

- 실제 데이터로 인덱싱을 진행하려면 `src/data/sentence_chunks` 또는 `data/processed/hover_with_gold_chunks/hover_with_gold.json` 등을 사용해 `chunks` 리스트를 만들고 `BM25Retriever.build_from_chunks`를 호출하세요.

- 요구 패키지(`rank-bm25`, `nltk`)를 `requirements.txt`에 추가하면 다른 사용자가 동일한 환경을 재현하기 쉬워집니다.

- 장기적으로는 BM25 인덱싱을 별도 스크립트로 분리하고(예: `scripts/build_bm25_index.py`) 대용량 데이터에 대한 배치 처리/로그ging/중간 체크포인트를 추가하세요.

---

## 변경 이력 (간단 로그)
- 2026-04-07: `bm25_engine.py` — 기본값(fallback) 추가, `Config` 임포트 제거, 타입 애너테이션 제거
- 2026-04-07: `scripts/test_bm25.py` — 스모크 테스트 스크립트 추가
- 2026-04-07: 문서 파일 `docs/BM25_ENGINE_CHANGES.md` 생성

---

필요하시면 이 문서를 더 포맷해서 `CHANGELOG.md`에 병합하거나, Git 커밋 메시지 샘플과 PR 템플릿도 생성해 드리겠습니다.
