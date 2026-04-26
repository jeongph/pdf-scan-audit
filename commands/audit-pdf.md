---
description: 스캔 PDF 품질 정밀 진단 - 페이지 누락/순서/회전/잘림 검출
argument-hint: [pdf-paths...]
---

# /audit-pdf

스캔 PDF 한 권 또는 여러 권의 품질을 검사합니다.

## 인자
- `$ARGUMENTS` — 검사할 PDF 경로(공백 구분, 여러 개 가능). 비어 있으면 현재 디렉토리의 `*.pdf` 후보로 안내.

## 동작
`pdf-scan-audit` skill의 워크플로우 그대로 실행:

1. 의존성 확인(`python3 -c "import fitz"`)
2. 임시 작업 디렉토리 생성
3. 메타·콘텐츠·페이지번호 검사 3종 실행
4. 의심 페이지 PNG 추출 및 시각 검증
5. 마크다운 표로 결과 보고
6. 임시 디렉토리 자동 정리(`--keep` 미지정 시)

## 옵션
- `--keep` — 결과 디렉토리 보존(검사 후 경로 안내)

자세한 절차는 `${CLAUDE_PLUGIN_ROOT}/skills/pdf-scan-audit/SKILL.md` 참조.
