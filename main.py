"""
무한매수법 V4.0 가이드 도구 — 진입점

사용법:
    python main.py              # 일반 실행 (오늘 종가/체결 입력 → 내일 가이드 출력)
    python main.py --status     # 현재 포트폴리오 상태만 출력
    python main.py --reset      # 상태 초기화 (신중히 사용)
    python main.py --config PATH  # 설정 파일 경로 지정 (기본: config.yaml)
"""
from __future__ import annotations

import argparse

import yaml

from src.runner import InfiniteBuyingRunner
from src.state.manager import StateManager


def load_config(path: str = "config.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="무한매수법 V4.0 가이드 도구",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="현재 포트폴리오 상태만 출력 (매매 입력 없음)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="상태 파일 초기화 (주의: 복구 불가)",
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="설정 파일 경로 (기본: config.yaml)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    state_mgr = StateManager(
        state_file=config.get("state_file", "data/state.json"),
    )

    if args.reset:
        ans = input("상태를 초기화하면 복구할 수 없습니다. 계속하시겠습니까? (yes 입력): ").strip()
        if ans == "yes":
            state_mgr.reset()
            print("  초기화 완료.")
        else:
            print("  취소됨.")
        return

    runner = InfiniteBuyingRunner(state_mgr=state_mgr)

    if args.status:
        runner.run_status_only()
        return

    runner.run()


if __name__ == "__main__":
    main()
