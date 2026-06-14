# 구현 요약 — 거시경제 대시보드

작성일: 2026-06-14

---

## 구현 과정 요약

### 1단계: 환경 설정

- Python 3.11.9 확인
- 프로젝트 디렉토리 구조 생성 (`collectors/`, `db/`, `dashboard/`, `utils/`, `.github/workflows/`)
- `requirements.txt` 작성 및 패키지 설치 (fredapi, yfinance, streamlit, plotly 등)
- `.env` 파일 생성 (FRED_API_KEY, ECOS_API_KEY)
- `.gitignore` 생성 (`.env`, `plan.md` 제외)
- GitHub 리포지토리 연결 및 초기 push

### 2단계: 설계 결정 사항

| 항목 | 결정 내용 |
|---|---|
| ISM PMI 대체 | `ISM/MAN_PMI`(Quandl 포맷, FRED 미지원) → `UMCSENT`(미시건대 소비자심리) |
| ECOS 수출 코드 수정 | `901Y015`(채권 통계) → `403Y001` 수출금액지수, item_code `*AA` (총지수) |
| 지표 수 | 23개 (삼성전자/SK하이닉스 별도 계상) |
| DB 영속성 | GitHub Actions에서 수집 후 `macro.db`를 git에 커밋하는 방식 |
| Gmail 알림 | GMAIL_USER / GMAIL_APP_PASSWORD 환경변수 기반 (미설정 시 콘솔 출력) |

### 3단계: 수집 모듈 구현

| 모듈 | 담당 지표 | 결과 |
|---|---|---|
| `collectors/fred.py` | FRED 7종 + 장단기 금리차 자체 계산 | 8개 ticker 수집 성공 |
| `collectors/market.py` | yfinance 12종 | 12개 ticker 수집 성공 |
| `collectors/ecos.py` | ECOS 3종 (기준금리, CPI, 수출금액지수) | 3개 ticker 수집 성공 |
| `scheduler.py` | 세 모듈 순차 실행 | 총 23개 ticker, 약 3,000건 초기 수집 |

#### 수집 중 발생한 이슈 및 해결

1. **yfinance MultiIndex 이슈**: 신버전(1.4.x)에서 단일 ticker 다운로드 시 `Close` 컬럼이 DataFrame으로 반환됨 → `.squeeze()` 처리로 해결
2. **yfinance Rate Limit**: 연속 요청 시 `YFRateLimitError` 발생 → ticker 간 `time.sleep(1)` 추가
3. **Windows cp949 인코딩**: `notifier.py`의 em dash(`—`) 문자가 출력 오류 → ASCII 문자로 대체
4. **ECOS 901Y015 코드 오류**: plan.md의 코드가 채권 통계 코드였음 → API로 확인 후 `403Y001` + `*AA`로 수정

### 4단계: 데이터베이스

- SQLite (`db/macro.db`) 단일 테이블 `indicators`
- `(ticker, date)` UNIQUE 제약으로 중복 방지, UPSERT 처리
- 최종 저장 현황: 23개 ticker, 3,045건

### 5단계: Streamlit 대시보드 구현

4개 탭 구성:

| 탭 | 구성 요소 |
|---|---|
| 글로벌 금융 | KPI 5개 + 국채 금리 추이 차트 + DXY 차트 |
| 인플레이션/경기 | KPI 4개 + CPI/PCE 비교 차트 + 실업률/소비자심리 차트 |
| 한국/원자재 | KPI 6개 + 환율/원자재/한국 경제 차트 |
| 반도체/주식 | KPI 8개 + 정규화 수익률 비교 차트 + 등락률 히트맵 |

- 금리/달러/환율 등 역방향 지표는 delta_color `inverse` 처리
- 각 KPI 카드에 hover로 기준일 표시
- 반도체/주식 탭: 첫날 기준 정규화(%p 수익률) 비교 차트

### 6단계: GitHub Actions 자동화

- `.github/workflows/collect.yml`: 매일 UTC 01:00 (KST 10:00) 수집 스케줄
- 수집 후 `macro.db`를 자동 커밋·푸시 (DB 영속성 확보)
- 4개 GitHub Secret 등록 필요: `GH_TOKEN`, `FRED_API_KEY`, `ECOS_API_KEY`, `GMAIL_USER`, `GMAIL_APP_PASSWORD`

---

## 사용자 수동 설정 필요 항목

### GitHub Secrets 등록

GitHub 리포지토리 → Settings → Secrets and variables → Actions에서 아래 5개를 등록해야 합니다:

| Secret 이름 | 값 |
|---|---|
| `GH_TOKEN` | Personal Access Token (repo + workflow 권한) |
| `FRED_API_KEY` | FRED API 키 |
| `ECOS_API_KEY` | 한국은행 ECOS API 키 |
| `GMAIL_USER` | Gmail 주소 (알림용) |
| `GMAIL_APP_PASSWORD` | Gmail 앱 비밀번호 |

### Gmail 앱 비밀번호 발급

1. Google 계정 → 보안 → 2단계 인증 활성화
2. 보안 → 앱 비밀번호 → 메일 선택 → 16자리 비밀번호 생성

---

## 최종 디렉토리 구조

```
macro-dashboard/
├── collectors/
│   ├── __init__.py
│   ├── fred.py
│   ├── market.py
│   └── ecos.py
├── db/
│   ├── schema.sql
│   └── macro.db
├── dashboard/
│   └── app.py
├── utils/
│   ├── __init__.py
│   ├── db.py
│   ├── validator.py
│   └── notifier.py
├── .github/workflows/
│   └── collect.yml
├── .env              (gitignore)
├── .gitignore
├── config.py
├── scheduler.py
├── requirements.txt
├── architecture.svg
└── implementation_summary.md
```
