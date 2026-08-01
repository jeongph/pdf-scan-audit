#!/usr/bin/env bash
# next-version.sh 테스트 — 나올 수 있는 커밋 조합을 모두 검사한다.
#
# 핵심 불변식: 범프는 "누적"이 아니라 "가장 높은 등급 1회"다.
#   feat 이 5개 쌓여도 0.1.0 -> 0.2.0 이지 0.5.0 이 아니다.
set -uo pipefail

SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/next-version.sh"

pass=0
fail=0

# check <설명> <현재버전> <기대결과> <커밋메시지>...
#   기대결과가 "none" 이면 릴리스하지 않아야 한다.
check() {
  local label="$1" current="$2" want="$3"; shift 3
  local got rc
  got=$(for m in "$@"; do printf '%s\0' "$m"; done | bash "$SCRIPT" "$current")
  rc=$?

  if [ "$want" = "none" ]; then
    if [ "$rc" -eq 10 ] && [ -z "$got" ]; then
      ok "$label"; return
    fi
    nope "$label" "릴리스 없음" "${got:-<빈값>} (exit $rc)"; return
  fi

  if [ "$rc" -eq 0 ] && [ "$got" = "$want" ]; then
    ok "$label"
  else
    nope "$label" "$want" "${got:-<빈값>} (exit $rc)"
  fi
}

# git log --format=%B%x00 의 실제 출력을 그대로 재현한다.
# 각 커밋은 "<메시지>\n\0" 으로 끝나고, 레코드 사이에 개행이 하나 더 들어간다.
# 이 개행 때문에 두 번째 커밋부터 첫 줄이 빈 줄로 읽히는 함정이 있다.
gitlog_input() {
  local first=1 m
  for m in "$@"; do
    if [ "$first" -eq 1 ]; then first=0; else printf '\n'; fi
    printf '%s\n\0' "$m"
  done
}

# check 와 같지만 입력을 git log 형식으로 만든다.
check_gitlog() {
  local label="$1" current="$2" want="$3"; shift 3
  local got rc
  got=$(gitlog_input "$@" | bash "$SCRIPT" "$current")
  rc=$?

  if [ "$want" = "none" ]; then
    if [ "$rc" -eq 10 ] && [ -z "$got" ]; then ok "$label"; else nope "$label" "릴리스 없음" "${got:-<빈값>} (exit $rc)"; fi
    return
  fi
  if [ "$rc" -eq 0 ] && [ "$got" = "$want" ]; then ok "$label"; else nope "$label" "$want" "${got:-<빈값>} (exit $rc)"; fi
}

ok()   { printf '  ok   %s\n' "$1"; pass=$((pass + 1)); }
nope() {
  printf '  FAIL %s\n' "$1"
  printf '       기대: %s\n' "$2"
  printf '       실제: %s\n' "$3"
  fail=$((fail + 1))
}

printf 'next-version.sh — 커밋 조합별 버전 결정\n\n'

printf '[단일 타입]\n'
check "fix 1개 → patch"                    0.5.2 0.5.3 "fix: 정렬 버그 수정"
check "feat 1개 → minor"                   0.5.2 0.6.0 "feat: 새 커맨드 추가"
check "docs 1개 → 릴리스 없음"              0.5.2 none  "docs: README 수정"

printf '\n[같은 타입이 여러 개 — 한 번만 올라야 한다]\n'
check "fix 3개 → patch 1회"                0.5.2 0.5.3 "fix: A" "fix: B" "fix: C"
check "feat 5개 → minor 1회"               0.1.0 0.2.0 "feat: A" "feat: B" "feat: C" "feat: D" "feat: E"
check "feat 10개 → minor 1회"              0.1.0 0.2.0 "feat: 1" "feat: 2" "feat: 3" "feat: 4" "feat: 5" \
                                                        "feat: 6" "feat: 7" "feat: 8" "feat: 9" "feat: 10"
check "docs 4개 → 릴리스 없음"              0.5.2 none  "docs: A" "docs: B" "docs: C" "docs: D"

printf '\n[타입이 섞임 — 가장 높은 등급을 따른다]\n'
check "feat + fix → minor"                 0.5.2 0.6.0 "fix: A" "feat: B"
check "fix + docs → patch"                 0.5.2 0.5.3 "docs: A" "fix: B"
check "feat + docs → minor"                0.5.2 0.6.0 "docs: A" "feat: B"
check "feat 2 + fix 3 → minor 1회"         0.5.2 0.6.0 "feat: A" "fix: B" "fix: C" "feat: D" "fix: E"
check "전부 섞임 → minor 1회"               0.5.2 0.6.0 "docs: A" "fix: B" "chore: C" "feat: D" "ci: E" "test: F"

