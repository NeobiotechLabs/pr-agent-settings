# [가이드] Organization 전역 AI PR 자동 리뷰 시스템 구축 및 연동 (Qodo Merge)

* **작성일**: 2026-07-22
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
# 사용하려는 모델 코드 기입 (예: glm-5, minimax-m3 등)
# 커스텀 OpenAI-호환 엔드포인트 모델은 litellm 라우팅을 위해 반드시 "openai/" 접두사 필요
model = "openai/glm-5"
model_wrapper = "OpenAI"
fallback_model = "openai/glm-5"
# 내장 fallback(gpt-5.4-mini)은 Z.ai에서 400(Unknown Model)을 반환하므로 비활성화
fallback_models = []
# 내부에 등록되지 않은 커스텀 모델(glm-5 등)은 토큰 한계를 반드시 명시 — 미설정 시 예측이 즉시 실패함
custom_model_max_tokens = 131072
# 리뷰 출력 언어: 한국어
response_language = "ko"

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

jobs:
  pr_agent_job:
    runs-on: ubuntu-latest
    permissions:
      issues: write
      pull-requests: write
      contents: read
    steps:
      - name: Run Qodo Merge (PR-Agent)
        uses: The-PR-Agent/pr-agent@main
        env:
          OPENAI_API_KEY: \${{ secrets.GLOBAL_LLM_API_KEY }}
          # 사용하는 LLM 인프라에 맞춰 아래 주소 중 하나를 활성화하십시오.
          OPENAI_API_BASE: "https://z.ai" # GLM 사용 시
          # OPENAI_API_BASE: "https://minimax.io"         # MiniMax 사용 시
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
   * **Target repositories**: **All repositories** (원할 경우 특정 레포지토리 제외 가능)
4. 아래 **Rules** 섹션에서 **"Require a workflow to pass before merging"** 조건을 찾아 체크합니다.
5. **Add workflow**를 눌러 아래 정보를 맵핑하고 저장합니다:
   * **Repository**: `pr-agent-settings`
   * **Workflow**: `.github/workflows/global-review.yml`

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
* **해결책**: AI 리뷰가 작동하지 않는 저장소가 있다면, 해당 저장소 내에 더미 파일(예: `blank.yml`)을 하나 생성해 두면 정상 작동합니다. 이미 빌드/배포 CI를 쓰는 저장소는 별도 조치가 필요 없습니다.

---

**문서 관련 문의 및 개선 제안**: [본인 슬랙 아이디/이메일]
