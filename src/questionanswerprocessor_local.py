
from exllama.model import ExLlama, ExLlamaCache, ExLlamaConfig
from exllama.tokenizer import ExLlamaTokenizer
from exllama.generator import ExLlamaGenerator
import os, glob
import torch

from prompts.templates import llama2Templates
from src.questionanswerprocessor import QuestionAnswerProcessor

GPT_MODEL_NAME = "gpt-3.5-turbo"
LLAMA2_7B_MODEL_NAME = "Llama-2-7b-Chat-GPTQ"
GPT_MODEL_ID = 1
LLAMA2_7B_MODEL_ID = 2

    
class LlamaAnswerProcessor(QuestionAnswerProcessor):
    def __init__(self, settings):
        super().__init__(settings)
        self.model_id = LLAMA2_7B_MODEL_ID
        self.model_name = LLAMA2_7B_MODEL_NAME
        self.stop_tokens = [29989, 326, 29918, 355, 29989, 29958]

    def load_model(self, model_directory):
        tokenizer_path = os.path.join(model_directory, "tokenizer.model")
        model_config_path = os.path.join(model_directory, "config.json")
        st_pattern = os.path.join(model_directory, "*.safetensors")
        model_path = glob.glob(st_pattern)[0]

        config = ExLlamaConfig(model_config_path)               # create config from config.json
        config.model_path = model_path                          # supply path to model weights file

        self.model = ExLlama(config)                                 # create ExLlama instance and load the weights
        self.tokenizer = ExLlamaTokenizer(tokenizer_path)            # create tokenizer from tokenizer model file

        cache = ExLlamaCache(self.model)                             # create cache for inference
        self.generator = ExLlamaGenerator(self.model, self.tokenizer, cache)   # create generator

        # Configure generator

        self.generator.disallow_tokens([self.tokenizer.eos_token_id])

        self.generator.settings.token_repetition_penalty_max = 1.2
        self.generator.settings.temperature = 0.1
        self.generator.settings.top_p = 0.65
        self.generator.settings.top_k = 100
        self.generator.settings.typical = 0.5

    def answer(self, question):
        message = self.wrap_llama_template([question])
        response = self.generate(message)
        return response

    def generate_tokens(self, message: str, stream: bool = False, max_new_tokens: int = 2000):
        ids, mask = self.tokenizer.encode(message, return_mask = True, max_seq_len = self.model.config.max_seq_len)
        self.generator.gen_begin(ids, mask = mask)
        max_new_tokens = min(self.MAX_NEW_TOKENS, self.generator.model.config.max_seq_len - ids.shape[1])
        eos = torch.zeros((ids.shape[0],), dtype = torch.bool)
        response_tokens=[]
        for i in range(max_new_tokens):
            token = self.generator.gen_single_token(mask = mask)
            if stream: print(self.tokenizer.decode(token[0]), end=' ', flush=True)

            for j in range(token.shape[0]):
                if token[j, 0].item() == self.tokenizer.eos_token_id: eos[j] = True
            if eos.all(): break

            response_tokens.append(token[0].item())

            if token == self.stop_tokens[-1]:
                if response_tokens[-len(self.stop_tokens):] == self.stop_tokens:
                    response_tokens = response_tokens[:-1*(len(self.stop_tokens)+1)]
                    return response_tokens

        text = self.tokenizer.decode(self.generator.sequence[0])#[len(prompt):].replace("<|im_end|>", "")
        print(text)
        return response_tokens

    def generate(self, message: str, stream: bool = False, max_new_tokens: int = None):
        response_tokens = self.generate_tokens(message, stream, max_new_tokens)
        response = self.tokenizer.decode(torch.tensor(response_tokens))
        return response

    def wrap_llama_template(self, prompts:list[str], system_message: str = None, replies:list[str] = []):
        llama_templates = llama2Templates(system_message)
        return llama_templates.generate_message(prompts, replies)
