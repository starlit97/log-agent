# v2 후보: ML 파이프라인 (탐색 결과)

> **상태**: 탐색만 완료, **구현 안 됨**.
> v2 진입 조건(라벨 200건+, LLM baseline 측정 완료, ML 우위 검증) 충족 시 정식 설계로 승격 검토.
>
> 이 문서는 *지금 만드는 시스템*이 아니다.
> v0는 LLM-only이며, 현 시스템 구조는 [../v0-architecture.md](../v0-architecture.md) 참고.
> 단계 게이트 조건은 [../roadmap.md](../roadmap.md) 참고.

---

## Context

Excel 형태의 보안 로그(출입/모바일웨이/권한대장/정보기기 등)를 입력받아 ML 이진분류(0/1)로 이상 여부를 판정하는 후보 설계.

- ML 모델이 분류 수행 (RandomForest / XGBoost / LightGBM / SVM)
- LLM은 보조 역할 (데이터 이해, EDA 전략, 결과 해석)
- 라벨이 있는 지도학습 시나리오 가정 (없으면 IsolationForest 등 비지도로 fallback)

---

## 파이프라인 코어 (8 Stage)

```
[Excel] → Ingest → LLM Understand → EDA/Preprocess → Feature Selection
   → Split → Train → Evaluate → Predict & Explain → [Report]
```

### Stage 1. Ingest

- pandas.read_excel / openpyxl
- 컬럼 정규화, dtype 추론, 결측 식별
- 출력: 원본 DataFrame + 메타정보(컬럼명, dtype, 결측률)

### Stage 2. LLM Data Understanding (1회 호출)

- 입력: 컬럼명·샘플 5행·메타정보
- 출력 (JSON 강제):
```json
{
  "target_candidate": "is_anomaly",
  "feature_roles": {
    "user_id": "id",
    "access_time": "datetime",
    "gate": "categorical",
    "duration": "continuous"
  },
  "domain_hints": ["야간출입은 위험피처", "사번은 식별자만"],
  "preprocessing_plan": ["..."]
}
```
- 모델: Qwen2.5-7B 또는 32B (구조화 출력)

### Stage 3. EDA & Preprocessing

| 작업 | 기법 | 라이브러리 |
|---|---|---|
| 이상치 탐지 | IQR, Z-score | scipy, numpy |
| 결측치 처리 | mean/median/KNN imputer | sklearn.impute |
| 다중공선성 | VIF, 상관행렬 | statsmodels |
| 연속형 그룹화 | KBinsDiscretizer, qcut | sklearn, pandas |
| 변수 그룹화 | PCA, FactorAnalyzer | sklearn |
| 인코딩 | One-Hot, Target Encoding | sklearn, category_encoders |
| 정규화 | StandardScaler, MinMaxScaler | sklearn |

VIF > 10 변수 제거, 상관계수 |r| > 0.9 쌍에서 하나 제거.

### Stage 4. Feature Selection

3-Tier 결합:
1. **Filter** — Pearson, Chi-square, Mutual Information
2. **Wrapper** — RFE (재귀적 제거)
3. **Embedded** — L1(Lasso), Tree feature_importance

LLM 도메인 힌트(Stage 2) 가중치 반영하여 최종 피처 결정.

### Stage 5. Split & Imbalance Handling

- `train_test_split(stratify=y, test_size=0.2)`
- 불균형 보정: SMOTE / RandomUnderSampler / `class_weight='balanced'`
- StratifiedKFold (k=5) 교차검증

### Stage 6. Model Training

| 모델 | 용도 | 튜닝 |
|---|---|---|
| RandomForest | baseline, 해석성 | n_estimators, max_depth |
| XGBoost | 성능 | learning_rate, max_depth, gamma |
| LightGBM | 대용량 빠른 학습 | num_leaves, min_child_samples |
| SVM(RBF) | 소규모 정밀 | C, gamma |

- HPO: Optuna (TPE sampler, 30~100 trials)
- 앙상블: VotingClassifier or Stacking
- Best model + 전처리 = `sklearn.Pipeline`으로 직렬화 (joblib)

### Stage 7. Evaluation & Threshold Tuning

- 지표: Precision, Recall, F1, ROC-AUC, PR-AUC
- Confusion Matrix 시각화
- Threshold 튜닝: 이상탐지 = Recall 우선
  - 비용 함수 정의: `cost = α·FN + β·FP`
  - PR curve에서 cost 최소 threshold 선택

### Stage 8. Predict & Explain

