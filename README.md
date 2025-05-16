# wordle-solver

1. Problem Statement (5/16)
2. Implement The Grader (5/16 ~ 5/19)
3. Related Works (5/16 ~ 5/19)
4. Devise Algorhtms + Write Docs: "Theorical Approach" (5/19 ~ 5/25)
5. Implement + Write Docs: "Implemenatation Details" (5/26 ~ 6/1)
6. PPT Prepare + Final Docs Writing (6/2 ~ 6/4)

## Problem Statement
[워들](https://www.nytimes.com/games/wordle/index.html)을 최대한 적은 질의로 해결하는 프로그램을 작성하라.

### 함수 목록 및 정의
```
wordle_solve(words: list[str]) -> void
```
- `words`: 길이 5의 문자열들이 담긴 리스트
- 이 함수는 최대한 적은 질의로 정답 문자열 `ans`를 알아내야 한다.
- 정답 문자열 `ans`는 `words`에 존재함이 보장된다.
- 이 함수는 `query` 함수를 원하는 만큼 호출할 수 있다.
- `query` 함수의 인자로 정답 문자열을 넣을 때까지 `query` 함수를 호출한 횟수가 질의 횟수가 된다.
- 이 함수는 **정확히 한 번** 호출된다.

```
query(word: str) -> list[int]?
```
- `word`: 길이 5의 문자열
- `word`는 `words`에 속하는 문자열이어야 한다.
  - 그렇지 않은 경우 `[-1, -1, -1, -1, -1]`을 반환한다.
- 이 함수는 숨겨진 정답 문자열 `ans`와 비교하여 길이 5의 리스트를 반환한다.
- 리스트의 각 원소 $a_i$는 0, 1, 2 중 하나이다.
  - $a_i = 0$은 `word[i] = ans[j]`인 $1 \leq j \leq 5$가 존재하지 않는다는 뜻이다.
  - $a_i = 1$은 `word[i] = ans[j]`, $i \neq j$이고 $a_j \neq 2$인 $1 \leq j \leq 5$가 존재한다는 뜻이다.
  - $a_i = 2$은 `word[i] = ans[i]`라는 뜻이다.
- `word`가 `ans`와 같으면 프로그램이 종료된다.

**제출하는 코드의 어느 부분에서도 입출력 함수를 실행해서는 안 된다.**

### 예제

문자열 리스트가 `["apple", "offer", "fifth"]`이고, 숨겨진 문자열이 `"fifth"`라고 하자. 그러면 그레이더는 다음과 같이 함수를 호출한다.
```
wordle_solve(["apple", "offer", "fifth"])
```
프로그램이 `query("apple")`을 호출하면 상술된 규칙에 따라 `[0, 0, 0, 0, 0]`을 반환한다.
프로그램이 `query("offer")`을 호출하면 상술된 규칙에 따라 `[0, 1, 2, 0, 0]`을 반환한다.
프로그램이 `query("fifth")`을 호출하면 상술된 규칙에 따라 프로그램이 종료된다.

### 샘플 그레이더

샘플 그레이더는 아래와 같은 형식으로 입력을 받는다.
- Line 1: $N$
- Line $1+i$: 길이 5의 $i$번째 문자열 $(1 \leq i \leq N)$

샘플 그레이더는 프로그램이 종료되는 순간 `query` 함수가 호출된 횟수 $M$을 아래와 같은 형식으로 반환한다.
- Line 1: OK, $M$ queries

**샘플 그레이더는 실제 채점에서 사용하는 그레이더와 다를 수 있음에 유의하라.**

## Implement The Grader
recommended deadline: 5/19

## Related Works
recommended deadline: 5/19
- Greenberg, Ronald I. "Effective Wordle Heuristics." arXiv preprint arXiv:2408.11730 (2024).
- Mishra, Neelesh. "Using Information Theory to Play Wordle as Optimally as Possible." (2024).
- Bertsimas, Dimitris, and Alex Paskov. "An exact and interpretable solution to wordle." (2022).

## Devise Algorhtms + Write Docs: "Theorical Approach"
recommended deadline: 5/25

## Implement + Write Docs: "Implemenatation Details"
recommended deadline: 5/26

## PPT Prepare + Final Docs Writing
recommended deadline: 6/4
