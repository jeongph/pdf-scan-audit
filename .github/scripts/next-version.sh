#!/usr/bin/env bash
# 커밋 메시지들을 읽어 다음 버전을 계산한다.
#
#   사용법: next-version.sh <현재버전>  < (NUL 로 구분된 커밋 메시지들)
#   출력  : 다음 버전 문자열
#   종료  : 0 = 릴리스 대상 있음 / 10 = 없음 / 1 = 입력 오류
#
# 규칙은 docs/conventions/git-commit-convention.md 의 SemVer 표를 따른다.
#
#   BREAKING (제목의 ! 또는 BREAKING CHANGE 푸터)
#       major 가 0 이면 minor  — 0.x 는 초기 개발 구간이라 호환성을 보장하지 않는다
#                                (SemVer 4항, 실제 이력도 0.4.0 -> 0.5.0 으로 처리했다)
#       major 가 1 이상이면 major
#   feat                        minor
#   fix perf refactor revert build   patch
#       (컨벤션 표에서 perf 등은 '-' 지만, 코드가 실제로 바뀌는 타입을 빼면
#        그 변경이 기존 사용자에게 영영 전달되지 않는다)
#   docs style test ci chore    릴리스하지 않음
#
# 범프는 누적이 아니라 "가장 높은 등급 한 번"이다.
# feat 이 10개 쌓여도 0.1.0 -> 0.2.0 이지 0.11.0 이 아니다.
set -uo pipefail

CURRENT="${1:-}"

if ! printf '%s' "$CURRENT" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "현재 버전이 semver 가 아니다: ${CURRENT:-<빈값>}" >&2
  exit 1
fi

# 0 = 없음, 1 = patch, 2 = minor, 3 = breaking
level=0
bump_to() { [ "$1" -gt "$level" ] && level="$1"; return 0; }

title_re='^([a-z]+)(\([^)]*\))?(!)?:[[:space:]]+.'
breaking_re='(^|'$'\n'')BREAKING[ -]CHANGE:'

while IFS= read -r -d '' msg; do
  # git log --format=%B%x00 은 레코드 사이에 개행을 하나 더 끼워 넣는다.
  # 걷어내지 않으면 두 번째 커밋부터 첫 줄이 빈 줄로 읽혀 타입을 놓친다.
  while [ "${msg#$'\n'}" != "$msg" ]; do msg="${msg#$'\n'}"; done

  [ -z "$msg" ] && continue

  # 푸터의 BREAKING CHANGE 는 타입과 무관하게 최우선이다.
  if [[ "$msg" =~ $breaking_re ]]; then
    bump_to 3
    continue
  fi

  # 제목 줄만 떼어 타입을 본다.
  head_line="${msg%%$'\n'*}"
  [[ "$head_line" =~ $title_re ]] || continue

  type="${BASH_REMATCH[1]}"
  bang="${BASH_REMATCH[3]}"

  if [ -n "$bang" ]; then
    bump_to 3
    continue
  fi

  case "$type" in
    feat)                                bump_to 2 ;;
    fix|perf|refactor|revert|build)      bump_to 1 ;;
    *)                                   : ;;
  esac
done

[ "$level" -eq 0 ] && exit 10

major="${CURRENT%%.*}"
rest="${CURRENT#*.}"
minor="${rest%%.*}"
patch="${rest#*.}"

# 0.x 에서의 breaking 은 minor 로 낮춘다.
if [ "$level" -eq 3 ] && [ "$major" -eq 0 ]; then
  level=2
fi

case "$level" in
  3) major=$((major + 1)); minor=0; patch=0 ;;
  2) minor=$((minor + 1)); patch=0 ;;
  1) patch=$((patch + 1)) ;;
esac

printf '%s.%s.%s' "$major" "$minor" "$patch"
