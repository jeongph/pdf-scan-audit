# pdf-scan-audit

> 스캔 PDF 품질 정밀 진단 — 페이지 누락·순서·회전·잘림·해상도 결함을 자동 검출하고 표로 보고합니다.

스캐너로 읽은 책이 한 권 들어왔을 때, 메타데이터만 훑지 말고 회전 의심·페이지번호 연속성·이미지 잘림까지 정밀하게 검사하는 Claude Code 플러그인입니다. 612페이지짜리 책도 5분 안에 진단하고, 의심 페이지만 골라 시각 검증한 뒤 가독성 좋은 표로 보고합니다.

## 설치

마켓플레이스 등록(최초 1회):

```
/plugin marketplace add jeongph/claude-plugins
```

플러그인 설치:

```
/plugin install pdf-scan-audit@jeongph-claude-plugins
```

## 사용 예

자연어로 호출:

```
이 PDF 스캔 검사해줘
스캐너로 읽은 책 한 권 점검해줘
PDF 페이지 누락이나 회전 잘못된 거 있나 봐줘
```

슬래시 명령:

```
/audit-pdf book1.pdf
/audit-pdf book1.pdf book2.pdf
```

## 검사 항목

| 항목 | 설명 |
|---|---|
| 페이지 메타 | 페이지 크기 분포·회전 메타·portrait/landscape 방향 |
| 해상도(DPI) | 페이지별 임베디드 이미지 기준 DPI 추정·일관성 |
| 빈 페이지 | 이미지·텍스트 모두 거의 없는 페이지 검출 |
| 회전 의심 | 텍스트 줄 종횡비로 추정. 의심 페이지는 시각 검증 |
| 이미지 커버리지 | 이미지가 페이지 경계 밖으로 잘리거나 큰 여백이 한쪽으로 쏠림 |
| 페이지번호 연속성 | 헤더/푸터에서 추출한 페이지번호 시퀀스의 갭 분석 |
| OCR 오인식 vs 진짜 누락 | 갭 크기로 자동 분류 후 의심 구간만 시각 재검증 |

## 작동 방식

1. **의존성 확인** — `python3 -c "import fitz"` 체크. 없으면 `pip install pymupdf` 안내
2. **임시 디렉토리** — `mktemp -d -t pdf-scan-audit-XXXXXX`. 작업 디렉토리는 손대지 않음
3. **메타 검사** — 612페이지 한 번 순회로 크기·회전·DPI·빈페이지·이미지 통계 수집
4. **콘텐츠 검사** — 텍스트 줄 bbox로 회전 의심, 이미지 bbox로 잘림 검출
5. **페이지번호 분석** — 헤더/푸터 영역(상하단 10%)에서 숫자만 있는 줄 추출. 동적 추적으로 가장 그럴듯한 시퀀스 선택. PDF↔책 페이지 오프셋 자동 추정
6. **의심 페이지 시각 검증** — 회전 의심·페이지번호 갭 양옆을 PNG로 추출해 Claude가 직접 보고 판정
7. **표로 보고** — 검사 대상·핵심 결론·메타 검사·책 구조 매핑·시각 재검증·종합 진단·권장 사항 순
8. **정리** — 임시 디렉토리 자동 삭제. `--keep` 옵션으로 보존 가능

## 적용 대상

- **메인 타겟**: 종이책을 스캐너로 읽은 PDF (Epson ScanSmart, ScanSnap, FineReader 등 출력)
- **부분 적용**: 디지털 PDF — 회전·페이지 크기·페이지번호 연속성은 의미 있음. 빈 페이지·이미지 커버리지 등은 자동 스킵

## 의존성

- Python 3.8+
- [PyMuPDF](https://pymupdf.readthedocs.io/) (`pip install pymupdf`)

## 디렉토리 구조

```
pdf-scan-audit/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── pdf-scan-audit/
│       ├── SKILL.md
│       ├── scripts/
│       │   ├── inspect_meta.py
│       │   ├── inspect_content.py
│       │   ├── pagenum_check.py
│       │   └── extract_pages.py
│       └── references/
│           ├── interpretation.md
│           └── output-format.md
├── commands/
│   └── audit-pdf.md
├── requirements.txt
└── README.md
```

## 라이선스

MIT
