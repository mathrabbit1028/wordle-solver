import atexit
import datetime
import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from dotenv import load_dotenv
from snowflake.snowpark import Session
from snowflake.cortex import complete

import numpy as np
from scipy.stats import mode

load_dotenv()

class Solver:
    def __init__(self):
        self.session = self._init_snowflake()
        self.model = "claude-3-5-sonnet"
        self.problems = {}
        self.snowflake_calls = 0
        self.log_file = open("run.log", "a")
        atexit.register(self.cleanup)

    def _init_snowflake(self):
        connection_params = {
            "account": os.environ.get("SNOWFLAKE_ACCOUNT"),
            "user": os.environ.get("SNOWFLAKE_USER"),
            "password": os.environ.get("SNOWFLAKE_USER_PASSWORD"),
            "role": os.environ.get("SNOWFLAKE_ROLE"),
            "database": os.environ.get("SNOWFLAKE_DATABASE", ""),
            "schema": os.environ.get("SNOWFLAKE_SCHEMA", ""),
            "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE", ""),
        }
        return Session.builder.configs(connection_params).create()

    def cleanup(self):
        try:
            self.log_file.close()
        except:
            pass
        try:
            self.session.close()
        except:
            pass

    def start_problem(self, problem_id, candidate_words):
        candidate_words = np.array(candidate_words, dtype='<U5')
        self.problems[problem_id] = {
            "candidate_words": candidate_words,
            "plausible_words": candidate_words.copy(),
            "feedback_history": [],
            "translated_feedback": [],
            "guess_history":[]
        }
        self._log(f"\n=== Starting Problem {problem_id} ===")
        self._log(f"Candidate words: {', '.join(candidate_words[:5])}")

    def add_feedback(self, problem_id, verbal_feedback):
        if verbal_feedback:
            last_guess = self.problems[problem_id]["guess_history"][-1]
            self.problems[problem_id]["feedback_history"].append(verbal_feedback)
            self.problems[problem_id]["translated_feedback"].append(self.translate(verbal_feedback, last_guess))

    def translate(self, verbal_feedback, guess):
        # new try, not used. if the verbal feedback can be separated by a specific sign, then divide the verbal feedback            
        num_votes = 3

        prompts = []

        prompts.append(f'''
        You are a precise logic translator for Wordle feedback.

        Your job is to convert the interpretation into a 5-digit numeric code:
        - 2 = correct letter in correct position
        - 1 = correct letter in wrong position
        - 0 = incorrect letter

        Output only the 5-digit code. (e.g. `21001`) 
        Do not include any other texts

        Examples:

        Guess: mesic
        Feedback: the letter 's' appears somewhere else in the target word, while all other letters ('m', 'e', 'i', and 'c') are not present in the target word at all.
        Output: 00100
                                    
        Guess: schwa  
        Feedback: for the guess word "schwa": the first letter 's', second letter 'c', and fourth letter 'w' are not present in the target word at all. the third letter 'h' and the last letter 'a' appear somewhere in the target word, but they are currently in the wrong positions.
        Output: 00101

        Guess: rasps
        Feedback: 
        - the first 'r' is not present in the target word
        - the 'a' is in the correct position
        - the 's' in the middle is not in the target word
        - the 'p' appears in the target word but needs to be in a different position
        - the final 's' is exactly where it should be
        Output: 02012
                    
        Now process the following input:
        ''')      

        prompts.append('''
        You're playing Wordle.
        Convert the verbal feedback into a 5-digit code using the following rules:
        - 0: Letter is not in the word 
        - 1: Letter is in the word but in the wrong position 
        - 2: Letter is in the correct position
        Return only the 5-digit code (e.g., 20100).
        Do not include any explanation or extra text.  
                    
        Examples:
        Guess: liter
        Feedback: 'l' is in the word but in the wrong position. 'i' is in the word but in the wrong position. 't' is not in the word. 'e' is in the word but in the wrong position. 'r' is not in the word.
        Output: 11010
                    
        Guess: mesic
        Feedback: for the guess word "mesic", the letter 's' appears somewhere else in the target word, while all other letters ('m', 'e', 'i', and 'c') are not present in the target word at all.
        Output: 00100

        Guess: rutin          
        Feedback: 'r' is not in the word. 'u' is in the correct position. 't' is in the correct position. 'i' is not in the word. 'n' is in the correct position.
        Output: 02202
        ''')     

        prompts.append(f'''
        Your task is to translate the wordle feedback into five-digits code based on following rules:
        0: the character is not in the word
        1: the character is in the word, but in the wrong position.
        2: the character is in the word and in the correct position.

        Only output the five digits.

        Examples:
        Guess: fails
        Feedback:
        the letter 'f' is not present in the target word at all. the letter 'a' appears in the target word but needs to be in a different position. the letter 'i' is not in the target word. the letter 'l' is perfectly placed in this position. the letter 's' is in the target word but should be moved to a different spot.
        Output: 01021  

        Guess: ombre
        Feedback:
        - the 'o' appears in the word but in a different position
        - the 'm' appears in the word but in a different position
        - the 'b' is not in the word at all
        - the 'r' appears in the word but in a different position
        - the 'e' is correctly placed in this position
        Output: 11012

        Guess: seaze
        Feedback: the first 's' appears somewhere else in the word, the 'e' is in the correct position, 'a' is not in the word at all, 'z' is not in the word at all, and the last 'e' is in the correct position.
        Output: 12002        
        ''')        

        added_prompt = f'''
            Guess: {guess}  
            Feedback: {verbal_feedback}
        '''

        responses = np.zeros((num_votes,5))

        for i in range(num_votes):
            start_time = time.time()
            response = 'notdigit'
            while not response.isdigit():
                response = (
                    complete(
                        model=self.model,
                        prompt=[{"role": "user", "content": prompts[i] + added_prompt}],
                        options={"max_tokens": 20, "temperature": 0.0},
                        session=self.session,
                    )
                    .strip()
                    .lower()
                )
                print(f'{i}th response: {response}')
                
            for j, num in enumerate(list(map(int, response))):
                responses[i][j] = num

            self.snowflake_calls += 1
            self._log(f'response: {response}, time took for LLM: {time.time() - start_time}')

            if i == 1 and np.array_equal(responses[0], responses[1]):
                return list(map(int, responses[0]))
            
        responses = np.round(responses).astype(int)
        final_response = mode(responses, axis=0, keepdims=False).mode
        
        return list(map(int,final_response))

    def choose_next_guess(self, problem_id, turn):

        start_time = time.time()

        candidates = self.problems[problem_id]["candidate_words"]
        plausibles = self.problems[problem_id]["plausible_words"]
        history = self.problems[problem_id]["feedback_history"]
        translated_history = self.problems[problem_id]["translated_feedback"]
        guess_history = self.problems[problem_id]["guess_history"]

        def query_res(word, ans):            
            feedback = np.zeros(5)
            for i in range(5):
                if word[i] == ans[i]:
                    feedback[i] = 2

            remaining = {}
            for i, ch in enumerate(ans):
                if feedback[i] != 2:
                    remaining[ch] = remaining.get(ch, 0) + 1

            for i in range(5):
                if feedback[i] != 2 and remaining.get(word[i], 0) > 0:
                    feedback[i] = 1
                    remaining[word[i]] -= 1

            return feedback
        
        if history:
            last_guess = guess_history[-1]
            last_guess_res = translated_history[-1]
            mask = [(tuple(query_res(word=last_guess, ans=t)) == tuple(last_guess_res)) for t in plausibles]
            mask = np.array(mask, dtype=bool)
            plausibles = plausibles[mask]
            self.problems[problem_id]["plausible_words"] = plausibles


        def query_res_all(ans: str, words: list[str]) -> np.ndarray:
            ans = np.array(list(ans), dtype='<U1')
            words = np.array([list(word) for word in words], dtype='<U1')
            N: int = words.shape[0]

            not_greens = (ans != words) # (N, 5)

            matches = (words[:, :, None] == ans[None, None, :]) # (N, 5, 5)
            '''
            matches[x][i][j]
            x번째 단어의 i번째 문자와 답의 j번째 문자가 같은지 여부
            '''
            t = (matches & not_greens[:, None, :]).sum(axis=2) # (N, 5)
            '''
            def get_t(word: str, ans: str, i: int) -> int:
                cnt: int = 0
                for j in range(5):
                    if ans[j] == word[i] and ans[j] != word[j]:
                        cnt += 1
                return cnt
            '''

            matches = (words[:, :, None] == words[:, None, :]) # (N, 5, 5)
            '''
            matches[x][i][j]
            x번째 단어의 i번째 문자와 x번째 단어의 j번째 문자가 같은지 여부
            '''
            s = np.cumsum(matches & not_greens[:, None, :], axis=2)[np.arange(N)[:, None], np.arange(5), np.arange(5)] # (N, 5)
            '''
            def get_s(word: str, ans: str, i: int) -> int:
                cnt: int = 0
                for j in range(i+1):
                    if word[j] == word[i] and ans[j] != word[j]:
                        cnt += 1
                return cnt
            '''
            
            res = np.full_like(words, fill_value=2, dtype=int) # (N, 5)
            res[not_greens] = (t >= s)[not_greens].astype(int)

            res = (res * np.array([1, 3, 9, 27, 81])).sum(axis=1) # (N,)

            return res

        guess = None

        # for fallback
        if 'probs' not in self.problems[problem_id].keys():
            self.problems[problem_id]["probs"] = 1/len(candidates) * np.ones(len(candidates))
        probs = self.problems[problem_id]["probs"]
        belief = 100
        if history:
            last_guess, last_guess_res = guess_history[-1], translated_history[-1]
            for i, word in enumerate(candidates):
                res = query_res(last_guess, word)
                if np.array_equal(res, last_guess_res):
                    probs[i] *= belief
                if word == last_guess:
                    probs[i] *= 0    
            probs /= probs.sum()
            self.problems[problem_id]["prob"] = probs

        # when find
        if len(plausibles)==1:
            guess = plausibles[0]
        # when fallback
        elif len(plausibles)==0:
            print('FALLBACK ACTIVATED')
            k = 1_000_000 // len(candidates)
            sampled_plausibles = candidates[np.random.choice(len(candidates), size=k, p=probs)]
            sampled_candidates = np.unique(sampled_plausibles.copy())
            res = np.zeros((len(sampled_candidates), len(sampled_plausibles)), dtype=int)
            
            for i, ans in enumerate(sampled_candidates):
                res[i] = query_res_all(ans, sampled_plausibles)
            
            counts = np.zeros((len(sampled_candidates), 273), dtype=int)
            for i in range(len(sampled_candidates)):
                counts[i] = np.bincount(res[i], minlength=273)
            
            probs2 = counts / counts.sum(axis=1, keepdims=True)
            probs_ = probs2.copy()
            probs_[probs2 == 0] = 1
            entropies = -np.sum(probs2 * np.log2(probs_), axis=1)
            guess = sampled_candidates[np.argmax(entropies)]

        elif len(plausibles) * len(candidates) > 1_000_000:
            print('SAMPLED ENTROPY ACTIVATED')
            sample_size = min(1_000_000 // len(plausibles), len(plausibles))
            sampled_candidates = np.random.choice(plausibles, sample_size, replace=False)
            res = np.zeros((len(plausibles), sample_size), dtype=int)
            
            for i, ans in enumerate(plausibles):
                res[i] = query_res_all(ans, sampled_candidates)
            
            counts = np.zeros((len(plausibles), 273), dtype=int)
            for i in range(len(plausibles)):
                counts[i] = np.bincount(res[i], minlength=273)
            
            probs = counts / counts.sum(axis=1, keepdims=True)
            probs_ = probs.copy()
            probs_[probs == 0] = 1
            entropies = -np.sum(probs * np.log2(probs_), axis=1)
            
            guess = plausibles[np.argmax(entropies)]
        
        elif len(plausibles) < 10:
            # todo: brute-force code
            candidates_str = np.array(candidates)
            plausibles_str = np.array(plausibles)

            remaining_candidates = np.setdiff1d(candidates_str, plausibles_str)

            num_needed = min(len(remaining_candidates), 100 - len(plausibles_str))
            extra_selected = np.random.choice(remaining_candidates, num_needed, replace=False)

            small_candidates = list(plausibles_str) + list(extra_selected)

            n = len(plausibles)
            m = len(small_candidates)

            dp = np.ones((1 << n, m, n), dtype=int) * 1000
            _min = np.ones((1 << n, n)) * 1000

            def solve(bit, k):
                if (bit & (1<<k)) == 0:
                    return
                if _min[bit][k] < 1000:
                    return
                if bit == (1 << k):
                    dp[bit, :, k] = 1
                    _min[bit][k] = 1
                    return
                # print(bit, k)
                for i in range(m):
                    _bit = bit
                    for j in range(n):
                        if bit & (1<<j):
                            if np.array_equal(
                                query_res(small_candidates[i], plausibles[k]), 
                                query_res(small_candidates[j], plausibles[k])
                            ):
                                continue
                            _bit -= (1<<j)
                    
                    assert(bit != _bit)

                    solve(_bit, k)
                    dp[bit][i][k] = _min[_bit][k]
                
                    _min[bit][k] = min(_min[bit][k], dp[bit][i][k])
            
            for bit in range(1<<n):
                for k in range(n):
                    solve(bit, k)

            guess = small_candidates[np.argmin(dp.sum(axis=2)[(1<<n)-1])]

        else: 
            res = np.zeros((len(plausibles), len(candidates)), dtype=int)
            for i, ans in enumerate(plausibles):
                res[i] = query_res_all(ans, candidates)

            res = res.T

            counts = np.zeros((len(candidates), 273), dtype=int)
            
            for i in range(len(candidates)):
                counts[i] = np.bincount(res[i], minlength=273)
            
            probs = counts/counts.sum()
            probs_ = probs.copy()
            probs_[probs == 0] = 1
            entropies = -np.sum(probs * np.log2(probs_), axis=1)
            mask = np.array([(i in plausibles) for i in entropies])
            entropies[mask] += (1/len(plausibles))
            guess = candidates[np.argmax(entropies)]
        
        self.problems[problem_id]["guess_history"].append(guess)

        self._log(f"Turn {turn}: Received feedback: {history[-1] if history else 'None'}")
        self._log(f"Translated: {translated_history[-1] if history else 'None'}")
        self._log(f"Turn {turn}: Guess: {guess}")
        self._log(f"time spent for guess: {time.time()-start_time}")
        self._log(f"plausibles: {len(plausibles)}")
        return guess
    
    def _log(self, msg):
        ts = datetime.datetime.now().isoformat()
        self.log_file.write(f"[{ts}] {msg}\n")
        self.log_file.flush()

solver = Solver()

class StudentHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length"))
        data = json.loads(self.rfile.read(length))
        
        if self.path == "/start_problem":
            problem_id = data["problem_id"]
            candidate_words = data["candidate_words"]
            solver.start_problem(problem_id, candidate_words)
            self.send_response(200)
            self.end_headers()
            return

        if self.path == "/guess":
            problem_id = data["problem_id"]
            verbal_feedback = data.get("verbal_feedback")
            turn = data["turn"]
            solver.add_feedback(problem_id, verbal_feedback)
            guess = solver.choose_next_guess(problem_id, turn)

            response = {"guess": guess}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            return

        self.send_response(404)
        self.end_headers()

def run():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), StudentHandler)
    print(f"Student server running on port {port}...")
    server.serve_forever()

if __name__ == "__main__":
    run()