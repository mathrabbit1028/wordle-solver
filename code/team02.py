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
        def splited_by(verbal_feedback, sign):
            return False
            return (verbal_feedback.count(sign) == 5)
        
        for sign in ['.', ',', '\n']:
            if splited_by(verbal_feedback, sign):
                start_time = time.time()
                combined_response = []
                splited_feedbacks = verbal_feedback.split(sign)[:5]
                shared_prompt = f'''
                    You are a precise wordle solver. 
                    Return a single digit 0,1,2 based on which case the verbal feedback falls on.
                    0: the character is not in the word
                    1: the character is in the word but in the wrong position
                    2: the character is in the word in the correct position
                    Return only the single digit. No explanation. No extra text. 
                '''
                for splited_feedback in splited_feedbacks:
                    individual_prompt = f'The feedback is: {splited_feedback}'
                    response = (
                        complete(
                            model=self.model,
                            prompt=[{"role": "user", "content": shared_prompt + individual_prompt}],
                            options={"max_tokens": 20, "temperature": 0.0},
                            session=self.session,
                        )
                        .strip()
                        .lower()
                    )
                    combined_response.append(int(response))
                
                self._log(f'response using splited_feedback: {combined_response}, time took: {time.time() - start_time}')
                return combined_response
            
        num_votes = 2

        prompts = []

        prompts.append(f'''
        You are a precise logic translator for Wordle feedback.

        Task:
        You are given two inputs:
        - A guess word (5 letters)
        - A verbal feedback about the guess

        Your job is to convert the interpretation into a 5-digit numeric code:
        - 2 = correct letter in correct position
        - 1 = correct letter in wrong position
        - 0 = incorrect letter

        Wordle feedback is computed using the following rules:

        Rules:
        - Output only the 5-digit code (e.g. `21001`)
        - No explanation. No extra text.

        Examples:

        Input:  
        Guess: HELLO  
        Feedback: All letters are incorrect.  
        Output: 00000

        Input:  
        Guess: CRANE  
        Feedback: The first and last letters are correct and in the right position. The second letter is correct but in the wrong position. The rest are incorrect.  
        Output: 21002

        Input:  
        Guess: ejido
        Feedback: 'e' is in the word but in the wrong position. 'j' is not in the word. 'i' is in the word but in the wrong position. 'd' is not in the word. 'o' is not in the word.
        Output: 10100

        Input:  
        Guess: acidy
        Feedback: 'a' is in the correct position. 'c' is not in the word. 'i' is in the correct position. 'd' is in the correct position. 'y' is not in the word.
        Output: 20220

        Now process the following input:
        ''')      
        prompts.append(f'''
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
                    
        Guess: sered
        Feedback: 's' is not in the word. 'e' is in the word but in the wrong position. 'r' is in the word but in the wrong position. 'e' is in the word but in the wrong position. 'd' is not in the word.
        Output: 01110

        Guess: rutin          
        Feedback: 'r' is not in the word. 'u' is in the correct position. 't' is in the correct position. 'i' is not in the word. 'n' is in the correct position.
        Output: 01101
        ''')     
        prompts.append(prompts[0])

        responses = np.zeros((num_votes,5))
        for i in range(num_votes):
            start_time = time.time()
            response = (
                complete(
                    model=self.model,
                    prompt=[{"role": "user", "content": prompts[i]}],
                    options={"max_tokens": 20, "temperature": 0.0},
                    session=self.session,
                )
                .strip()
                .lower()
            )
            for j, num in enumerate(list(map(int, response))):
                responses[i][j] = num

            self.snowflake_calls += 1
            self._log(f'response: {response}, time took for LLM: {time.time() - start_time}')

            if i == 1 and response[0] == response[1]:
                return list(map(int, response[0]))
            
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
            # First pass: assign 2 (correct position)
            for i in range(5):
                if word[i] == ans[i]:
                    feedback[i] = 2
                    word[i] = None
                    ans[i] = None

            # Count remaining letters in secret
            remaining = {}
            for ch in ans:
                if ch:
                    remaining[ch] = remaining.get(ch, 0) + 1

            # Second pass: assign 1 (misplaced)
            for i in range(5):
                if word[i] and remaining.get(word[i], 0) > 0:
                    feedback[i] = 1
                    remaining[word[i]] -= 1

            return feedback

            # below is legacy code
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
            li = [tuple(query_res(word=word,ans=j)) for j in plausibles]
            _, counts = np.unique(li, return_counts=True, axis=0)
            probs = counts/counts.sum()
            return -np.sum(probs * np.log2(probs))
        
        if history:
            last_guess = guess_history[-1]
            last_guess_res = translated_history[-1]
            mask = [(tuple(query_res(word=last_guess, ans=t)) == tuple(last_guess_res)) for t in plausibles]
            mask = np.array(mask, dtype=bool)
            plausibles = plausibles[mask]
            self.problems[problem_id]["plausible_words"] = plausibles

        # when damned
        if len(plausibles)==0:
            guess = candidates[np.random.randint(0,len(candidates)-1)]
            self.problems[problem_id]["guess_history"].append(guess)
            self._log(f"Turn {turn}: Received feedback: {history[-1] if history else 'None'}")
            self._log(f"Translated: {translated_history[-1] if history else 'None'}")
            self._log(f"Turn {turn}: We are damned")
            self._log(f"Turn {turn}: Guess: {guess}")
            return guess

        ent = {word:calc_entropy(word) for word in plausibles}
        guess = max(ent, key=ent.get)
        self.problems[problem_id]["guess_history"].append(guess)

        self._log(f"Turn {turn}: Received feedback: {history[-1] if history else 'None'}")
        self._log(f"Translated: {translated_history[-1] if history else 'None'}")
        self._log(f"Turn {turn}: Guess: {guess}")
        self._log(f"time spent for guess: {time.time()-start_time}")
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