# BM25 테스트 가이드

이 문서는 로컬에서 BM25 유닛 테스트를 실행하는 방법과 테스트의 목적을 설명합니다.

사전 조건
- 가상환경을 활성화한 상태에서 작업하세요.
- `requirements.txt`에 명시된 패키지를 설치하세요:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

테스트 실행
- 프로젝트 루트에서 다음 명령으로 pytest를 실행하세요:

```bash
PYTHONPATH=. pytest -q
```

테스트 설명
- `tests/test_bm25_engine.py`는 작은 고정 코퍼스를 이용해 `BM25Engine`이 인덱스를 빌드하고, 쿼리에 대해 기대되는 최상위 결과를 반환하는지 확인합니다.

문제 해결
- `ModuleNotFoundError: No module named 'src'` 발생 시: `PYTHONPATH=.` 로 실행했는지 확인하세요.
- `HF_TOKEN` 관련 예외는 `bm25_engine.py`가 런타임에 `Config`를 직접 임포트하지 않도록 조치되어 있으므로 테스트 실행에는 영향이 없어야 합니다.

추가
- 더 많은 케이스(여러 쿼리, edge-case 텍스트 등)를 추가해 테스트 범위를 넓히는 것을 권장합니다.
