import atexit
import datetime
import json
import os

from http.server import BaseHTTPRequestHandler, HTTPServer

from dotenv import load_dotenv
from snowflake.snowpark import Session
from snowflake.cortex import complete

import math

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
        self.problems[problem_id] = {
            "candidate_words": candidate_words,
            "plausible_words": candidate_words.copy(),
            "feedback_history": [],
            "translated_feedback": [],
            "guess_history":[]
        }
        self._log(f"\n=== Starting Problem {problem_id} ===")
        self._log(f"Candidate words: {', '.join(candidate_words)}")

    def add_feedback(self, problem_id, verbal_feedback):
        if verbal_feedback:
            self.problems[problem_id]["feedback_history"].append(verbal_feedback)
            self.problems[problem_id]["translated_feedback"].append(self.translate(verbal_feedback))

    def translate(self, verbal_feedback):
        # todo: translate
        ''' [example LLM call]
        prompt = "MingeonTV"
        response = (
            complete(
                model=self.model,
                prompt=[{"role": "user", "content": prompt}],
                options={"max_tokens": 10, "temperature": 0.0},
                session=self.session,
            )
            .strip()
            .lower()
        )
        self.snowflake_calls += 1
        '''
        return [0, 0, 0, 0, 0]

    def choose_next_guess(self, problem_id, turn):
        candidates = self.problems[problem_id]["candidate_words"]
        plausibles = self.problems[problem_id]["plausible_words"]
        history = self.problems[problem_id]["feedback_history"]
        translated_history = self.problems[problem_id]["translated_feedback"]
        guess_history = self.problems[problem_id]["guess_history"]

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
            li = [tuple(query_res(word=word,ans=j)) for j in plausibles]
            prob_li = [li.count(i) for i in set(li)]
            return sum([-(x*len(prob_li))*math.log2(x*len(prob_li)) for x in prob_li])
        
        if history:
            last_guess = guess_history[-1]
            last_guess_res = translated_history[-1]
            self.problems[problem_id]["plausible_words"] = list(filter(lambda t: query_res(word=last_guess,ans=t)==last_guess_res,plausibles))

        ent = {word:calc_entropy(word) for word in plausibles}
        plausibles.sort(key=lambda t:ent[t], reverse = True)
        guess = plausibles[0]

        self._log(f"Turn {turn}: Received feedback: {history[-1] if history else "None"}")
        self._log(f"Turn {turn}: Guess: {guess}")
        return guess

        if not history:
            # todo: first guess

            self._log(f"Turn {turn}: Received feedback: None (first turn)")
            self._log(f"Turn {turn}: Guess: {guess}")
            return guess

        # todo: second guess
        '''
        prompt_history = "\n".join([f"Feedback: {fb}" for fb in history])

        prompt = (
            "You're playing Wordle. Based on the following feedback, choose your next guess from the candidate list.\n"
            f"Feedback so far:\n{prompt_history}\n\n"
            f"Candidate words: {', '.join(candidates)}\n"
            "Return only your next guess."
        )

        response = (
            complete(
                model=self.model,
                prompt=[{"role": "user", "content": prompt}],
                options={"max_tokens": 10, "temperature": 0.0},
                session=self.session,
            )
            .strip()
            .lower()
        )

        self.snowflake_calls += 1

        guess = response if response in candidates else candidates[0]
        '''
        last_feedback = history[-1] if history else "None"
        self._log(f"Turn {turn}: Received feedback: {last_feedback}")
        self._log(f"Turn {turn}: Guess: {guess}")
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
