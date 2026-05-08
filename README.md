# log-agent

보안 로그 폴더를 감시하고, 새 엑셀 파일이 들어오면 로컬 LLM으로 이상 여부를 판정해 메일을 발송하는 에이전트.

## 상태

PoC 단계 — v0 (LLM-only) 진행 중. 단계별 계획은 [docs/roadmap.md](docs/roadmap.md) 참고.

## 데이터 취급 — 먼저 읽으세요

이 저장소는 사내 보안 로그를 다룹니다. **실 데이터를 commit해서는 안 됩니다.** 규칙은 [docs/security.md](docs/security.md) 참고.

## 문서

- [docs/roadmap.md](docs/roadmap.md) — 단계별 계획 (v0 → v1 → v2)
- [docs/v0-architecture.md](docs/v0-architecture.md) — 지금 만드는 시스템 구조
- [docs/security.md](docs/security.md) — 데이터/자격증명 취급 규칙
- [docs/explorations/ml-pipeline.md](docs/explorations/ml-pipeline.md) — v2 후보 ML 파이프라인 (탐색만 됨, 구현 X)

## 셋업

v0 스캐폴드 작업 진행 예정. 추후 갱신.
