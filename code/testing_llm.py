from dotenv import load_dotenv
from snowflake.snowpark import Session
from snowflake.cortex import complete

import numpy as np
from scipy.stats import mode


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

word_list = open('words.txt').read().strip().split('\n')[:]

df = []

for i in range(10):
    secret = word_list[np.random.randint(10000)]
    guess = word_list[np.random.randint(10000)]
    raw_feedback = compute_feedback(secret, guess)
    verbalized_feedback = verbalize_feedback(secret, guess, raw_feedback)
    df.append({'secret': secret, 'guess': guess, 'raw_feedback': raw_feedback, 'verbalized_feedback': verbalized_feedback})
    print(f"guess word: {guess}\nverbalized feedback: {verbalized_feedback}\nraw_feedback: {''.join(map(str, raw_feedback))}")