# v0 Architecture

LLM-only 직판정 파이프라인.

## 데이터 흐름

자동 모드 (운영) 와 데모 모드 (UI) 가 동일한 분석 모듈을 공유한다.

```
                  [자동 모드]                  [데모 모드]
[감시 폴더] --(엑셀 추가)--> [watcher]      [ui/app.py (Streamlit)]
                                ↓                ↓
                          [loader (pandas)]  ←──┘ (공유)
                                ↓
                          [analyzer]
                            ├─ 시스템 프롬프트 (룰 정의)
                            └─ 사용자 프롬프트 (행 데이터 + 컨텍스트)
                                ↓
                          [llm client (Ollama)]
                                ↓
                          [JSON 응답 파싱 (pydantic)]
                                ↓
                            (이상 있음?) ── no ──> 종료
                                ↓ yes
                          [mailer (smtplib)]
                          (자동 발송 OR UI 승인 후 발송)
```

## 모듈 책임

| 모듈 | 책임 | 비책임 |
|---|---|---|
| `watcher.py` | 폴더 변경 감지, 새 파일 큐잉 | 파싱·분석 |
| `loader.py` | 엑셀 → DataFrame, 컬럼 정규화 | 이상 판정 |
| `llm.py` | LLM 호출 추상화 (HTTP 클라이언트) | 프롬프트 작성 |
| `analyzer.py` | 프롬프트 조립, 응답 파싱, 결과 구조화 | 메일 발송 |
| `mailer.py` | SMTP 연결, 메일 템플릿 렌더 | 결과 판정 |
| `main.py` | 모듈 결합, 설정 로드, 엔트리포인트 | 비즈니스 로직 |
| `ui/app.py` | Streamlit 데모 UI (업로드 → 분석 → 메일 미리보기 → 발송) | LLM 호출/메일 발송 직접 구현 (analyzer/mailer 재사용) |

의존 방향: `main` → `{watcher, analyzer, mailer}`, `ui/app` → `{loader, analyzer, mailer}`, `analyzer` → `{loader, llm}`. 역방향 호출 금지 (단방향).

## 기술 스택

- Python 3.11
- pandas + openpyxl (엑셀)
- watchdog (폴더 감시)
- httpx (LLM HTTP 호출)
- pydantic (LLM 응답 검증)
- smtplib (메일, 표준 라이브러리)
- python-dotenv (설정)
- streamlit (데모 UI)

LLM 서빙: Ollama 또는 vLLM. 모델은 Qwen2.5-7B-Instruct부터 시작. 정확도 부족 시 14B → 32B 단계적.

## 설정 (`.env`)

```
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:7b-instruct
WATCH_DIR=./data/incoming
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
ALERT_TO=
```

실제 값은 절대 commit 금지. `.env.example`만 commit.

## 범위 외 (v0에 포함 안 함)

- ML 분류기, 학습, SHAP, 앙상블, HPO
- DB, 큐, 워커 분리
- 웹 UI, 대시보드
- 다중 사용자, 권한 관리
- 라벨 수집 인터페이스
- 모델 자동 재학습

위 항목은 v1/v2 진입 조건 충족 시 별도 검토.

## 검증 방법

자동 모드:
- 합성 엑셀(이상 행 의도적 포함)을 `WATCH_DIR`에 떨어뜨림
- watcher가 감지 → analyzer가 이상 행 식별 → mailer가 메일 발송
- 메일 본문에 이상 행 + LLM 사유가 포함됨

데모 모드:
- `streamlit run ui/app.py` 로 UI 실행
- UI에서 합성 엑셀 업로드 → "분석 시작" → 결과 표시 → "발송" 버튼 → 메일 송신
- 한 페이지 내에서 업로드/미리보기/분석/메일 흐름이 순차로 보임

- 양 모드 모두 실 데이터 일체 사용하지 않고 검증 완료
