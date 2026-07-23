# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 응답 언어 규칙

- **항상 한국어로 응답한다.** (PR 리뷰 댓글, PR 설명, 커밋 메시지 작성 시에도 한국어 사용)

## 저장소 역할

이 저장소는 보유 중인 프론티어 LLM API(GLM/MiniMax)와 오픈소스 Qodo Merge(구 PR-Agent)를 결합해 **Organization 내 모든 Repository에 AI PR 자동 리뷰를 일괄 적용**하기 위한 **중앙 공용 설정 저장소**입니다. 애플리케이션 코드가 없고 전역 설정·워크플로만 관리하므로 **빌드/테스트/린트 명령이 없습니다.**

**핵심 빅픽처**: 이 저장소의 `.pr_agent.toml`과 워크플로는 이 저장소 자체가 아니라, GitHub Repository Rulesets를 통해 **Organization 전체 저장소에 주입**됩니다. 즉 여기의 모든 편집은 **조직 전체에 실시간 반영되는 운영(production) 설정 변경**입니다.

## 여러 파일을 읽어야 이해되는 핵심 메커니즘

1. **전역 주입**: `.github/workflows/global-review.yml`은 조직 Rulesets("Require a workflow to pass before merging", Repository: `pr-agent-settings`)에 맵핑되어 조직 내 모든 저장소의 PR에서 실행됩니다. 이 저장소 내부에서 직접 트리거되는 워크플로가 아닙니다.
2. **설정 우선순위**: 대상 저장소가 자체 루트에 `.pr_agent.toml`을 두면, 이 저장소의 전역 `.pr_agent.toml`보다 **개별 저장소 설정이 우선(Override)** 적용됩니다.
3. **알려진 함정**: 대상 저장소에 `.github/workflows/*.yml` 파일이 하나도 없는 완전 빈 상태면 전역 워크플로가 실행되지 않습니다. 워크플로 표지 파일(`pr_review.yml`) 추가로 해결하며, 이미 CI가 있는 저장소는 조치가 필요 없습니다.
4. **단일 출처 문서**: `docs/guide.md`가 이 시스템의 구축·연동 가이드이자 설정값·워크플로 내용·Rulesets/시크릿 등록 절차의 기준 문서입니다.

## 작업 시 알아야 할 규약

- 가이드가 정의하는 목표 구조: 루트 `.pr_agent.toml`, `.github/workflows/global-review.yml`, `docs/guide.md` — 파일 실존 여부는 디스크 상태에서 확인할 것.
- **엔드포인트**: 지연 최소화를 위해 항상 **글로벌 전용 엔드포인트**(GLM `https://api.z.ai/api/coding/paas/v4`, MiniMax `https://api.minimax.io/v1`)를 사용 함. 추후 다른 모델 사용이 필요하면, global-review.yml에 OPENAI_API_BASE 변경 필요
- **API 키**는 Organization 시크릿 `GLOBAL_LLM_API_KEY`(All repositories 접근)로만 관리하며 어떤 파일에도 직접 기재하지 않습니다.
- **리뷰 출력 언어** 기본값은 한국어(`reply_language = "ko"`)입니다.
- `.pr_agent.toml` / `global-review.yml` 수정 시 항상 `docs/guide.md`의 예제와 일관성을 맞춰야 하며, 조직 전체에 영향이 가므로 diff를 최소화합니다.
