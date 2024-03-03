
from abc import ABC, abstractmethod
import logging
import pandas as pd
import csv
import json
import datetime
import time
from src.utilities import get_strtime
from datetime import datetime
import promptlayer
from openai import OpenAI
import os, glob
from langchain.llms import Ollama
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from timeout_function_decorator import timeout

from prompts.templates import llama2Templates
from src.ollamaclient import OllamaClient
from src.sqldb import HallucinationDb
from src.custom_exceptions import ProcessLockedException

GPT_MODEL_NAME = "gpt-3.5-turbo"
LLAMA2_7B_MODEL_NAME = "Llama-2-7b-Chat-GPTQ"
GPT_MODEL_ID = 1
LLAMA2_7B_MODEL_ID = 2


class QuestionAnswerProcessor(ABC):
    def __init__(self, settings) -> None:
        self.settings = settings
        self.db = HallucinationDb(settings)
        self.answers_table = self.db.GetTableDefinition(self.db.TERMS_ANSWERS_TABLE)
        self.models_table = self.db.GetTableDefinition(self.db.MODELS_TABLE)
        self.MAX_NEW_TOKENS = 2000

        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    @abstractmethod
    def answer(self, question):
        pass

    #def get_strtime(self):
    #    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def process_questions(self, questions_df:pd.DataFrame=None, verbose:bool=False, reverse:bool=False, sample_size:str=None, half:bool=False):

        self.logger.info(f"Processing questions with {self.model_name} model...")

        self.use_db = False

        self.questions_df = questions_df
        if self.questions_df is None:
            self.use_db = True
            self.initalize_questions_df(sample_size)
        else:
            if sample_size is not None:
                self.logger.warning("Sample size is ignored because a DataFrame is provided.")
              
        if reverse:
            self.questions_df = self.questions_df.iloc[::-1]
        if half:
            self.questions_df = self.questions_df.iloc[len(self.questions_df)//2:]

        if not self.use_db:
            self.answers_path = f"answers_{get_strtime()}.csv"
            self.answers_df = pd.DataFrame(columns=list(self.questions_df.columns) + ['model_id', 'model_name', 'answer'])
            self.answers_df.to_csv(self.answers_path, index=False)

        if verbose: 
            self.logger.info(f"There are {len(self.questions_df)} unanswered questions by {self.model_name} model in the dataset.")
            response_times = []
        for index, row in self.questions_df.iterrows():
            question = row["question"]
            
            if verbose: 
                start_time = datetime.now()
                self.logger.info(f"Time: {start_time.strftime('%H:%M:%S')}\nQuestion-{row['question_id']}: {question}")
            
            answer = self.answer(question)
            
            if verbose:
                end_time = datetime.now()
                response_time = (end_time - start_time).seconds
                response_times.append(response_time)
                average_time = sum(response_times) / len(response_times)
                self.logger.info(f"Time: {end_time.strftime('%H:%M:%S')} response took {response_time} seconds. Average response time: {average_time} \nAnswer: {answer}\n---\n")
            
            if not self.use_db:
                new_row = pd.DataFrame(row).transpose()
                new_row['model_id'] = self.model_id
                new_row['model_name'] = self.model_name
                new_row['answer'] = answer
                new_row.to_csv(self.answers_path, mode='a', header=False, index=False, quoting=csv.QUOTE_ALL)
            else:
                self.db.sql.execute(
                    self.answers_table.insert().values(
                        question_id = row["question_id"],
                        model_id = self.model_id,
                        answer = answer
                    )
                )
            
            if answer == "WARNING! Model failure." or answer == "WARNING! Timeout.":
                raise ProcessLockedException("Process locked due to a loop.")

    def GetModelId(self):
        query = self.models_table.select().where(self.models_table.c.name == self.model_name)
        query_result = self.db.sql.execute(query)

        if query_result.rowcount == 0:
            insert_query = self.models_table.insert().values(name = self.model_name)
            insert_result = self.db.sql.execute(insert_query)
            model_id = insert_result.inserted_primary_key[0]
        else:
            model_id = query_result.fetchone()[0]
        return model_id
        
    def initalize_questions_df(self, sample_size:str=None):
        all_questions_df = self.db.GetTableAsDf(self.db.COMBINED_TERMS_QUESTIONS)

        answers_table = self.db.GetTableDefinition(self.db.TERMS_ANSWERS_TABLE)
        answers_query = answers_table.select().where(answers_table.c.model_id == self.model_id)
        answered_questions_df = pd.read_sql(answers_query, self.db.sql.connection)
        
        self.questions_df = all_questions_df[~all_questions_df['question_id'].isin(answered_questions_df['question_id'])]
        if sample_size is not None:
            self.sample_questions(sample_size)

    def sample_questions(self, sample_size:str):
        current_dir = os.path.dirname(os.path.abspath('__file__'))
        parent_dir = os.path.dirname(current_dir)  
        data_dir_current = os.path.join(current_dir, 'data')
        data_dir_parent = os.path.join(parent_dir, 'data')

        if os.path.exists(data_dir_current):
            sampled_ids_path = os.path.join(data_dir_current, 'intermediate', 'sampled_ids.json')
        elif os.path.exists(data_dir_parent):
            sampled_ids_path = os.path.join(data_dir_parent, 'intermediate', 'sampled_ids.json')
        else:
            raise FileNotFoundError("The 'data' directory does not exist in the current or parent directory.")
    

        with open(sampled_ids_path, 'r') as f:
            sampled_ids_dict = json.load(f)
            if sample_size in sampled_ids_dict:
                sampled_ids = sampled_ids_dict[sample_size]
                self.questions_df = self.questions_df[self.questions_df['question_id'].isin(sampled_ids)]
            else:
                raise ValueError(f"Invalid sample size: {sample_size}. Expected '180', '1080', or None.")

class OllamaAnswerProcessor(QuestionAnswerProcessor):
    def __init__(self, settings):
        super().__init__(settings)
      

    def load_model(self, model_name):
        self.model_name = model_name
        self.model_id = self.GetModelId()
        self.model = OllamaClient(model_name=model_name)

    def answer(self, question):
        return self.model.generate(question)

class GptAnswerProcessor(QuestionAnswerProcessor):
    def __init__(self, settings):
        super().__init__(settings)
        self.model_id = GPT_MODEL_ID
        self.model_name = GPT_MODEL_NAME
        
        self.__check_settings(settings)
        self.client = OpenAI(api_key=settings.openai_api_key)

    def change_model(self, model_name):
        self.model_name = model_name
        self.model_id = self.GetModelId()

    def __check_settings(self, settings):
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is not set")
        
    def try_gptapi_call(self, messages, temperature=0, model=GPT_MODEL_NAME):
        for i in range(3):
            try:
                return self.inner_api_call(messages, temperature, model)
            except TimeoutError as exc:
                logging.exception(f"Timeout: {exc}\nRetrying...")
                time.sleep(2)
                continue
            except Exception as exc:
                logging.exception(f"Exception: {exc}")
                time.sleep(6)
                continue
        return "WARNING! Model failure."

    @timeout(120)
    def inner_api_call(self, messages, temperature, model):
        return self.client.chat.completions.create(
                    model=model,
                    temperature=temperature,
                    messages=messages)

    def answer(self, question):
        message = [{"role": "user", "content": question}]
        response = self.try_gptapi_call(message)
        answer = response.choices[0].message.content
        return answer








