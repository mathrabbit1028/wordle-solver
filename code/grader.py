import requests
from concurrent.futures import ThreadPoolExecutor
import time
import random
import numpy as np

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
        max_candidates = len(word_list) # 최대 후보 단어 개수를 word_list 크기와 5000 중 작은 값으로 제한

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
    parts = []
    for i, f in enumerate(feedback):
        ch = guess[i]
        if f == 2:
            parts.append(f"'{ch}' is in the correct position.")
        elif f == 1:
            parts.append(f"'{ch}' is in the word but in the wrong position.")
        else:
            parts.append(f"'{ch}' is not in the word.")
    return " ".join(parts)


def run_for_team(team_name, base_url):
    print(f"[{team_name}] Starting evaluation")

    for problem_id, problem_data in PROBLEMS.items():
        candidate_words = problem_data["candidate_words"]
        secret = problem_data["secret_word"]

        try:
            print(secret)
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
                r = requests.post(f"{base_url}/guess", json=payload, timeout=9.9)
                r.raise_for_status()
                guess = r.json()["guess"]
            except Exception as e:
                print(f"[{team_name}] Error: {e}")
                break

            guess_count += 1

            # added to avoid infinite loop
            if guess_count > 10:
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