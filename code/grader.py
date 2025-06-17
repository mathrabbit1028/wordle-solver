import requests
from concurrent.futures import ThreadPoolExecutor
import time
import random
import numpy as np

from dotenv import load_dotenv
from snowflake.snowpark import Session
from snowflake.cortex import complete
import atexit
import os


load_dotenv()

class RunLLM:
    def __init__(self):
        self.session = self._init_snowflake()
        self.model = "claude-3-5-sonnet"
        self.problems = {}
        self.snowflake_calls = 0
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
            self.session.close()
        except:
            pass

    def get_response(self, prompt, max_token = 20, temp = 0.0):
        response = (
            complete(
                model=self.model,
                prompt=[{"role": "user", "content": prompt}],
                options={"max_tokens": max_token, "temperature": temp},
                session=self.session,
            )
            .strip()
            .lower()
        )
        return response

runLLM = RunLLM()

STUDENTS = {
    "team02": "http://localhost:8000",
}

word_list = open('./words.txt').read().strip().split('\n')

np.random.seed(1234567890)

PROBLEMS = {
    "A": {"secret_word": "flame", "candidate_words": ["crane", "flame", "slate"]},
    "B": {"secret_word": "altar", "candidate_words": ["prank", "altar", "adapt"]},
}

def make_problems(num_test_sets = 100):
    global PROBLEMS
    for i in range(num_test_sets):
        test_id = str(i + 1)

        secret_word = random.choice(word_list)

        min_candidates = 10 # 최소 후보 단어 개수
        max_candidates = 3000

        num_candidates = random.randint(min_candidates, max_candidates)

        candidate_words_set = set()
        candidate_words_set.add(secret_word)

        while len(candidate_words_set) < num_candidates:
            candidate_words_set.add(random.choice(word_list))

        candidate_words = list(candidate_words_set)
        random.shuffle(candidate_words)

        PROBLEMS[test_id] = {
            "secret_word": secret_word,
            "candidate_words": candidate_words
        }


def compute_feedback(secret, guess):
    feedback = [0] * 5  # Default: 0
    secret_chars = list(secret)
    guess_chars = list(guess)

    # First pass: assign 2 (correct position)
    for i in range(5):
        if guess_chars[i] == secret_chars[i]:
            feedback[i] = 2
            secret_chars[i] = None
            guess_chars[i] = None

    # Count remaining letters in secret
    remaining = {}
    for ch in secret_chars:
        if ch:
            remaining[ch] = remaining.get(ch, 0) + 1

    # Second pass: assign 1 (misplaced)
    for i in range(5):
        if guess_chars[i] and remaining.get(guess_chars[i], 0) > 0:
            feedback[i] = 1
            remaining[guess_chars[i]] -= 1

    return feedback


def verbalize_feedback(secret, guess, feedback):
    prompt = f'''
        You need to describe the result of the wordle with words only; don't explicitly stating the number value.
        These are the description for the numerical feedback corresponding to the guess word:
        0: the character is not in the word
        1: the character is in the word but in the wrong position.
        2: the character is in the word and in the correct position.

        This the the guess word and the following feedback: 
        guess word: {guess}
        feedback: {feedback}

    '''
    verbalized_feedback =  runLLM.get_response(prompt, max_token=150, temp = 0.7)
    return verbalized_feedback


def run_for_team(team_name, base_url):
    print(f"[{team_name}] Starting evaluation")

    for problem_id, problem_data in PROBLEMS.items():
        candidate_words = problem_data["candidate_words"]
        secret = problem_data["secret_word"]

        try:
            print(f'secret: {secret}')
            requests.post(
                f"{base_url}/start_problem",
                json={"problem_id": problem_id, "candidate_words": candidate_words},
                timeout=10,
            )
        except Exception as e:
            print(f"[{team_name}] Failed to send start_problem: {e}")
            continue

        guess_count = 0
        feedback = None
    
        while True:
            try:
                payload = {
                    "problem_id": problem_id,
                    "verbal_feedback": feedback,
                    "turn": guess_count + 1,
                }
                r = requests.post(f"{base_url}/guess", json=payload, timeout=20)
                r.raise_for_status()
                guess = r.json()["guess"]
            except Exception as e:
                print(f"[{team_name}] Error: {e}")
                break

            guess_count += 1

            # added to avoid infinite loop
            if guess_count > 20:
                print(f"[{team_name}] Guess number exceeded 10")
                break
            if guess == secret:
                print(f"[{team_name}] Solved {problem_id} in {guess_count} guesses.")
                break

            raw_feedback = compute_feedback(secret, guess)
            feedback = verbalize_feedback(secret, guess, raw_feedback)

    print(f"[{team_name}] Finished.")


def main():
    with ThreadPoolExecutor(max_workers=4) as executor:
        for team, url in STUDENTS.items():
            executor.submit(run_for_team, team, url)


if __name__ == "__main__":
    make_problems()
    main()