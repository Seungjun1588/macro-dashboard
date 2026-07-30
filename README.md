# macro-dashboard

거시경제 지표를 매일 자동 수집해 SQLite에 쌓고, Streamlit 대시보드로 보는 개인용 프로젝트입니다.
FRED(미국) · ECOS(한국은행) · Yahoo Finance 3개 소스에서 23개 지표를 수집합니다.

- **경기 사이클 판단** — 장단기 금리차 · 실업률 추세 · CPI YoY · 소비자심리를 조합해 팽창/과열/수축/침체 4단계로 표시
- **신호등 시스템** — 지표별 임계값 기준으로 🟢🟡🔴 표시
- **알림** — 금리 역전, 환율 급변, SOX 급등 등 조건 충족 시 배너 노출
- **실적 트래커** — 삼성전자 · SK하이닉스 · 엔비디아 분기 매출/영업이익/재고

---

## 실행 방법

### 1. 의존성 설치

```powershell
pip install -r requirements.txt
```

### 2. 환경변수 설정

프로젝트 루트에 `.env` 파일을 만듭니다 (`.gitignore`에 등록되어 있어 커밋되지 않습니다).

```
FRED_API_KEY=your_fred_api_key
ECOS_API_KEY=your_ecos_api_key
GMAIL_USER=your@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
```

| 변수 | 용도 | 발급처 | 필수 여부 |
|---|---|---|---|
| `FRED_API_KEY` | 미국 지표 수집 | https://fred.stlouisfed.org/docs/api/api_key.html | 수집 시 필요 |
| `ECOS_API_KEY` | 한국 지표 수집 | https://ecos.bok.or.kr/api/ | 수집 시 필요 |
| `GMAIL_USER` / `GMAIL_APP_PASSWORD` | 수집 실패 시 이메일 알림 | Gmail 앱 비밀번호 | 선택 (없으면 콘솔 출력) |

> Yahoo Finance(주가·환율·원자재)는 API 키가 필요 없습니다.
> 대시보드만 볼 거라면 `.env` 없이도 동작합니다 — DB(`db/macro.db`)가 저장소에 함께 커밋되어 있습니다.

### 3. 대시보드 실행

```powershell
python -m streamlit run dashboard/app.py
```

브라우저에서 `http://localhost:8501`이 열립니다. 종료는 터미널에서 `Ctrl+C`.

포트를 바꾸려면:

```powershell
python -m streamlit run dashboard/app.py --server.port 8502
```

<details>
<summary><code>streamlit: 용어가 인식되지 않습니다</code> 오류가 날 때</summary>

`streamlit.exe`가 설치된 Scripts 폴더가 PATH에 없어서 생기는 문제입니다.
위처럼 `python -m streamlit`으로 실행하면 PATH를 거치지 않으므로 해결됩니다.
`python streamlit run ...`(`-m` 없이)은 `streamlit`이라는 *파일*을 찾으므로 다른 오류가 납니다.
</details>

### 4. 데이터 수집 (수동)

```powershell
python scheduler.py
```

FRED → Yahoo Finance → ECOS 순으로 수집하고 `db/macro.db`에 upsert합니다.
소스별로 실패해도 나머지는 계속 진행하며, 실패 시 이메일 알림을 보냅니다.

개별 소스만 수집하려면:

```powershell
python collectors/fred.py
python collectors/market.py
python collectors/ecos.py
```

### 5. 데이터 상태 점검

```powershell
python scripts/macro_health_check.py    # 수집 누락·지연 감지
python scripts/latest_snapshot.py       # 최신값 + 변화율 스냅샷 (NOTABLE 표시)
```

헬스체크 기준: 월간 지표 45일, 일간 지표 7일 초과 시 `STALE`로 판정합니다.

---

## 자동 수집 (GitHub Actions)

`.github/workflows/collect.yml`이 **매일 UTC 01:00 (KST 10:00)** 에 실행됩니다.
수집 → 헬스체크 → (선택) Claude로 리포트 요약 → `db/macro.db` 커밋·푸시 순서입니다.
`workflow_dispatch`로 수동 실행도 가능합니다.

