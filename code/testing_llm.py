from dotenv import load_dotenv
from snowflake.snowpark import Session
from snowflake.cortex import complete

import atexit
import os
import numpy as np
import time
from scipy.stats import mode

load_dotenv()

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

def verbalize_feedback(secret, guess, feedback, useLLM = False):
    testLLM = testingLLM()

    if useLLM:
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
        return testLLM.get_response(prompt, max_token=150, temp = 0.7)

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

word_list = open('words.txt').read().strip().split('\n')[:]
len_test = 10
dataset = gain_dataset(word_list, len_test, hard = True)

testLLM = testingLLM()

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

scores = [None for i in range(len(prompts))]

for i in range(len(prompts)):
    testLLM._log(f'testing {i}th prompt')
    scores[i] = testLLM.test(dataset, prompts[i])
    print(f'{i}th score: {scores[i]}')