- 신규 데이터 → `pipeline.predict_proba` → 이상점수
- SHAP 값으로 row별 기여 피처 추출
- LLM Reasoner: SHAP top-3 피처 + 사용자 컨텍스트 → 자연어 사유

> 예: "출입시각(03:12)·근무시간이탈·권한등급 불일치가
> 주요 이상 신호. 평소 패턴(09-18시) 대비 이탈."

- 출력: 이상 건 Excel + 요약 보고서(Markdown) + 메일

---

## LLM 개입 지점 (3곳만)

| Stage | 역할 | 호출 빈도 |
|---|---|---|
| 2. Understand | 스키마/도메인 이해, EDA 전략 | 데이터셋당 1회 |
| 4. Selection 보조 | 도메인 의미 기반 변수 우선순위 | 데이터셋당 1회 |
| 8. Explain | 이상 건 자연어 해석 | 이상 건당 1회 (보통 N<100) |

→ LLM 비용·지연 통제 가능, 모델 학습 본체는 결정론적 ML.

---

## 모듈 구조 (제안)

```
anomaly_agent/
├── ingest.py         # Excel/CSV 로딩, 스키마 정규화
├── llm/
│   ├── understand.py # Stage 2: 데이터 이해
│   └── explain.py    # Stage 8: SHAP→자연어
├── preprocess/
│   ├── outlier.py    # IQR, Z-score
│   ├── missing.py    # imputer
│   ├── encoding.py   # one-hot, target enc
│   ├── scaling.py    # standard, minmax
│   └── multicol.py   # VIF, corr filter
├── feature/
│   ├── filter.py     # chi2, MI
│   ├── wrapper.py    # RFE
│   └── embedded.py   # Lasso, tree importance
├── model/
│   ├── trainer.py    # CV + Optuna
│   ├── ensemble.py   # voting/stacking
│   └── persist.py    # joblib 저장/로드
├── eval/
│   ├── metrics.py    # PR/ROC/F1
│   └── threshold.py  # cost 기반 튜닝
├── predict/
│   ├── inference.py  # predict_proba
│   └── shap_expl.py  # SHAP
└── report/
    ├── excel.py      # 이상건 시트
    └── markdown.py   # 요약 리포트
```

---

## (구버전) 단계별 우선순위

원래 작성 시점의 단계 계획. 현재 v0=LLM-only로 결정되어 아래는 v2 내부 단계로 격하됨.

```
v0.1 (1주)  Stage 1,3,5,6,7  → RandomForest 단일, 합성데이터 검증
v0.2 (2주) + Stage 4 (피처선택) + XGBoost + Optuna
v0.3 (2주) + Stage 2,8 (LLM 개입) + SHAP 해석
v1.0 (3주) + 앙상블 + 자동 재학습 트리거 + 보고서 자동발송
```

---

## 핵심 라이브러리

```
pandas numpy
scikit-learn xgboost lightgbm
statsmodels         # VIF
imbalanced-learn    # SMOTE
optuna              # HPO
shap
joblib
litellm             # LLM 추상화 (Stage 2, 8)
openpyxl
```

---

## 검증 방법 (가상)

1. 합성 데이터 (`sklearn.make_classification`, imbalance ratio 1:99)로 Stage 1~7 단위 테스트
2. 실제 샘플 (1개월 출입로그 익명화본)로 end-to-end PoC
3. 지표 목표: PR-AUC > 0.8, Recall@10%FPR > 0.7
4. LLM 해석 품질: 보안담당자 눈으로 N=20 샘플 정성 평가

---

## 결정 보류 항목 (실행 전 확정 필요)

- 라벨 데이터 확보 가능 여부 (없으면 비지도 IsolationForest fallback)
- 엑셀 컬럼 표준화 여부 (가변 시 Stage 2 필수, 고정 시 매핑 정적)
- LLM 호스팅 (사내 vLLM vs 외부 API — **외부 API는 정책상 불가**)
- HITL 정책 (자동 메일발송 vs 검토대기)

---

## v2 진입 시 재검토할 가정들

- **데이터 양**: 현 시점 데모 수준. ML은 최소 수천 행 + 양·음 라벨 균형 필요
- **LLM-only baseline**: v0 운영해보고 정확도가 충분한지 측정. 충분하면 ML 도입 불요
- **LLM 직접 분류 vs ML 분류**: ML 도입 전, "LLM이 분류 직접 수행 + LLM이 사유 생성" 단일 모델 구성과 정확도 비교
- **운영 비용**: ML 학습/재학습 운영 부담이 LLM 추론 비용보다 낮은지
