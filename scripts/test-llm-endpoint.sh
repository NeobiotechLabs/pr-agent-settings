#!/usr/bin/env bash
# LLM 엔드포인트 사전 검증 스크립트 — GitHub 반영 전 키/엔드포인트/모델명을 확인합니다.
#
# 사용법:
#   bash scripts/test-llm-endpoint.sh [모델명] [베이스_URL]
#   예) bash scripts/test-llm-endpoint.sh                        # 기본: glm-5 + api.z.ai
#       bash scripts/test-llm-endpoint.sh minimax-m3 https://api.minimax.io
#
# API 키 제공 방법 (둘 중 하나):
#   1) .secrets.local 파일에 키를 한 줄로 기록 (gitignore됨 — 대화/저장소에 남지 않음, 권장)
#   2) 환경변수 GLM_API_KEY 설정
set -euo pipefail

MODEL="${1:-glm-5}"
BASE_URL="${2:-https://api.z.ai/api/coding/paas/v4}"

if [[ -n "${GLM_API_KEY:-}" ]]; then
  KEY="$GLM_API_KEY"
elif [[ -f .secrets.local ]]; then
  KEY="$(tr -d ' \r\n' < .secrets.local)"
else
  echo "에러: API 키가 없습니다. .secrets.local 파일에 키를 기록하거나 GLM_API_KEY 환경변수를 설정하세요." >&2
  exit 1
fi

echo "엔드포인트 : ${BASE_URL}/chat/completions"
echo "모델       : ${MODEL}"
echo "키         : ${KEY:0:6}...${KEY: -4} (마스킹됨)"
echo "---"

RESP_FILE="$(mktemp)"
HTTP_CODE=$(curl -sS -w '%{http_code}' -o "$RESP_FILE" \
  "${BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${KEY}" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"${MODEL}\", \"messages\": [{\"role\": \"user\", \"content\": \"ping - reply with just the word pong\"}], \"max_tokens\": 20}")

echo "HTTP 상태: ${HTTP_CODE}"
echo "응답 본문:"
cat "$RESP_FILE"
echo ""
echo "---"
case "$HTTP_CODE" in
  200) echo "✅ 통과: 키·엔드포인트·모델명 모두 정상입니다." ;;
  401|403) echo "❌ 인증 실패: API 키를 확인하세요." ;;
  404) echo "❌ 경로/모델 없음: 엔드포인트 URL이나 모델명(${MODEL})을 확인하세요." ;;
  *) echo "❌ 기타 오류: 위 응답 본문을 확인하세요." ;;
esac
rm -f "$RESP_FILE"
