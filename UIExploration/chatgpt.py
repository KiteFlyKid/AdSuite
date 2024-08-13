import openai
import json
from copy import deepcopy

from typing import List, Set, Dict
from pathlib import Path
import time
import re

from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type
)  # for exponential backoff

import os
@retry(
    retry=retry_if_exception_type((openai.error.APIError, openai.error.APIConnectionError, openai.error.RateLimitError, openai.error.ServiceUnavailableError, openai.error.Timeout)),
    wait=wait_random_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(10)
)
def chat_completion_with_backoff(**kwargs):
    os.environ['http_proxy'] = "http://127.0.0.1:7890"
    os.environ['https_proxy'] = "http://127.0.0.1:7890"
    response =openai.ChatCompletion.create(**kwargs)
    del os.environ['http_proxy']
    del os.environ['https_proxy']
    return response


openai.api_key_path = Path('./api.key').absolute()
model=vision_model = 'gpt-3.5-turbo'
model=vision_model='gpt-4o-mini'
# model = 'gpt-4'
expensive_model = 'gpt-4'
temp = 0.2
#proxy = 'http://127.0.0.1:7980'
system_message: str

history = []
sessions: List["Session"] = []

def getTotalTokensUsed() -> int:
    return sum([session.tokens_used["completion"] + session.tokens_used["prompt"] for session in sessions])

def setupChatGPT(prompt) -> None:
    global system_message
    system_message = prompt

