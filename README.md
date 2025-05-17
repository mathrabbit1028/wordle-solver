# wordle-solver

_last update: 5/17_

1. Problem Statement (5/16)
2. Implement The Grader (5/16 ~ 5/19)
3. Related Works (5/16 ~ 5/19)
4. Devise Algorhtms + Write Docs: "Theorical Approach" (5/19 ~ 5/25)
5. Implement + Write Docs: "Implemenatation Details" (5/26 ~ 6/1)
6. PPT Prepare + Final Docs Writing (6/2 ~ 6/4)

## Problem Statement
[워들](https://www.nytimes.com/games/wordle/index.html)을 최대한 적은 질의로 해결하는 프로그램을 작성하라.

### 함수 목록 및 정의
여러분은 다음 함수 `wordle_solve`를 구현해야 한다.
```
wordle_solve(words: list[str]) -> None
```
- `words`: 문자열들이 담긴 리스트
  - 이 리스트에 담긴 모든 문자열은 알파벳 소문자들로만 구성된 길이 5의 문자열이다.
- 이 함수는 최대한 적은 질의로 정답 문자열 `ans`를 알아내야 한다.
- 정답 문자열 `ans`는 `words`에 존재함이 보장된다.
- 이 함수는 `query` 함수를 원하는 만큼 호출할 수 있다.
- `query` 함수의 인자로 정답 문자열을 넣을 때까지 `query` 함수를 호출한 횟수가 질의 횟수가 된다.
- 이 함수는 **정확히 한 번** 호출된다.

다음은 여러분의 프로그램에서 호출할 수 있는 그레이더의 함수들이다.
```
query(word: str) -> list[int]?
```
- `word`: 길이 5의 문자열
- `word`는 `words`에 속하는 문자열이어야 한다.
  - 그렇지 않은 경우 `[-1, -1, -1, -1, -1]`을 반환한다.
- 이 함수는 숨겨진 정답 문자열 `ans`와 비교하여 길이 5의 리스트 $[a_0, a_1, a_2, a_3, a_4]를 반환한다.
- 리스트의 각 원소 $a_i ~ (0 \leq < 5)$는 0, 1, 2 중 하나이다.
  - `word[i]`와 `ans[i]`가 같은 문자면 $a_i = 2$이다.
  - `word[i]`와 `ans[i]`가 다른 문자이면
    - `ans[j]`와 `word[i]`가 같으면서 `ans[j]`와 `word[j]`가 다른 $0 \leq j < 5$의 개수를 $t$라 하자.
    - `word[j]`와 `word[i]`가 같으면서, `ans[j]`와 `word[j]`가 다른 $0 \leq j \leq i$의 개수를 $s$라 하자.
    - $t \geq s$이면 $a_i = 1$이고, 아니면 $a_i = 0$이다.
- `word`가 `ans`와 같으면 프로그램이 종료된다.

**제출하는 코드의 어느 부분에서도 입출력 함수를 실행해서는 안 된다.**

### 예제

문자열 리스트가 `["apple", "offer", "fifth"]`이고, 숨겨진 문자열이 `"fifth"`라고 하자. 그러면 그레이더는 여러분의 프로그램의 다음 함수를 호출한다.
```
wordle_solve(["apple", "offer", "fifth"])
```
첫 번째로, 프로그램이 `query("apple")`을 호출하면 `query` 함수는 `[0, 0, 0, 0, 0]`을 반환한다.

이어서, 프로그램이 `query("offer")`을 호출하면 `query` 함수는 `[0, 1, 2, 0, 0]`을 반환한다.

다음에, 프로그램이 `query("fifth")`을 호출하면 `query` 함수는 그 어떤 값도 반환하지 않고, 마지막 호출을 포함해서 현재까지 사용된 쿼리의 수를 출력한다. 이후 모든 실행을 종료한다.

### 노트

다음은 `query` 함수의 구현의 이해에 도움이 될 몇 가지 예제이다:
- 정답 문자열이 `"bbbff"`일 때, `query("fafaf")`의 반환값은 `[1, 0, 0, 0, 2]`이다. 
  - $a_0$의 경우, `"bbbff"`에서 일치하지 않은 `'f'` 문자의 개수가 하나이고($t=1$), `"fafaf"`에서 인덱스 0(0-based)의 `f`는 첫 번째 일치하지 않은 `'f'` 문자이므로($s=1$) $a_0 = 1$이다.
  - $a_2$의 경우, `"bbbff"`에서 일치하지 않은 `'f'` 문자의 개수가 하나인데($t=1$), `"fafaf"`에서 인덱스 2(0-based)의 `f`는 두 번째 일치하지 않은 `'f'` 문자이므로($s=2$) $a_2 = 0$이다.
- 정답 문자열이 `"fffbb"`일 때, `query("afafa")`의 반환값은 `[0, 2, 0, 1, 0]`이다.

### 샘플 그레이더

샘플 그레이더는 아래와 같은 형식으로 입력을 받는다.
- Line 1: $N$
- Line $i+1$: `words`의 $i$번째 문자열 $(1 \leq i \leq N)$
- Line $N+2$: 정답 문자열 `ans`

샘플 그레이더는 프로그램이 종료되기 직전에, 현재까지 `query` 함수가 호출된 횟수 $M$을 아래와 같은 형식으로 반환한다.
- Line 1: OK, $M$ queries

**샘플 그레이더는 실제 채점에서 사용하는 그레이더와 다를 수 있음에 유의하라.**

## Implement The Grader
_recommended deadline: 5/19_

샘플 그레이더 구현이 완료되었습니다. 총 네 개의 파일로 구성되어 있습니다.
- `src/py/grader.py`: 채점기가 실행하는 파일. 입력 및 입력 데이터 유효성 검사가 포함되어 있음.
- `src/py/query.py`: 호출할 `query` 함수가 정의된 파일.
- `src/py/solver.py`: 구현할 `wordle_solver` 함수가 정의된 파일.
- `src/log.txt`: `query` 함수의 호출을 기록하는 로그 파일.

**여러분은 `src/py/solver.py`만 수정하여야 합니다.**

### 실행 방법
수정은 `src/py/solver.py`만 하지만, 실행은 `src/py/grader.py`를 실행해야 합니다. vs code에서 `wordle-solver` 폴더를 열고 `src/py/grader.py`를 run 하거나, `wordle-solver` 폴더에서 커맨드 명령어
```
python src/py/grader.py
```
를 실행하십시오.

### 구현 유의사항
`solver.py`에도 적혀 있는 내용입니다. 다음 코드는 작성하지 말아야 합니다:
- `grader.py` 또는 `query.py`에서 `query` 함수를 제외한 변수 혹은 함수를 호출하는 코드
- `wordle_solve` 함수의 값 반환
- `input`, `print` 함수 등의 입출력 함수
  
### 로그 파일
정답을 맞추기 직전 호출까지 `"answer: {} / query: {} / result: {}"`의 꼴로 호출의 결과가 `log.txt`에 기록됩니다. 디버깅 용도입니다.

### 예제


## Related Works
_recommended deadline: 5/19_
- Greenberg, Ronald I. "Effective Wordle Heuristics." arXiv preprint arXiv:2408.11730 (2024). (구윤우)
- Mishra, Neelesh. "Using Information Theory to Play Wordle as Optimally as Possible." (2024). (김성훈)
- Bertsimas, Dimitris, and Alex Paskov. "An exact and interpretable solution to wordle." (2022). (정민건)

## Devise Algorhtms + Write Docs: "Theorical Approach"
_recommended deadline: 5/25_

## Implement + Write Docs: "Implemenatation Details"
_recommended deadline: 6/1_

## PPT Prepare + Final Docs Writing
_recommended deadline: 6/4_