printf '\n[BREAKING — 0.x 는 minor, 1.x 이상은 major]\n'
check "0.x + feat! → minor"                0.5.2 0.6.0 "feat!: 시그니처 변경"
check "0.x + scope 붙은 feat(a)! → minor"  0.5.2 0.6.0 "feat(api)!: 시그니처 변경"
check "0.x + BREAKING CHANGE 푸터 → minor" 0.5.2 0.6.0 "refactor: 구조 변경

BREAKING CHANGE: 설정 키가 제거됐다"
check "0.x + BREAKING-CHANGE 푸터 → minor" 0.5.2 0.6.0 "refactor: 구조 변경

BREAKING-CHANGE: 설정 키가 제거됐다"
check "1.x + feat! → major"                1.2.3 2.0.0 "feat!: 시그니처 변경"
check "1.x + BREAKING 푸터 → major"        1.2.3 2.0.0 "fix: 수정

BREAKING CHANGE: 응답 포맷이 바뀌었다"
check "2.x + BREAKING → major"             2.6.0 3.0.0 "refactor(core)!: 재설계"
check "BREAKING + feat + fix 다수 → 1회"    1.2.3 2.0.0 "feat: A" "fix: B" "feat!: C" "fix: D" "feat: E"

printf '\n[릴리스 대상이 아닌 타입]\n'
check "chore 만 → 없음"                    0.5.2 none  "chore: 설정 정리"
check "ci 만 → 없음"                       0.5.2 none  "ci: 워크플로우 추가"
check "style 만 → 없음"                    0.5.2 none  "style: 들여쓰기 정리"
check "test 만 → 없음"                     0.5.2 none  "test: 케이스 추가"
check "chore+ci+style+test → 없음"         0.5.2 none  "chore: A" "ci: B" "style: C" "test: D"
check "봇의 릴리스 커밋만 → 없음"           0.5.2 none  "chore(release): 0.5.2"

printf '\n[코드가 바뀌는 타입은 patch]\n'
check "perf → patch"                       0.5.2 0.5.3 "perf: 캐싱으로 속도 개선"
check "refactor → patch"                   0.5.2 0.5.3 "refactor: 함수 분리"
check "revert → patch"                     0.5.2 0.5.3 "revert: \"feat: A\" 되돌리기"
check "build → patch"                      0.5.2 0.5.3 "build: 의존성 갱신"

printf '\n[스코프·형식 변형]\n'
check "scope 붙은 feat → minor"            0.5.2 0.6.0 "feat(okf): 노드 검증 추가"
check "scope 붙은 fix → patch"             0.5.2 0.5.3 "fix(resolve-dir): 경로 판정 수정"
check "대문자 타입 FEAT → 무시"             0.5.2 none  "FEAT: 대문자는 컨벤션 위반"
check "타입 없는 커밋 → 무시"               0.5.2 none  "그냥 작업했음"
check "머지 커밋 → 무시"                    0.5.2 none  "Merge pull request #8 from jeongph/fix/a"
check "머지 커밋 + fix → patch"            0.5.2 0.5.3 "Merge pull request #8 from jeongph/fix/a" "fix: 실제 수정"
check "콜론 뒤 공백 없음 → 무시"            0.5.2 none  "feat:공백없음은 컨벤션 위반"

printf '\n[git log 실제 출력 형식 — 레코드 사이 개행이 끼어든다]\n'
check_gitlog "첫 커밋만 릴리스 대상"          0.5.2 0.5.3 "fix: 첫 커밋" "docs: 둘째"
check_gitlog "둘째 커밋이 릴리스 대상"        0.5.2 0.5.3 "docs: 첫 커밋" "fix: 둘째"
check_gitlog "셋째 커밋이 릴리스 대상"        0.5.2 0.6.0 "docs: A" "chore: B" "feat: C"
check_gitlog "마지막 커밋의 BREAKING 푸터"    1.2.3 2.0.0 "docs: A" "fix: B

BREAKING CHANGE: 포맷 변경"
check_gitlog "본문 여러 줄인 커밋이 섞임"     0.5.2 0.6.0 "chore(release): 0.5.2" "feat: 새 기능

여러 줄
본문이다"
check_gitlog "머지 커밋 뒤의 fix"            0.5.2 0.5.3 "Merge pull request #11 from a/b" "chore(release): 0.5.2" "fix: 실제 수정"
check_gitlog "전부 비대상"                   0.5.2 none  "docs: A" "chore: B" "ci: C"

printf '\n[경계]\n'
check "커밋 없음 → 없음"                   0.5.2 none
check "빈 메시지 → 없음"                   0.5.2 none  ""
check "patch 자리올림 없음"                0.5.9 0.5.10 "fix: A"
check "minor 올리면 patch 는 0"            0.5.9 0.6.0  "feat: A"
check "major 올리면 minor·patch 는 0"      1.4.9 2.0.0  "feat!: A"
check "0.0.x 에서 fix"                     0.0.1 0.0.2  "fix: A"
check "0.0.x 에서 feat"                    0.0.1 0.1.0  "feat: A"

printf '\n통과 %d · 실패 %d\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
