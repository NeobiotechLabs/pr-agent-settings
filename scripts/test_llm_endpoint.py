#!/usr/bin/env python3
"""LLM 엔드포인트 사전 검증 스크립트 — litellm으로 실제 호출하여 모델/키/URL 조합 확인

사용법:
  python scripts/test_llm_endpoint.py                  # 기본 모델(minimax) 테스트
  python scripts/test_llm_endpoint.py --model glm      # 특정 모델 테스트
  python scripts/test_llm_endpoint.py --all            # 등록된 모든 모델 테스트
  python scripts/test_llm_endpoint.py --list           # 사용 가능한 모델 목록 표시

API 키 제공 방법 (우선순위):
  1) 환경변수 LLM_API_KEY
  2) .secrets.local 파일에 키를 한 줄로 기록 (gitignore됨 — 권장)

의존성:
  pip install litellm
"""

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
MODELS_FILE = SCRIPT_DIR / "models.json"
SECRETS_FILE = REPO_ROOT / ".secrets.local"


def load_api_key() -> str | None:
    """API 키를 환경변수 또는 .secrets.local에서 로드한다."""
    key = os.environ.get("LLM_API_KEY", "").strip()
    if key:
        return key
    if SECRETS_FILE.exists():
        return SECRETS_FILE.read_text().strip()
    return None


def load_models() -> list[dict]:
    """models.json에서 모델 설정 목록을 로드한다."""
    if not MODELS_FILE.exists():
        print(f"❌ 모델 설정 파일을 찾을 수 없습니다: {MODELS_FILE}", file=sys.stderr)
        sys.exit(1)
    with open(MODELS_FILE) as f:
        return json.load(f)["models"]


def list_models(models: list[dict]) -> None:
    """사용 가능한 모델 목록을 출력한다."""
    print("사용 가능한 모델:")
    print("─" * 60)
    for m in models:
        env_key = m.get("env_key", "OPENAI_API_KEY")
        print(f"  {m['name']:<14s} {m['label']:<22s} {m['base_url']}")
        print(f"  {'':14s} litellm model: {m['model']}  (env: {env_key})")
    print()
    print("기본값: minimax")


def test_model(base_url: str, model: str, label: str, api_key: str, env_key: str = "OPENAI_API_KEY") -> bool:
    """litellm으로 단일 모델을 호출하여 성공 여부를 반환한다.

    global-review.yml과 동일한 방식: 환경변수를 설정한 뒤 litellm.completion()을 호출한다.
    litellm은 provider별로 다른 환경변수를 확인하므로, env_key에 따라 설정한다.
    """
    try:
        import litellm
    except ImportError:
        print("❌ litellm이 설치되어 있지 않습니다.", file=sys.stderr)
        print("   pip install litellm", file=sys.stderr)
        sys.exit(1)

    print("─" * 60)
    print(f"엔드포인트 : {base_url}")
    print(f"모델       : {model} ({label})")
    print(f"키         : {api_key[:6]}...{api_key[-4:]} (masked)")
    print(f"환경변수   : {env_key}")
    print("─" * 60)

    # 워크플로와 동일하게 환경변수 설정 + api_key 명시적 전달
    os.environ[env_key] = api_key
    os.environ["OPENAI_API_BASE"] = base_url

    try:
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": "ping - reply with just the word pong"}],
            max_tokens=20,
            api_key=api_key,
        )
        content = response.choices[0].message.content
        print(f"응답       : {content}")
        print("─" * 60)
        print("✅ [PASS] key / endpoint / model 모두 정상")
        return True

    except litellm.AuthenticationError as e:
        print(f"HTTP 상태  : 401/403")
        print(f"오류       : {e}")
        print("─" * 60)
        print("❌ [FAIL] 인증 오류 — API 키를 확인하세요")
        return False

    except litellm.NotFoundError as e:
        print(f"HTTP 상태  : 404")
        print(f"오류       : {e}")
        print("─" * 60)
        print(f"❌ [FAIL] 모델 미발견 — 모델명({model})을 확인하세요")
        return False

    except litellm.APIConnectionError as e:
        print(f"오류       : {e}")
        print("─" * 60)
        print("❌ [FAIL] 연결 실패 — 엔드포인트 URL을 확인하세요")
        return False

    except litellm.APIError as e:
        print(f"오류       : {e}")
        print("─" * 60)
        print("❌ [FAIL] API 오류 — 위 메시지를 확인하세요")
        return False

    except Exception as e:
        print(f"예상치 못한 오류: {type(e).__name__}: {e}")
        print("─" * 60)
        print("❌ [FAIL]")
        return False


def find_model(models: list[dict], name: str) -> dict | None:
    """이름으로 모델 설정을 찾는다."""
    for m in models:
        if m["name"] == name:
            return m
    return None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LLM 엔드포인트 사전 검증 스크립트 (litellm 기반)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model", "-m", default="minimax",
        help="테스트할 모델 이름 (기본: minimax)",
    )
    parser.add_argument(
        "--all", "-a", action="store_true",
        help="등록된 모든 모델을 테스트",
    )
    parser.add_argument(
        "--list", "-l", action="store_true",
        help="사용 가능한 모델 목록 표시",
    )
    args = parser.parse_args()

    models = load_models()

    if args.list:
        list_models(models)
        return

    # API 키 확인
    api_key = load_api_key()
    if not api_key:
        print("❌ API 키가 없습니다.", file=sys.stderr)
        print("   .secrets.local 파일에 키를 기록하거나 LLM_API_KEY 환경변수를 설정하세요.", file=sys.stderr)
        sys.exit(1)

    if args.all:
        failures = 0
        for m in models:
            env_key = m.get("env_key", "OPENAI_API_KEY")
            if not test_model(m["base_url"], m["model"], m["label"], api_key, env_key):
                failures += 1
            print()
        print("═" * 60)
        if failures == 0:
            print("✅ 모든 모델 테스트 통과")
        else:
            print(f"❌ {failures}개 모델 테스트 실패")
        sys.exit(failures)
    else:
        m = find_model(models, args.model)
        if not m:
            print(f"❌ 모델 '{args.model}'을(를) 찾을 수 없습니다.", file=sys.stderr)
            print(file=sys.stderr)
            list_models(models)
            sys.exit(1)
        env_key = m.get("env_key", "OPENAI_API_KEY")
        if not test_model(m["base_url"], m["model"], m["label"], api_key, env_key):
            sys.exit(1)


if __name__ == "__main__":
    main()
