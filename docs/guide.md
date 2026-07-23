# [가이드] Organization 전역 AI PR 자동 리뷰 시스템 구축 및 연동 (Qodo Merge)

* **작성일**: 2026-07-22
* **마지막 수정**: 2026-07-23 — 워크플로 표지 파일(pr_review.yml) 유효 YAML 요건, Rulesets 대상 브랜치 함정 및 "Waiting for workflow to run" 해소법, 긴급 머지용 Bypass list, toml 예시 실설정 일치화
* **문서 목적**: Gemini Code Assist 서비스 중단에 따른 대체재로, 보유 중인 프론티어 LLM API(GLM/MiniMax)와 오픈소스 Qodo Merge(구 PR-Agent)를 결합하여 **Organization 내 모든 Repository에 AI PR 리뷰 시스템을 일괄 적용**하는 방법을 안내합니다.

---

## 1. 시스템 개요 및 아키텍처
개별 프로젝트 저장소마다 설정 파일을 심지 않고, **중앙 공용 저장소 단 1개**를 개설하여 조직 전체의 프롬프트 규칙과 GitHub Actions 워크플로우를 통합 관리합니다.

```text
[공용 저장소: pr-agent-settings]
  ├── .pr_agent.toml          <-- 전체 AI 모델 설정 (GLM / MiniMax) 및 리뷰 규칙
  └── .github/workflows/
        └── global-review.yml <-- GitHub Repository Rulesets에 의해 조직 내 전역 실행
```

* **비용**: 인프라 비용 0원 (GitHub Actions 사용) + API 토큰 비용만 발생
* **특징**: 프롬프트나 모델을 변경할 때 중앙 저장소의 파일만 수정하면 조직 전체에 즉시 실시간 반영됩니다.
* **네트워크**: 지연 최소화를 위해 중국 내수용 주소(`bigmodel.cn`) 대신 글로벌 전용 엔드포인트 인프라(`api.z.ai` / `minimax.io`)를 적용합니다.

---

## 2. 사전 준비 사항 (Prerequisites)
작업을 시작하기 전 아래의 정보와 권한이 준비되어 있어야 합니다.
1. **GitHub Organization Owner(관리자) 권한**
2. **LLM API Key 및 글로벌 엔드포인트 정보**
   * **GLM (Zhipu AI)**: `https://api.z.ai/api/coding/paas/v4` (코딩 최적화 글로벌 엔드포인트)
   * **MiniMax**: `https://api.minimax.io` (글로벌 리전 API 엔드포인트)

---

## 3. 구축 단계별 프로세스

### 1단계: 중앙 공용 저장소 구성
1. GitHub Organization 내에 **`pr-agent-settings`**라는 이름의 Public 또는 Private 저장소를 생성합니다. (※ 저장소 명칭은 규칙이므로 대소문자 일치 필수)
2. 저장소 루트에 AI 모델 환경을 정의하는 `.pr_agent.toml` 파일을 생성하고 아래 내용을 작성합니다.

```toml
# .pr_agent.toml
[github_app]
# PR 생성/재오픈/수정 시 자동으로 실행할 기본 명령어
pr_commands = ["/review", "/describe"]

[config]
# 사용하려는 모델 코드 기입 — litellm 프로바이더 접두사 필수 (예: GLM은 zai/glm-5, OpenAI-호환 커스텀은 openai/<모델>)
model = "zai/glm-5"
fallback_model = "zai/glm-5"
# 내장 fallback(gpt-5.4-mini)은 Z.ai에서 400(Unknown Model)을 반환하므로 비활성화
fallback_models = []
# 내부에 등록되지 않은 커스텀 모델(glm-5 등)은 토큰 한계를 반드시 명시 — 미설정 시 예측이 즉시 실패함
custom_model_max_tokens = 131072
# 리뷰 출력 언어: 한국어
response_language = "ko"

[openai]
api_base = "https://api.z.ai/api/coding/paas/v4"

[pr_reviewer]
# AI 리뷰어의 성격 설정 (주의: 섹션명은 pr_review가 아니라 pr_reviewer)
require_score_review = true
```

3. 이어서 `.github/workflows/global-review.yml` 경로에 워크플로우 파일을 생성하고 아래 코드를 작성합니다.

```yaml
name: Global AI PR Reviewer
on:
  pull_request:
    types: [opened, reopened, synchronize]
  # PR 댓글 창에 입력된 수동 명령어(/review, /improve, /ask)를 감지하기 위한 트리거 (가이드 §6)
  issue_comment:

jobs:
  pr_agent_job:
    # 봇 자신의 댓글에는 응답하지 않도록 하여 무한 루프 방지
    if: ${{ github.event.sender.type != 'Bot' }}
    runs-on: ubuntu-latest
    permissions:
      issues: write
      pull-requests: write
      contents: read
    steps:
      - name: Run Qodo Merge (PR-Agent)
        uses: The-PR-Agent/pr-agent@main
        env:
          OPENAI_API_KEY: ${{ secrets.GLOBAL_LLM_API_KEY }}
          # GitHub 인증 토큰 (GitHub가 자동으로 제공) — PR에 리뷰 댓글을 작성하려면 필수
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          # 사용하는 LLM 인프라에 맞춰 아래 주소 중 하나를 활성화하십시오.
          OPENAI_API_BASE: "https://api.z.ai/api/coding/paas/v4" # GLM 사용 시 (코딩 최적화 글로벌 엔드포인트)
          # OPENAI_API_BASE: "https://api.minimax.io/v1" # MiniMax 사용 시
```

