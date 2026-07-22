# LLM 엔드포인트 사전 검증 스크립트 (PowerShell 버전) — GitHub 반영 전 키/엔드포인트/모델명 확인
#
# 사용법 (저장소 루트에서):
#   pwsh scripts\test-llm-endpoint.ps1
#   pwsh scripts\test-llm-endpoint.ps1 -Model minimax-m3 -BaseUrl https://api.minimax.io
#
# API 키 제공 방법 (둘 중 하나):
#   1) .secrets.local 파일에 키를 한 줄로 기록 (gitignore됨 — 권장)
#   2) 환경변수 GLM_API_KEY 설정
param(
  [string]$Model = "glm-5",
  [string]$BaseUrl = "https://api.z.ai/api/coding/paas/v4"
)

if ($env:GLM_API_KEY) {
  $key = $env:GLM_API_KEY.Trim()
} elseif (Test-Path .secrets.local) {
  $key = (Get-Content .secrets.local -Raw).Trim()
} else {
  Write-Error "API 키가 없습니다. .secrets.local 파일에 키를 기록하거나 GLM_API_KEY 환경변수를 설정하세요."
  exit 1
}

Write-Output "Endpoint : $BaseUrl/chat/completions"
Write-Output "Model    : $Model"
Write-Output "Key      : $($key.Substring(0,6))...$($key.Substring($key.Length-4)) (masked)"
Write-Output "---"

$body = @{
  model      = $Model
  messages   = @(@{ role = "user"; content = "ping - reply with just the word pong" })
  max_tokens = 20
} | ConvertTo-Json -Compress

try {
  $resp = Invoke-RestMethod -Uri "$BaseUrl/chat/completions" -Method Post `
    -Headers @{ Authorization = "Bearer $key" } `
    -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($body))
  Write-Output "HTTP status: 200"
  Write-Output "Response:"
  $resp | ConvertTo-Json -Depth 10
  Write-Output "---"
  Write-Output "[PASS] key / endpoint / model all OK"
} catch {
  $status = $_.Exception.Response.StatusCode.value__
  Write-Output "HTTP status: $status"
  Write-Output "Response:"
  Write-Output $_.ErrorDetails.Message
  Write-Output "---"
  if ($status -in 401, 403) {
    Write-Output "[FAIL] auth error - check the API key"
  } elseif ($status -eq 404) {
    Write-Output "[FAIL] not found - check endpoint URL or model name ($Model)"
  } else {
    Write-Output "[FAIL] see response body above"
  }
  exit 1
}
