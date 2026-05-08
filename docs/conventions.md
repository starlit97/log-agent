# Conventions

## 모듈 / 임포트

- 한 모듈 = 한 책임. 이름이 책임을 말하도록.
- 모듈 간 의존은 [v0-architecture.md](v0-architecture.md) 의 의존 방향만 따른다.
- `ui/`, `tests/` → `src/log_agent/` import 는 OK. 반대 방향 금지.

## 네이밍

- 함수 / 변수: `snake_case`.
- 클래스: `PascalCase`.
- 의미 없는 약어 금지: `cfg`, `mgr`, `util`, `proc` → `config`, `manager`, `utility`, `processor` 로 풀어 적는다.
- bool 변수는 `is_`, `has_`, `should_` prefix.

## 타입 / 검증

- 공개 함수에 타입 힌트 필수.
- 외부 입력(파일, LLM 응답, 환경변수)은 pydantic 또는 명시적 검증을 거친 뒤 사용.
- `Any` 사용 시 주석으로 이유 명시.

## 테스트

- pytest. 합성 데이터만 사용 (`tests/fixtures/`, 결정론적 시드).
- 외부 의존(Ollama, SMTP, 파일시스템 watch)은 mock. 실제 호출 금지.
- 한 테스트 = 한 사실. 어설션이 여러 측면을 동시에 검증하지 않도록 분리.
- 테스트 함수명은 `test_<무엇이>_<어떤조건에서>_<어떻게된다>` 형태.

## 로깅

- `print()` 금지. 표준 `logging` 모듈 사용.
- 로그에 사번 / 인명 / 사내 IP / 도메인 출력 금지. 필요 시 hash 또는 마스킹.

## 설정

- 모든 환경 의존 값은 `.env` 에서 로드. 코드 하드코딩 금지.
- `.env.example` 은 commit, `.env` 는 절대 commit 금지.

## 주석

- 사용자 글로벌 규칙에 따라 기본은 무주석. "왜"만 적는다.
- 임시 / 우회 코드에는 반드시 TODO + 사유 + 후속 조치.

## 커밋

- 제목 50자 이내, 명령형 ("Add ...", "Fix ...", "Refactor ...").
- 본문에는 "왜". "무엇"은 diff 가 보여준다.
- 한 커밋 = 한 논리 변경.
