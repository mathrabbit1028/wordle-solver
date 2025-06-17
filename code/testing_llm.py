from dotenv import load_dotenv
from snowflake.snowpark import Session
from snowflake.cortex import complete

import atexit
import os
import numpy as np
import time
from scipy.stats import mode

load_dotenv()


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

def gain_dataset(word_list, len_test, hard = True):
    dataset = []

    if hard:
        for i in range(len_test): 
            data_easy = True
            while(data_easy): 
                secret = word_list[np.random.randint(10000)]
                guess = word_list[np.random.randint(10000)]
                raw_feedback = compute_feedback(secret, guess)
                data_easy = (sum([int(i != 0) for i in raw_feedback]) < 3)
            verbalized_feedback = verbalize_feedback(secret, guess, raw_feedback)
            dataset.append({'secret': secret, 'guess': guess, 'raw_feedback': raw_feedback, 'verbalized_feedback': verbalized_feedback})
            print(f"guess word: {guess}\nverbalized feedback: {verbalized_feedback}\nraw_feedback: {''.join(map(str, raw_feedback))}")
        return dataset
    
    for i in range(len_test):
        secret = word_list[np.random.randint(10000)]
        guess = word_list[np.random.randint(10000)]
        raw_feedback = compute_feedback(secret, guess)
        verbalized_feedback = verbalize_feedback(secret, guess, raw_feedback)
        dataset.append({'secret': secret, 'guess': guess, 'raw_feedback': raw_feedback, 'verbalized_feedback': verbalized_feedback})
        print(f"guess word: {guess}\nverbalized feedback: {verbalized_feedback}\nraw_feedback: {''.join(map(str, raw_feedback))}")
    return dataset

class testingLLM(): 
    def __init__(self):
        self.session = self._init_snowflake()
        self.model = "claude-3-5-sonnet"
        self.problems = {}
        self.snowflake_calls = 0
        self.log_file = open("testing_llm.log", "a")
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

    def get_response(self, prompt):
        response = (
            complete(
                model=self.model,
                prompt=[{"role": "user", "content": prompt}],
                options={"max_tokens": 20, "temperature": 0.0},
                session=self.session,
            )
            .strip()
            .lower()
        )
        return response

    def test(self, dataset, prompt):
        num_correct = 0
        times_computed = []
        for data in dataset:
            start_time = time.time()
            added_input = f'''
                Guess: {data['guess']}  
                Feedback: {data['verbalized_feedback']}
            '''
            response = self.get_response(prompt + added_input)
            response = list(map(int,response))
            time_computed = time.time() - start_time
            times_computed.append(time_computed)
            self._log(f"response: {response}, raw_feedback: {data['raw_feedback']}, time computed: {time_computed}")
            if(response == data['raw_feedback']):
                num_correct += 1
            else:
                self._log(f"the response is wrong.\nverbal feedback: {data['verbalized_feedback']}\n")
        accuracy = num_correct / len(dataset)
        return accuracy

    def _log(self, msg):
        self.log_file.write(f"{msg}\n")
        self.log_file.flush()

word_list = open('words.txt').read().strip().split('\n')[:]
len_test = 10
# dataset = gain_dataset(word_list, len_test)
dataset = [{'secret': 'ambos', 'guess': 'calms', 'raw_feedback': [0, 1, 0, 1, 2], 'verbalized_feedback': "'c' is not in the word. 'a' is in the word but in the wrong position. 'l' is not in the word. 'm' is in the word but in the wrong position. 's' is in the correct position."}, {'secret': 'capex', 'guess': 'adept', 'raw_feedback': [1, 0, 1, 1, 0], 'verbalized_feedback': "'a' is in the word but in the wrong position. 'd' is not in the word. 'e' is in the word but in the wrong position. 'p' is in the word but in the wrong position. 't' is not in the word."}, {'secret': 'carle', 'guess': 'creep', 'raw_feedback': [2, 1, 1, 0, 0], 'verbalized_feedback': "'c' is in the correct position. 'r' is in the word but in the wrong position. 'e' is in the word but in the wrong position. 'e' is not in the word. 'p' is not in the word."}, {'secret': 'eying', 'guess': 'jiggy', 'raw_feedback': [0, 1, 1, 0, 1], 'verbalized_feedback': "'j' is not in the word. 'i' is in the word but in the wrong position. 'g' is in the word but in the wrong position. 'g' is not in the word. 'y' is in the word but in the wrong position."}, {'secret': 'flews', 'guess': 'leats', 'raw_feedback': [1, 1, 0, 0, 2], 'verbalized_feedback': "'l' is in the word but in the wrong position. 'e' is in the word but in the wrong position. 'a' is not in the word. 't' is not in the word. 's' is in the correct position."}, {'secret': 'ruana', 'guess': 'aruhe', 'raw_feedback': [1, 1, 1, 0, 0], 'verbalized_feedback': "'a' is in the word but in the wrong position. 'r' is in the word but in the wrong position. 'u' is in the word but in the wrong position. 'h' is not in the word. 'e' is not in the word."}, {'secret': 'astun', 'guess': 'savin', 'raw_feedback': [1, 1, 0, 0, 2], 'verbalized_feedback': "'s' is in the word but in the wrong position. 'a' is in the word but in the wrong position. 'v' is not in the word. 'i' is not in the word. 'n' is in the correct position."}, {'secret': 'greve', 'guess': 'sered', 'raw_feedback': [0, 1, 1, 1, 0], 'verbalized_feedback': "'s' is not in the word. 'e' is in the word but in the wrong position. 'r' is in the word but in the wrong position. 'e' is in the word but in the wrong position. 'd' is not in the word."}, {'secret': 'ileum', 'guess': 'liter', 'raw_feedback': [1, 1, 0, 1, 0], 'verbalized_feedback': "'l' is in the word but in the wrong position. 'i' is in the word but in the wrong position. 't' is not in the word. 'e' is in the word but in the wrong position. 'r' is not in the word."}, {'secret': 'ryked', 'guess': 'icker', 'raw_feedback': [0, 0, 2, 2, 1], 'verbalized_feedback': "'i' is not in the word. 'c' is not in the word. 'k' is in the correct position. 'e' is in the correct position. 'r' is in the word but in the wrong position."}]

testLLM = testingLLM()

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
               
Guess: sered
Feedback: 's' is not in the word. 'e' is in the word but in the wrong position. 'r' is in the word but in the wrong position. 'e' is in the word but in the wrong position. 'd' is not in the word.
Output: 01110

Guess: rutin          
Feedback: 'r' is not in the word. 'u' is in the correct position. 't' is in the correct position. 'i' is not in the word. 'n' is in the correct position.
Output: 01101
''')     

scores = [None for i in range(len(prompts))]

for i in range(len(prompts)):
    testLLM._log(f'testing {i}th prompt')
    scores[i] = testLLM.test(dataset, prompts[i])
    print(f'{i}th score: {scores[i]}')