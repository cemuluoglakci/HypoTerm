import requests
import logging
import time
from timeout_function_decorator import timeout

default_system_prompt = """You are a helpful, respectful and honest assistant. Always answer as helpfully as possible.
If you don’t know the answer to a question, don’t share false information."""


class OllamaClient:
    def __init__(self, host = "localhost",
                 port = "11434", 
                 model_name = None):
        self.host = host
        self.port = port
        self.base_url = f"http://{self.host}:{self.port}"
        self.model_name = model_name or "llama2:7b-chat-q4_1"
        
    def generate(self, prompt:str, 
                 system_prompt:str = default_system_prompt, 
                 num_ctx = 4096,
                 max_tokens:int = 4096,
                 temperature:float = 0,
                 num_gpu:int = 100,
                 raw:bool = False
                 ) -> str:
        self.system_prompt = system_prompt
        self.prompt = prompt
        self.num_ctx = num_ctx 
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.num_gpu = num_gpu
        self.raw = raw

        return self.try_model_call()

    def try_model_call(self):
        for i in range(3):
            try:
                return self.model_call()
            except TimeoutError as exc:
                logging.exception(f"Timeout: {exc}")
                return "WARNING! Timeout."
            except Exception as exc:
                logging.exception(f"Exception: {exc}")
                time.sleep(6)
                continue
        return "WARNING! Model failure."

    @timeout(500)
    def model_call(self):
        url = f"{self.base_url}/api/generate/"

        data = {
            "model": self.model_name,
            "prompt": self.prompt,
            "stream": False,
            "options": {
                "num_predict": self.max_tokens,
                "temperature": self.temperature,
                "penalize_newline": False,
                "num_ctx": self.num_ctx,
                "num_gpu": self.num_gpu,
            }
        }
        if self.raw:
            data['raw'] = True
        else:
            data['raw'] = False
            data['system'] = self.system_prompt
        raw_response = requests.post(url, json=data)
        try:
            llama_response = raw_response.json()['response']
        except Exception as exc:
            logging.exception(f"Exception: {exc}")
            llama_response = raw_response.text
        return llama_response      
        