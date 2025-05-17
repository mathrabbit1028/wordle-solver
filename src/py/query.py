words: list[str] = []
N: int = 0
M: int = 0
ans: str = ""

def init(_words: list[str], _ans: str) -> None:
    global words, ans
    words = _words
    ans = _ans

def query(word: str) -> list[int]:
    global M
    M += 1

    if word not in words:
        return [-1, -1, -1, -1, -1]

    if word == ans:
        print(f"OK, {M} queries")
        exit(0)

    def get_t(word: str, ans: str, i: int) -> int:
        cnt: int = 0
        for j in range(5):
            if ans[j] == word[i] and ans[j] != word[j]:
                cnt += 1
        return cnt
    
    def get_s(word: str, ans: str, i: int) -> int:
        cnt: int = 0
        for j in range(i+1):
            if word[j] == word[i] and ans[j] != word[j]:
                cnt += 1
        return cnt
    
    res = [2, 2, 2, 2, 2]
    for i, c in enumerate(word):
        if ans[i] != c:
            t = get_t(word, ans, i)
            s = get_s(word, ans, i)
            res[i] = int(t >= s)

    assert(res != [2, 2, 2, 2, 2])
    
    f = open("src/log.txt", "a")
    f.write(f"answer: {ans} / query: {word} / result: {res}\n")
    f.close()

    return res