class Session:
    history: List[tuple]
    tokens_used: Dict[str, int]

    def __init__(self, init_history: List[tuple] = None):
        if init_history is None:
            self.history = [('system', system_message)]
        else:
            self.history = deepcopy(init_history)
        self.tokens_used = {"completion": 0, "prompt": 0}
        sessions.append(self)

    def dump(self, path: Path):
        with open(path, 'w') as f:
            json.dump(self.__dict__, f)

    def __iter__(self):
        return iter(self.history)

    def __getitem__(self, item):
        return self.history[item]

    def transformMessage(self, messages):
        return [{'role': t, 'content': m} for (t, m) in messages]

    def updateTokensUsed(self, usage: Dict[str, int]):
        self.tokens_used['completion'] += usage['completion_tokens']
        self.tokens_used['prompt'] += usage['prompt_tokens']

    def __call__(self, message):
        #print(self.history)
        self.history.append(('user', message))
        print(message)
        resp = chat_completion_with_backoff(
            model=model,
            messages=self.transformMessage(self.history),
            temperature=temp)
        self.updateTokensUsed(resp["usage"])
        response = resp['choices'][0]['message']['content']
        print("="*20)
        self.history.append(('assistant', response))
        print(response)
        return response

    def findFirstInteger(self, s: str):
        if re.search(r'\d+', s) is None:
            return None
        return int(re.search(r'\d+', s).group())
    def queryIndex_noback(self, prompt="", limit=lambda x: True) -> int:
        prompt += "Please choose only one UI element with its index such that the element can make us closer to our test target."
        response = self(prompt)
        print('In queryIndex: ',response)
        for m in re.finditer('index-', response):
            local = response[m.start():m.start()+12]
            if 'index-none' not in local and limit(self.findFirstInteger(local[5:])):
                return self.findFirstInteger(local[5:])
        return -1
    def queryIndex(self, prompt="", limit=lambda x: True) -> int:
        prompt += "Please choose only one UI element with its index such that the element can make us closer to our test target."\
                  + "\nIf none of the UI element can do so, respond with index-none."
        response = self(prompt)
        print('In queryIndex: ',response)
        for m in re.finditer('index-', response):
            local = response[m.start():m.start()+12]
            if 'index-none' not in local and limit(self.findFirstInteger(local[5:])):
                return self.findFirstInteger(local[5:])
        return -1
        #if 'index-none' in response:
        #    return -1
        #raise NotImplementedError("How to deal with the situation where chatgpt cannot give any index?")

    def queryOpinion(self, prompt="") -> bool:
        prompt += "Please response in YES or NO, one word only."
        response = self(prompt)
        return "YES" in response or ('NO' not in response and 'yes' in response)

    def queryListOfIndex(self, prompt="", guard = lambda x: True) -> Set[int]:
        prompt += "Please select a list of indexes for the texts that you think are very very relevant to the goal.\n" + \
                  "Please return in the form [0,1,2] or return nothing is none of the texts are relevant." \
                  "Remember, only select the ones that are relevant. It is ok to select nothing."
        response = self(prompt)
        try:
            strList:str = response[response.index('['): response.index(']')+1]
            return set(filter(guard, map(lambda x: int(strList.strip()), strList.split(','))))
        except:
            print("No list is find in the response. Fall back to using regex and grab all the numbers.")
            return set(filter(guard, [int(number.strip()) for number in re.findall(r"\d+", response)]))

    def queryString(self, prompt="") -> str:
        prompt += " Please only respond with the text input and nothing else."
        response = self(prompt)

        def extract_str(res: str):
            if sum([ch == '"' for ch in response]) >= 2:
                res = res.split('"')[1]
            elif sum([ch == "'" for ch in response]) >= 2:
                res = res.split("'")[1]
            return res

        return extract_str(response)

    def clear_last(self):
        self.history = self.history[:-2]

    def record_history(self):
        Path('chatgpt_android/history').mkdir(exist_ok=True)
        cur_time = time()
        with open(f'chatgpt_android/history/history-{cur_time}.json', 'w') as f:
            json.dump(self.full_history, f)
        print(f'History saved to history-{cur_time}')

    def parse_test_steps(self,response):
        test_steps = json.loads(response)
        print(test_steps)
        return test_steps
    def spawn_tests(self,target,app,spawn_num = 1):
        system_prompt = f"Suppose You are an Android UI testing expert and helping write a UI test. Our test objective is to {target} on the {app} app. Give me one sequence of test steps to achieve the test objective.\n"
        instr_prompt = f"Response with only the test steps in the json format with key being the order of steps and value being the test step description. Each test step should be some phrases instead of whole sentences."
        messages = [('system',system_prompt),('user',instr_prompt)]
        resp = chat_completion_with_backoff(
            model=model,
            messages=self.transformMessage(messages),
            temperature=temp,
            n=spawn_num)
        self.updateTokensUsed(resp["usage"])
        responses = [resp['choices'][i]['message']['content'] for i in range(len(resp['choices']))]
        return [self.parse_test_steps(response) for response in responses]
    def grounding_multi(self,target,app,test_steps,ui_description):
        system_prompt = f"Suppose You are an Android UI testing expert and helping map test steps to UI element on the screen.\n"
        ui_prompt = ui_description
        test_step_prompt = f"Current we have {len(test_steps)} candidate test steps to map, namely:\n"
        for test_step in test_steps:
            pass
        instr_prompt = f"Response with only the mapping from test step to UI element index in the json format with key being the test step and value being only the index of UI element."
    def grounding_single(self,target,app,test_step,ui_description):
        system_prompt = f"Suppose You are an Android UI testing expert and helping ground UI element to test step on the screen.\n"
        ui_prompt = ui_description
        test_step_prompt = f"The needed test step is: {test_step}.\n"
        instr_prompt = f"Response with one UI element index that can be grounded to the test step. Response only the index of UI element and nothing else."
        usr_prompt = "\n".join([ui_prompt,test_step_prompt,instr_prompt])
        messages = [('system',system_prompt),('user',usr_prompt)]
        resp = chat_completion_with_backoff(
            model=model,
            messages=self.transformMessage(messages),
            temperature=temp,
            n=1)
        print(resp)
        self.updateTokensUsed(resp["usage"])
        response = resp['choices'][0]['message']['content']
        return response
    def targeting(self,target,app,ui_description):
        system_prompt = f"Suppose You are an Android UI testing expert and helping select UI element to {target} on {app} app.\n"
        ui_prompt = ui_description
        instr_prompt = f"Response with one UI element index that can help {target}. Response only the index of UI element and nothing else."
        usr_prompt = "\n".join([ui_prompt,instr_prompt])
        messages = [('system',system_prompt),('user',usr_prompt)]
        resp = chat_completion_with_backoff(
            model=model,
            messages=self.transformMessage(messages),
            temperature=temp,
            n=1)
        print(resp)
        self.updateTokensUsed(resp["usage"])
        response = resp['choices'][0]['message']['content']
        return response
    
    def dream_tests(self,target,app,model_type,spawn_num = 5):
        system_prompt = f"Suppose You are an Android UI testing expert and helping write a UI test. Our test objective is to {target} on the {app} app. Give me one possible sequence of test steps to achieve the test objective.\n"
        instr_prompt = f"Response with only one json format with key being the order of steps and value being the test step description. Each test step should be some phrases instead of whole sentences."
        messages = [('system',system_prompt),('user',instr_prompt)]
        assert model_type in [model,expensive_model]
        resp = chat_completion_with_backoff(
            model=model_type,
            messages=self.transformMessage(messages),
            temperature=0.8,
            n=spawn_num)
        return resp

if __name__ == "__main__":
    setupChatGPT("")
    testsession = Session()
    # testsession.parse_test_steps("{\n  \"1\": \"Launch the AccuWeather app\",\n  \"2\": \"Click on the 'Favorites' tab\",\n  \"3\": \"Click on the 'Add' button\",\n  \"4\": \"Search for 'London'\",\n  \"5\": \"Select 'London' from the search results\",\n  \"6\": \"Click on the 'Save' button\",\n  \"7\": \"Click on the 'Settings' tab\",\n  \"8\": \"Click on the 'Default Location' option\",\n  \"9\": \"Search for 'London'\",\n  \"10\": \"Select 'London' from the search results\",\n  \"11\": \"Click on the 'Save' button\"\n}")
    
        
        
        