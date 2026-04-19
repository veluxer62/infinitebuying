# 무한매수법 V4.0 가이드 도구

무한매수법 V4.0 방법론에 따라 **내일의 매수·매도 가이드라인**을 계산해주는 CLI 도구입니다.  
자동 주문을 실행하지 않으며, 사용자가 직접 증권사 앱에서 주문을 넣는 것을 전제로 합니다.

---

## 주요 기능

- 오늘 체결한 매수·매도 내역을 입력하면 포트폴리오 상태를 자동으로 갱신합니다.
- 내일 넣어야 할 LOC 주문의 지정가·수량·금액을 출력합니다.
- 날짜별 운용 로그를 마크다운 파일로 저장합니다 (`data/logs/YYYY-MM-DD.md`).
- 회전 종료(최종매도) 시 수익 요약 보고서를 생성합니다 (`reports/`).

---

## 기술 스택

- Python 3.10+
- PyYAML (설정 파일 파싱)
- pytest (테스트)

---

## 설치 방법

```bash
# 저장소 클론
git clone <repository-url>
cd infinitebuying

# 의존성 설치
pip install -r requirements.txt
```

---

## 실행 방법

### 일반 실행 (매일 1회)

```bash
python main.py
```

실행 순서:

1. 오늘 종가 입력
2. 포트폴리오 현황 출력
3. 오늘 체결 내역 입력 (`b` 매수 / `q` 쿼터매도 / `f` 최종매도 / `n` 없음)
4. 상태 자동 갱신 (평단가, T값, 잔금)
5. **내일 매매 가이드라인 출력** (LOC 지정가, 수량, 금액)
6. 일별 로그 저장

**최초 실행 시** `data/state.json`이 없으면 초기 설정을 진행합니다.  
종목·분할수는 `config.yaml`에서 읽고, 원금을 입력받아 초기 상태를 생성합니다.

```
초기 설정을 시작합니다.
  종목: TQQQ  |  분할수: 40
  투자 원금 (USD) [20,000]: $        ← Enter 입력 시 config 기본값 사용
```

### 현황 조회 (주문 없음)

```bash
python main.py --status
```

현재 포트폴리오 상태만 출력하고 상태 파일을 변경하지 않습니다.

### 상태 초기화

```bash
python main.py --reset
```

`data/state.json`을 삭제하고 처음부터 시작합니다. **복구 불가**합니다.

### 설정 파일 지정

```bash
python main.py --config path/to/config.yaml
```

---

## 설정 파일 (`config.yaml`)

```yaml
# 운용 종목 및 분할 수
symbol: TQQQ
division: 40

# 초기 투자 원금 (USD) — 첫 실행 시 Enter로 이 값 사용
original_capital: 20000.0

# 파일 경로
state_file: data/state.json
log_dir: data/logs
report_dir: reports
```

---

## 무한매수법 V4.0 핵심 개념

| 용어 | 설명 |
|------|------|
| T값 | 매수 진행 단계. 1회매수 → +1, 절반매수 → +0.5, 쿼터매도 → ×0.75 |
| 별% | `(15 - 0.75 × T) %` |
| 별지점 | `평균단가 × (1 + 별%)` — LOC 매도·매수 기준가 |
| 매수점 | `별지점 - $0.01` — LOC 매수 지정가 |
| 1회 매수금 | `잔금 / (40 - T)` |
| 전반전 (T < 20) | 1회 매수금의 절반은 별지점 LOC, 절반은 평단가 LOC |
| 후반전 (20 ≤ T < 39) | 1회 매수금 전체를 별지점 LOC |
| 소진모드 (T ≥ 39) | 별도 방법론 수행 필요 |
| 쿼터매도 | 보유수량 × 1/4, 별지점 LOC |
| 최종매도 | 전량, `평단가 × 1.15` 지정가 |

---

## 프로젝트 구조

```
infinitebuying/
├── main.py                      # 진입점 (CLI 인자 파싱)
├── config.yaml                  # 종목·분할수·원금·경로 설정
├── requirements.txt
│
├── src/
│   ├── runner.py                # 메인 오케스트레이터 (실행 흐름 제어)
│   │
│   ├── strategy/
│   │   ├── calculator.py        # 핵심 계산 (별%, 별지점, T값, 매수금 등)
│   │   └── guide_builder.py     # 내일 가이드라인 생성 (TradeGuide)
│   │
│   ├── state/
│   │   └── manager.py           # 포트폴리오 상태 저장·로드 (state.json)
│   │
│   └── report/
│       ├── daily_logger.py      # 날짜별 마크다운 로그 생성
│       └── final_report.py      # 회전 종료 시 최종 보고서 생성
│
├── tests/
│   ├── test_calculator.py
│   ├── test_guide_builder.py
│   └── test_state_manager.py
│
├── data/
│   ├── state.json               # 포트폴리오 상태 (자동 생성, git 제외)
│   └── logs/                    # 날짜별 운용 로그 (자동 생성, git 제외)
│
├── reports/                     # 회전 종료 보고서 (자동 생성, git 제외)
└── research/
    └── 무한매수법_V4.0_방법론.md
```

---

## 테스트 실행

```bash
python -m pytest tests/ -v
```

---

## 일별 로그 예시

`data/logs/2026-04-19.md` 형식으로 저장됩니다.

- 포트폴리오 현황: 종가, 평균단가, 수익률, T값, 별지점 등
- 금일 체결 내역
- 내일 매매 가이드라인 (LOC 지정가, 수량, 금액)
