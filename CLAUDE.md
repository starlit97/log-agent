# log-agent — Agent Working Rules

이 저장소에서 작업하는 모든 코딩 에이전트는 이 문서를 따른다.
사용자 글로벌 규칙(KISS / YAGNI / 구조 무결성 / 편법 금지 / 검증 필수 등)은 그대로 적용되며,
본 문서는 프로젝트 특수 규칙을 추가한다.

## 절대 규칙

- **v0는 LLM-only.** scikit-learn, xgboost, lightgbm, statsmodels, optuna, shap,
  imbalanced-learn 등 ML 라이브러리를 의존성/코드에 추가하지 않는다.
  v2 진입 조건은 [docs/roadmap.md](docs/roadmap.md) 참조.
- **실 데이터 / 사내 정보 / 자격증명** 을 코드, 주석, 테스트, 커밋 메시지, 이슈 코멘트에 포함하지 않는다.
  상세 규칙은 [docs/security.md](docs/security.md).
- `tests/fixtures/` 와 `data/synthetic/` 외 위치에 데이터 파일을 commit 하지 않는다.
- **외부 LLM API** (OpenAI, Anthropic, Google 등) 호출을 운영 경로에 추가하지 않는다.
  운영 LLM은 로컬(Ollama / vLLM)만 사용.

## 아키텍처 규칙

- 의존 방향은 [docs/v0-architecture.md](docs/v0-architecture.md) 의 단방향을 따른다.
- 모듈 책임 표를 위반하지 않는다. 예: `analyzer`가 메일을 직접 발송하지 않는다 — 결과를 반환, 발송은 호출자.
- LLM 응답은 **반드시 pydantic 모델로 파싱·검증**한다. 비검증 dict 사용 금지.
- 새 모듈을 만들기 전, 기존 모듈 확장으로 해결 가능한지 먼저 검토한다.

## 작업 시 항상

- 시작 전 다음 문서를 읽었는지 확인한다:
  [docs/v0-architecture.md](docs/v0-architecture.md),
  [docs/roadmap.md](docs/roadmap.md),
  [docs/security.md](docs/security.md),
  [docs/conventions.md](docs/conventions.md).
- 코드 작성 후 `ruff check src/`, `pytest` 가 실제 통과한 출력을 본 뒤 완료를 선언한다.
- PR 설명에 변경이 닿는 모듈 범위를 명시한다.

## 막힐 때

- 원칙 충돌 시 코드 대신 TODO 를 남기고 중단, 사용자에게 보고한다.
  형식은 사용자 글로벌 CLAUDE.md 의 TODO FORMAT 을 사용.
- 라이브러리 버전 / API 사용법이 불확실하면 추측 코드를 쓰지 말고 문서 확인을 먼저 한다.