---

## 4. Organization 전역 시크릿(Secret) 등록
공용 워크플로우가 개별 프로젝트에서 실행될 때 API 키를 안전하게 호출할 수 있도록 조직 레벨에 등록합니다.
1. **Organization Settings** -> **Security** -> **Secrets and variables** -> **Actions** 메뉴로 이동합니다.
2. **New organization secret** 버튼을 클릭합니다.
3. 아래 정보로 시크릿을 생성합니다.
   * **Name**: `GLOBAL_LLM_API_KEY`
   * **Value**: [보유 중인 GLM 또는 MiniMax API Key 입력]
   * **Repository access**: **All repositories** 선택

---

## 5. Repository Rulesets을 통한 일괄 강제 배포
조직 내 모든 저장소에 별도의 작업 없이 워크플로우를 주입하는 핵심 단계입니다.
1. **Organization Settings** -> **Code, planning, and automation** -> **Repository rulesets** 메뉴로 이동합니다.
2. **New ruleset** -> **New repository ruleset**을 클릭합니다.
3. 규칙 세트를 다음과 같이 설정합니다:
   * **Ruleset Name**: `Global-AI-Review-Enforcement`
   * **Enforcement status**: **Evaluate** (우선 테스트) 또는 **Active** (즉시 적용)
     * **Evaluate**: 리뷰 워크플로는 실행·표시되지만 머지를 차단하지 않습니다(소프트 런칭용). 안정화 후 **Active**로 전환하면 강제 적용됩니다.
   * **Target repositories**: **All repositories** (원할 경우 특정 레포지토리 제외 가능)
   * **Target branches**: 기본 브랜치(`main`)를 포함하려면 반드시 전용 옵션인 **"Include default branch"**를 사용하십시오.
     * ⚠️ "Include by pattern" 입력란에 `~DEFAULT_BRANCH`를 직접 입력하면 **리터럴 문자열 패턴**으로 해석되어 매칭 대상이 0개("Applies to 0 targets")가 되고, 필수 워크플로가 어떤 PR에도 주입되지 않습니다. (2026-07-23 실제 장애 사례)
4. 아래 **Rules** 섹션에서 **"Require a workflow to pass before merging"** 조건을 찾아 체크합니다.
5. **Add workflow**를 눌러 아래 정보를 맵핑하고 저장합니다:
   * **Repository**: `pr-agent-settings`
   * **Workflow**: `.github/workflows/global-review.yml`

