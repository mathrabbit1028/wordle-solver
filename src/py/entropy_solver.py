import random
import math
from query import query
# importing others in grader.py and query.py is not premitted

def wordle_solve(words) -> None:
    def query_res(word, ans):
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
        return res
    
    def calc_entropy(word):
        li = [tuple(query_res(word=word,ans=j)) for j in sols]
        prob_li = [li.count(i) for i in set(li)]
        return sum([-(x*len(prob_li))*math.log2(x*len(prob_li)) for x in prob_li])

    sols = words.copy()
    while 1:
        ent = {word:calc_entropy(word) for word in sols}
        sols.sort(key=lambda t:ent[t], reverse = True)
        key = sols[0]
        res = query(key)
        sols = list(filter(lambda t: query_res(word=key,ans=t)==res,sols))