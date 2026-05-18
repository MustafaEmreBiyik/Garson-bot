from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from .grounded_response_formatter import (
    explain_paraphrase_rejection,
    format_grounded_response,
)
from .grounded_result_builder import build_grounded_result


BASE_DIR = Path(__file__).resolve().parents[1]
MENU_PATH = BASE_DIR / "data" / "menu.yaml"
RESTAURANT_INFO_PATH = BASE_DIR / "data" / "restaurant_info.yaml"


def run_grounded_demo(
    user_message: str,
    paraphrase_candidate: str | None = None,
) -> Dict[str, Any]:
    result = build_grounded_result(
        user_message=user_message,
        menu_path=MENU_PATH,
        restaurant_info_path=RESTAURANT_INFO_PATH,
    )
    rejection_reasons = explain_paraphrase_rejection(result, paraphrase_candidate)
    final_response = format_grounded_response(result, paraphrase_candidate)

    return {
        "user_message": user_message,
        "detected_intent": result.action.intent,
        "canonical_response": result.canonical_response,
        "paraphrase_candidate": paraphrase_candidate,
        "final_response": final_response,
        "used_paraphrase": paraphrase_candidate is not None and not rejection_reasons,
        "rejection_reasons": rejection_reasons,
        "must_preserve_terms": list(result.must_preserve_terms),
        "must_not_introduce": list(result.must_not_introduce),
        "metadata": dict(result.metadata),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the non-invasive grounded-response demo utility."
    )
    parser.add_argument(
        "--message",
        required=True,
        help="User message to send through the grounded demo path.",
    )
    parser.add_argument(
        "--paraphrase",
        default=None,
        help="Optional paraphrase candidate to validate before formatting the final response.",
    )
    return parser


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = run_grounded_demo(args.message, paraphrase_candidate=args.paraphrase)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