필요한 리포지토리 Secrets:

| Secret | 용도 |
|---|---|
| `GH_TOKEN` | DB 변경분 커밋·푸시 |
| `FRED_API_KEY`, `ECOS_API_KEY` | 데이터 수집 |
| `GMAIL_USER`, `GMAIL_APP_PASSWORD` | 실패 알림 |
| `ANTHROPIC_API_KEY` | 헬스체크 리포트 자연어 요약 (없으면 해당 스텝 건너뜀) |

---

## 수집 지표

| 카테고리 | 지표 |
|---|---|
| 글로벌 금융 | 미국 기준금리, 10년물/2년물 국채, 장단기 금리차(자체 계산), 달러 인덱스 |
| 인플레이션/경기 | 미국 CPI, PCE, 실업률, 미시건대 소비자심리 |
| 한국/원자재 | 원/달러 환율, 한국 기준금리, 한국 CPI, 수출금액지수, WTI 유가, 금 |
| 반도체/주식 | SOX, 엔비디아, 삼성전자, SK하이닉스, S&P500, 나스닥, 코스피, 코스닥 |

지표 추가·수정은 `config.py`의 `FRED_INDICATORS` / `YFINANCE_INDICATORS` / `ECOS_INDICATORS`에서 합니다.

---

## 프로젝트 구조

```
macro-dashboard/
├── config.py                 # 지표 정의, 색상, 경로, 환경변수 로드
├── scheduler.py              # 전체 수집 엔트리포인트
├── backfill_ks.py            # 삼성전자/하이닉스 누락분 백필 (rate limit 대응)
├── collectors/
│   ├── fred.py               # 미국 지표 + 장단기 금리차 계산
│   ├── market.py             # yfinance (주가·환율·원자재)
│   └── ecos.py               # 한국은행 ECOS
├── dashboard/
│   └── app.py                # Streamlit 앱 (6개 페이지)
├── db/
│   ├── schema.sql            # indicators 테이블 (ticker+date UNIQUE)
│   └── macro.db              # SQLite (저장소에 커밋됨)
├── scripts/
│   ├── macro_health_check.py # 수집 누락·지연 점검
│   └── latest_snapshot.py    # 최신 스냅샷 + NOTABLE 판정
├── utils/
│   ├── db.py                 # 연결·초기화·upsert
│   ├── validator.py          # 티커별 값 범위 검증 (이상치 차단)
│   └── notifier.py           # Gmail 실패 알림
├── reports/                  # 일일 브리핑 마크다운
├── .streamlit/config.toml    # 다크 테마
└── .claude/                  # Claude Code 에이전트·스킬 정의
```

### 데이터 모델

`indicators` 테이블 하나에 모든 지표를 저장합니다. `(ticker, date)`가 UNIQUE이며 수집 시 upsert하므로,
같은 기간을 여러 번 수집해도 중복이 쌓이지 않고 최신값으로 덮어씁니다.

---

## Claude Code 연동

`.claude/` 아래에 서브에이전트와 스킬이 정의되어 있습니다. Claude Code 세션에서 사용합니다.

**스킬**

- `macro-health-check` — "오늘 수집 이상 없어?" 류의 질문에 답할 때
- `macro-briefing` — 헬스체크 → 리서치 → 작성 → 검수 → `reports/YYYY-MM-DD.md` 저장 파이프라인

**서브에이전트**

| 에이전트 | 역할 |
|---|---|
| `data-validator` | 수집 상태를 대화형으로 점검·보고 (수정하지 않음) |
| `health-report-narrator` | CI에서 생성된 헬스체크 리포트를 사람이 읽기 좋게 요약 |
| `macro-researcher` | NOTABLE 지표의 변동 배경을 웹 검색으로 조사 |
| `macro-writer` | 스냅샷 + 리서치를 받아 브리핑 초안 작성 |
| `macro-critic` | 초안을 원본 데이터와 대조해 검수 |

브리핑 파이프라인은 사람이 직접 요청할 때만 실행되며, 자동 실행되지 않습니다.
