import query
from solver import wordle_solve

def check(str: str) -> None:
    assert(len(str) == 5)
    assert(str.isalpha())
    assert(str.islower())

if __name__ == "__main__":
    words = []
    N = int(input())
    for _ in range(N):
        word = input()
        check(word)
        words.append(word)
    ans = input()
    check(ans)

    query.init(words, ans)
    f = open("src/log.txt", "w")
    f.write("")
    f.close()
    wordle_solve(words)