### ⚠️ 이미 열려 있던 PR이 "Waiting for workflow to run"에 멈췄을 때
GitHub 필수 워크플로는 **요구사항이 활성 상태로 적용된 이후에 발생한 PR 이벤트**(opened / synchronize / reopened)에 대해서만 실행을 생성합니다. 따라서 룰셋을 생성하거나 대상 브랜치를 수정하기 **전에 이미 열려 있던 PR**은 체크 항목이 "Expected — Waiting for workflow to run" 상태로 계속 대기하며 머지가 차단됩니다. (Actions 탭에도 큐/실행이 나타나지 않는 것이 특징입니다.)
* **해결책**: 해당 PR을 **닫았다 다시 열기(close + reopen)** 하거나 **새 커밋을 push**하여 새 PR 이벤트를 발생시키면 워크플로가 실행됩니다. close+reopen 시 `/review`·`/describe`도 함께 생성됩니다. (2026-07-23 DynamicNavigation PR #39에서 close+reopen으로 해소 확인)
* 룰셋 적용 여부는 **Rulesets Insights** 또는 대상 PR의 **Checks** 탭에서 필수 체크가 실제로 생성되었는지 확인하십시오.

### 🚨 긴급 머지가 필요할 때 — Bypass list 설정 (권장)
리뷰 완료 여부와 관계없이 긴급하게 머지해야 하는 경우가 있으므로, Rulesets의 **Bypass list**에 우회 권한을 지정해 둡니다.
1. 해당 룰셋 편집 화면에서 **Bypass list** 섹션 → **Add bypass**를 클릭합니다.
2. 우회 권한을 부여할 대상을 추가합니다:
   * 역할: **Repository admin**, **Organization owner** 등
   * 또는 특정 팀(예: oncall·릴리즈 담당 팀)이나 GitHub App
3. **Bypass mode**를 선택합니다:
   * **Always**: 모든 보호 규칙 우회
   * **For pull requests only**: PR 관련 규칙(필수 워크플로 등)만 우회하고 다른 보호는 유지 — 권장
4. 저장하면, 지정된 인원은 필수 체크가 대기 중이거나 실패해도 머지 박스에서 **"Bypass required checks and merge"**로 긴급 머지할 수 있습니다. 모든 우회 이력은 **Rulesets Insights**에 감사 로그로 남습니다.

> ⚠️ 구 브랜치 보호(Branch protection)의 "Include administrators" 같은 **관리자 암묵 우회는 Rulesets에 없습니다.** Organization Owner라도 Bypass list에 추가되지 않으면 머지가 차단되므로 반드시 위 설정이 필요합니다.
>
> 참고: 필수 워크플로 규칙 자체를 제거하면 워크플로 주입 메커니즘이 함께 사라집니다(규칙이 곧 주입입니다). 따라서 규칙 삭제는 우회 옵션이 아니며, 임시로 전 조직의 차단을 풀려면 Enforcement status를 **Evaluate**로 전환하십시오.

---

## 6. 팀원들을 위한 사용 방법 및 가이드

시스템 구축이 완료되면 팀원들은 별도의 설정 없이 평소대로 PR을 생성하면 됩니다.

### 자동 기능
* **PR 생성 시**: AI가 코드 변경점을 요약하여 상세 안내를 작성하고(`/describe`), 곧바로 한 줄 단위 코드 리뷰 댓글 및 취약점 분석 결과(`/review`)를 PR 창에 남깁니다.

### 수동 명령어 (PR 댓글 창 활용)
리뷰 도중 AI에게 추가 작업을 요청하고 싶다면 PR 댓글 창에 아래 명령어를 입력하면 봇이 감지하여 응답합니다.
* `/review` : 전체 코드를 다시 정밀 리뷰합니다.
* `/improve` : 코드 가독성 및 리팩토링 제안 사항을 코드 제안(Suggestion) 박스 형태로 받아봅니다.
* `/ask [질문내용]` : 이 PR에 작성된 변경 코드에 대해 AI에게 궁금한 점을 직접 질문합니다.

---

## 7. 고급 활용 및 예외 처리 (고급팀 가이드)

### 특정 프로젝트에서 별도의 프롬프트/규칙을 쓰고 싶을 때
기본적으로 공용 저장소의 `.pr_agent.toml` 정책을 따르지만, 특정 프로젝트 저장소 루트에 `.pr_agent.toml`을 직접 생성하여 작성하면 **그 개별 저장소의 설정이 최우선(Override)으로 적용**됩니다. (예: 특정 팀만 영어로 리뷰를 받거나 점수 산정 방식을 다르게 하고 싶을 때 활용)

### ⚠️ 중요 주의 사항 (트러블슈팅)
GitHub 정책에 따라, 조직 단위로 전역 워크플로우를 배포하더라도 **대상이 되는 프로젝트 저장소 내에 어떠한 GitHub Actions 파일(`.github/workflows/*.yml`)도 존재하지 않는 완전 빈 상태**라면 전역 워크플로우가 실행되지 않는 이슈가 있습니다.
* **해결책**: AI 리뷰가 작동하지 않는 저장소가 있다면, 해당 저장소 내에 워크플로 표지 파일(`pr_review.yml`)을 하나 생성해 두면 정상 작동합니다. 이미 빌드/배포 CI를 쓰는 저장소는 별도 조치가 필요 없습니다.

#### 🚫 표지 파일은 반드시 "유효한 워크플로 YAML"이어야 합니다
빈 파일(0바이트)이나 유효하지 않은 YAML을 넣으면 **절대 안 됩니다.** GitHub가 해당 파일을 "Invalid workflow file"으로 처리하고, 그 파일이 포함된 브랜치에 push할 때마다 **이름이 `.github/workflows/pr_review.yml`인 실패 워크플로 실행**을 생성합니다. 이 실패 실행은 Actions 탭을 어지럽히고 **Actions 사용 시간(minutes)을 소모**하며, 소진 시 필수 워크플로 실행 자체가 막힐 수 있습니다("You may have run out of available minutes with this required workflow" 메시지).
* **올바른 표지 파일 예시**: 자동 실행되지 않는 수동 트리거 전용 워크플로로 생성합니다.

```yaml
# 자리표시(placeholder) 워크플로 — Organization 전역 주입 워크플로
# (pr-agent-settings의 global-review.yml)의 트리거 조건을 만족시키기 위한 표지 파일입니다.
# 실제 AI 리뷰는 조직 주입 워크플로가 수행하며, 이 파일은 자동 실행되지 않고
# 어떠한 작업도 수행하지 않습니다.
name: PR Review (placeholder)
on:
  workflow_dispatch:  # 수동 트리거 전용 — push/PR 시 자동 실행되지 않음
jobs:
  noop:
    runs-on: ubuntu-latest
    steps:
      - run: 'true'
```

---

**문서 관련 문의 및 개선 제안**: [본인 슬랙 아이디/이메일]
