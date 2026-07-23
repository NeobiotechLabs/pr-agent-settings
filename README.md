# pr-agent-settings

**Organization 전역 AI PR 자동 리뷰 중앙 설정 저장소** — 오픈소스 Qodo Merge(구 PR-Agent)와 보유 중인 프론티어 LLM API(GLM/MiniMax)를 결합하여, **Organization 내 모든 Repository에 AI PR 리뷰를 일괄 적용**하는 시스템입니다.

> Gemini Code Assist 서비스 중단에 따른 대체재로 도입되었습니다. GitHub Actions 기반으로 인프라 비용은 0원이며, LLM API 토큰 비용만 발생합니다.

## 작동 방식

개별 프로젝트 저장소마다 설정 파일을 심지 않고, 이 중앙 공용 저장소 하나가 AI 모델 설정과 리뷰 규칙을 통합 관리합니다. GitHub Organization **Repository Rulesets**로 리뷰 워크플로를 조직 내 모든 저장소에 주입하며, 중앙 저장소의 파일을 수정하면 **조직 전체에 즉시 실시간 반영**됩니다.

```text
[공용 저장소: pr-agent-settings]
  ├── .pr_agent.toml          <-- 전체 AI 모델 설정 (GLM / MiniMax) 및 리뷰 규칙
  └── .github/workflows/
        └── global-review.yml <-- GitHub Repository Rulesets에 의해 조직 내 전역 실행
```

## 주요 파일

| 경로 | 역할 |
|---|---|
| `.pr_agent.toml` | 전역 AI 모델(GLM/MiniMax) 설정, PR 생성 시 자동 실행 명령(`/review`, `/describe`), 리뷰 규칙 |
| `.github/workflows/global-review.yml` | 전역 AI 리뷰 워크플로 — 조직 내 모든 저장소의 PR 이벤트(opened/reopened/synchronize)에서 실행 |
| `docs/guide.md` | 구축·연동 가이드 (Rulesets 설정, 시크릿 등록, 트러블슈팅) |

## 팀원 사용 방법

별도의 설정 없이 평소대로 PR을 생성하면 됩니다.

**자동 기능**
- PR 생성 시 AI가 변경점 요약 설명(`/describe`)을 작성하고, 한 줄 단위 코드 리뷰 및 취약점 분석(`/review`)을 PR에 남깁니다.

**수동 명령어 (PR 댓글 창에 입력)**
- `/review` — 전체 코드 정밀 재리뷰
- `/improve` — 가독성·리팩토링 제안을 코드 제안(Suggestion) 박스로 제공
- `/ask [질문내용]` — 이 PR의 변경 코드에 대해 AI에게 직접 질문

## 예외 및 주의 사항

- **프로젝트별 오버라이드**: 개별 저장소 루트에 `.pr_agent.toml`을 직접 생성하면 해당 저장소의 설정이 최우선으로 적용됩니다. (예: 특정 팀만 리뷰 언어·점수 산정 방식을 다르게 운영)
- ⚠️ **AI 리뷰가 작동하지 않을 때**: 대상 저장소에 `.github/workflows/*.yml` 파일이 하나도 없는 완전 빈 상태면 전역 워크플로가 실행되지 않습니다(GitHub 정책). 워크플로 표지 파일(`pr_review.yml`)을 하나 추가하면 해결됩니다 — **반드시 유효한 YAML**이어야 하며, 빈 파일/유효하지 않은 파일은 실패 실행을 만들고 Actions 시간을 소모합니다(예시는 [docs/guide.md](docs/guide.md) §7 참고). 이미 CI를 사용하는 저장소는 별도 조치가 필요 없습니다.

## 관리자 가이드

Organization 시크릿(`GLOBAL_LLM_API_KEY`) 등록, Repository Rulesets 설정, 모델·엔드포인트 구성 등 전체 구축 절차는 **[docs/guide.md](docs/guide.md)** 를 참고하세요.


## QODO Review Test

PR 리뷰 테스트를 위한 파일 변경 건

- 3차 검증 (2026-07-22): litellm `zai/` 모델 접두사(`zai/glm-5`) 적용 후 `/review`·`/describe` 한국어 출력 확인

<!-- 테스트용 curl 명령어에 API 키가 평문으로 노출되어 제거함 — API 키는 Organization 시크릿(GLOBAL_LLM_API_KEY)으로만 관리합니다 -->

- .pr_agent.toml 파일 수정 (아래 라인 추가)
[openai]
api_base = "https://api.z.ai/api/coding/paas/v4"

- PR 재생성

- 2차 검증 (2026-07-22): `custom_model_max_tokens`·`[pr_reviewer]`·`response_language` 설정 수정 후 `/review`·`/describe` 한국어 출력 확인
- 