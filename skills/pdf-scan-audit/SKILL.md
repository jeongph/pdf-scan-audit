---
name: pdf-scan-audit
description: Use this skill when the user wants to inspect, audit, verify or check scanned PDF books for quality issues — page integrity, scan errors, missing/duplicated/misordered pages, rotated pages, cropped or skewed content, OCR quality, page number continuity, page size consistency. Korean triggers (사용자가 한글로 요청하는 자연스러운 표현 포함) "PDF 검사", "PDF 검사해줘", "스캔 검사", "스캔 품질", "페이지 누락", "페이지 누락이나 회전", "스캐너로 스캔한", "스캐너로 스캔", "스캔한 PDF", "책 스캔 검사", "책 스캔 확인", "페이지 회전 잘못", "페이지 잘렸", "순서 안 맞", "순서가 맞나", "잘못된 페이지", "메타데이터만 말고", "메타데이터만 확인하지 말고", "정확하고 자세하게 검사", "스캔본 검사", "스캔본 확인", "PDF 점검". English triggers "audit PDF", "audit scanned PDF", "check scanned PDF", "scan quality", "page integrity", "missing pages", "rotated page", "cropped page", "PDF quality report". Works on scanned PDFs (primary) and digital PDFs (partial checks).
---

# PDF Scan Audit

스캔 PDF의 품질을 정밀 진단합니다. 612페이지짜리 책도 5분 내에 메타·콘텐츠·페이지번호 연속성을 검사하고, 의심 페이지만 골라 시각 검증한 뒤 표로 보고합니다.

## 적용 대상

- **메인 타겟**: 종이책을 스캐너로 읽은 PDF (Epson ScanSmart, ScanSnap, FineReader 등 출력)
- **부분 적용**: 디지털 PDF — 회전·페이지 크기·페이지번호 연속성은 의미 있음. 빈 페이지·이미지 커버리지 등은 자동 스킵

## 워크플로우

### 1. 입력 확인
- 사용자가 지정한 PDF 경로(들)를 받는다. 다중 PDF 지원.
- 인자가 없으면 작업 디렉토리의 `*.pdf` 모두 후보로 보고 사용자에게 확인

### 2. 의존성 점검
```bash
python3 -c "import fitz" 2>&1
```
- `ModuleNotFoundError`면 `pip install pymupdf` 안내 후 중단
- 사용자가 설치를 거부하면 진행 불가 → 그대로 보고

### 3. 임시 작업 디렉토리 생성
```bash
WORKDIR=$(mktemp -d -t pdf-scan-audit-XXXXXX)
echo "WORKDIR=$WORKDIR"
```
- 모든 중간 산출물(JSON 결과·PNG)은 이 디렉토리에 저장
- 작업 디렉토리(사용자 cwd)에는 **아무 것도 남기지 않음**

### 4. 메타 검사 (`inspect_meta.py`)
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pdf-scan-audit/scripts/inspect_meta.py "$PDF" > "$WORKDIR/meta.json"
```
다음을 수집:
- 총 페이지 수, 페이지 크기 분포, 회전 메타(/Rotate), 방향(portrait/landscape)
- 빈 페이지·이미지 없는 페이지·텍스트 없는 페이지
- DPI 추정(가장 큰 임베디드 이미지 기준)

### 5. 콘텐츠 검사 (`inspect_content.py`)
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pdf-scan-audit/scripts/inspect_content.py "$PDF" > "$WORKDIR/content.json"
```
다음을 수집:
- 회전 의심 페이지(텍스트 줄 종횡비로 추정)
- 이미지가 페이지 경계 밖으로 잘리는 페이지
- 페이지 안에서 이미지 커버리지 비율
- 텍스트 거의 없는 페이지(스캔본인데 OCR 실패 신호)

### 6. 페이지번호 연속성 (`pagenum_check.py`)
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pdf-scan-audit/scripts/pagenum_check.py "$PDF" > "$WORKDIR/pagenum.json"
```
- 헤더/푸터 영역(상하단 10%)에서 숫자만 있는 줄을 페이지번호 후보로 추출
- 동적 추적으로 가장 그럴듯한 시퀀스 선택
- 갭이 큰(>50) 또는 음수인 갭은 **OCR 오인식**으로 자동 분류
- 갭이 1~5 정도면 진짜 누락 후보로 보고

### 7. 의심 페이지 시각 검증 (`extract_pages.py`)
다음 페이지를 PNG로 추출:
- 회전 의심 페이지 전부
- 페이지번호 갭이 진짜 누락 후보(1~5)인 구간 양옆
- 첫 5페이지 + 마지막 3페이지(표지/색인 확인)
- 빈 페이지 의심 전부

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pdf-scan-audit/scripts/extract_pages.py "$PDF" "$WORKDIR" --pages "$PAGES" --mode full
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pdf-scan-audit/scripts/extract_pages.py "$PDF" "$WORKDIR" --pages "$HEADER_PAGES" --mode header
```

`Read` 도구로 PNG를 직접 보고:
- 회전 의심 페이지가 정말 회전됐는지 vs 책 디자인 의도(가로 일러스트)인지 판단
- 헤더 영역에서 실제 페이지번호가 연속되는지 직접 눈으로 확인 → OCR 오인식 vs 진짜 누락 결정

### 8. 결과 보고
`references/output-format.md`의 표 형식대로 마크다운 표로 출력. 다음 섹션 포함:
- 검사 대상 메타데이터
- 핵심 결론(한 문장)
- 일반 메타 검사 결과 표
- 책 구조 매핑(PDF ↔ 책 페이지)
- 의심 페이지 시각 재검증 결과
- 종합 진단표
- 권장 사항

### 9. 정리
```bash
rm -rf "$WORKDIR"
```
- 사용자가 `--keep` 또는 "결과 저장해줘"라고 하면 스킵하고 경로 안내
- 그 외에는 무조건 정리. 작업 디렉토리는 검사 전 상태와 동일하게

## 해석 가이드

OCR 오인식 vs 진짜 누락, 회전 의심 vs 디자인 의도 등 판정 기준은 `references/interpretation.md` 참조.

## 출력 포맷

표 형식 표준은 `references/output-format.md` 참조.
