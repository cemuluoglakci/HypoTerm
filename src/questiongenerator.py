
from abc import ABC, abstractmethod
import logging
import pandas as pd
import datetime
import time
import promptlayer
import json
import re

from prompts import templates
from src.sqldb import HallucinationDb

Q_PER_TERM = 3
GPT_MODEL_NAME = "gpt-3.5-turbo"
GPT_SUGGESTION_ID = 1
TITLE_SIMILARITY_ID = 2
TEXT_SIMILARITY_ID = 3

NO_REPLACEMENT = 0
PROGRAMMATIC_REPLACEMENT = 1
GOLD_ANSWER_REPLACEMENT = 2
FRESH_REPLACEMENT = 3

hallucinative_df_columns = ["fake_term_id", "fake_term", "fake_term_explanation", 
                            "topic", "topic_explanation", "source_id", 
                            "real_term_id", "real_term", "real_term_explanation"]


class QuestionGenerator(ABC):
    def __init__(self, settings) -> None:
        self.__check_settings(settings)
        self.settings = settings
        promptlayer.api_key = settings.promptlayer_api_key
        self.openai = promptlayer.openai
        self.openai.api_key = settings.openai_api_key
        self.db = HallucinationDb(settings)

    @abstractmethod
    def generate(self, question):
        pass

    def get_strtime(self):
        return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def try_gptapi_call(self, messages, temperature=0, model=GPT_MODEL_NAME):
        for i in range(3):
            try:
                return self.openai.ChatCompletion.create(
                    model=model,
                    temperature=temperature,
                    messages=messages)
            except Exception as exc:
                logging.exception(f"Exception: {exc}")
                time.sleep(60)
                continue

    def __check_settings(self, settings):
        if not settings.promptlayer_api_key:
            raise ValueError("Promptlayer API key is not set")
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is not set")


class NonExistentTermQuestionGenerator(QuestionGenerator):
    def __init__(self, settings, hallucinative_df: pd.DataFrame):
        super().__init__(settings)
        self.__check_hallucinative_df(hallucinative_df)
        self.hallucinative_df = hallucinative_df

    def combine_term_triplets(self):
        self.fake_terms_ids = self.hallucinative_df["fake_term_id"].unique()
        self.term_triplets_table = self.db.GetTableDefinition(
            self.db.TERM_TRIPLETS_TABLE)
        
        for fake_term_id in self.fake_terms_ids:
            print(f"creating for fake term id: {fake_term_id}")
            self.__set_specific_term(fake_term_id)

            source_id_list = self.specific_term_df["source_id"].unique().tolist()
            df_list = []
            for source_id in source_id_list:
                df_list.append(self.specific_term_df[self.specific_term_df["source_id"] == source_id])

            for i in range(len(df_list)):
                print("Source id: ", source_id_list[i])
                arranged_df = pd.concat(df_list)
                #print(arranged_df[['fake_term_id', 'real_term_id', 'source_id']])
                df_list = df_list[1:] + df_list[:1]

                added_triplets = 0
                secondary_term_index = 0
                while added_triplets < Q_PER_TERM:

                    secondary_term_id = arranged_df.iloc[secondary_term_index]["real_term_id"]
                    secondary_term_source_id = arranged_df.iloc[secondary_term_index]["source_id"]
                    replacement_term_id = arranged_df.iloc[secondary_term_index + Q_PER_TERM]["real_term_id"]
                    replacement_term_source_id = arranged_df.iloc[secondary_term_index]["source_id"]

                    triplet_key = (fake_term_id, secondary_term_id, secondary_term_source_id, replacement_term_id, replacement_term_source_id)

                    try:
                        self.__insert_triplet(triplet_key)
                        added_triplets += 1
                        print("Added triplet: ", triplet_key)
                    except Exception as e:
                        print("Skipped triplet: ", triplet_key)
                    secondary_term_index += 1

    def __insert_triplet(self, triplet_key):
        self.db.sql.execute(
            self.term_triplets_table.insert().values(
                nonexistent_id = triplet_key[0],
                secondary_id = triplet_key[1],
                secondary_source = triplet_key[2],
                replacement_id = triplet_key[3],
                replacement_source = triplet_key[4]
            )
        )

    def generate(self):
        self.questions_table = self.db.GetTableDefinition(
            self.db.TERMS_QUESTIONS_TABLE)
        self.term_triplets = self.db.GetTableAsDf(
            self.db.TERM_TRIPLETS_COMBINED)
        
        ### delete later
        self.old_questions = self.db.GetTableDefinition(
            self.db.TERM_QUESTIONS_TABLE)
        
        for index, row in self.term_triplets.iterrows():
            self.__generate_questions(row)

    def __generate_questions(self, row: pd.Series):
        hallucinative_question = self.__generate_hallucinative_question(row)
        if hallucinative_question:
            self.__programmatically_replace(hallucinative_question,row)
            self.__fresh_replace(row)

    def __programmatically_replace(self, hallucinative_question, row):

        pattern = self.__get_combined_pattern(row["nonexistent_term"])
        programmatically_replaced_q = pattern.sub(row["replacement_term"], hallucinative_question)
        if programmatically_replaced_q == hallucinative_question and hallucinative_question != "test content":
            print(f"Warning for replacement: {row['nonexistent_term']} not found in {hallucinative_question}")
            print(row.to_dict())
        self.__insert_question(programmatically_replaced_q, row, PROGRAMMATIC_REPLACEMENT)

    def __fresh_replace(self, row):

        ####
        #### delete later
        possible_question = self.__check_question(row, FRESH_REPLACEMENT)
        if possible_question:
            self.__insert_question(possible_question, row, FRESH_REPLACEMENT)
            return possible_question
        

        user_prompt = templates.fresh_replacement_user.format(
            topic = f"""{row["topic"]}: {row["topic_explanation"]}""",
            main_term = f"""{row["replacement_term"]}: {row["replacement_explanation"]}""",
            secondary_term = f"""{row["secondary_term"]}: {row["secondary_explanation"]}"""
        )
        messages = [{"role": "system", "content": templates.fresh_replacement_system},
                    {"role": "user", "content": user_prompt}]
        fresh_response = self.try_gptapi_call(messages)
        fresh_question = fresh_response['choices'][0]['message']['content']
        self.__insert_question(fresh_question, row, FRESH_REPLACEMENT)

    def __generate_hallucinative_question(self, row):

        ####
        #### delete later
        possible_question = self.__check_question(row, NO_REPLACEMENT)
        if possible_question: 
            if self.__validate_question(possible_question, row, NO_REPLACEMENT):
                self.__insert_question(possible_question, row, NO_REPLACEMENT)
                return possible_question


        hallucinative_messages = self.__get_hallucinative_messages(row)
        hallucinative_response = self.try_gptapi_call(hallucinative_messages)
        hallucinative_question = hallucinative_response['choices'][0]['message']['content']
        if self.__validate_question(hallucinative_question, row, NO_REPLACEMENT):
            self.__insert_question(hallucinative_question, row, NO_REPLACEMENT)
            return hallucinative_question
        return ""

    def __get_hallucinative_messages(self, row: pd.Series):
        user_prompt = templates.question_generator_user.format(
            topic=f"""{row["topic"]}: {row["topic_explanation"]}""", 
            madeup_term=f"""{row["nonexistent_term"]}: {row["nonexistent_explanation"]}""",
            real_term = f"""{row["secondary_term"]}: {row["secondary_explanation"]}"""
        )
        return [{"role": "system", "content": templates.question_generator_system},
                {"role": "user", "content": user_prompt}]

    def __check_question(self, row: pd.Series, replacement_type: int = 0):
        
        if replacement_type == NO_REPLACEMENT:
            main_id = row["nonexistent_id"]
            main_source = NO_REPLACEMENT
        else:
            main_id = row["replacement_id"]
            main_source = row["replacement_source_id"]
        

        query = self.old_questions.select().where(
            self.old_questions.c.main_id == main_id,
            self.old_questions.c.main_source == main_source,
            self.old_questions.c.secondary_id == row["secondary_id"],
            self.old_questions.c.secondary_source == row["secondary_source_id"],
            self.old_questions.c.replacement_type == replacement_type
        )
        #print(query)

        result = self.db.sql.execute(query).fetchone()
        if result:
            return result["question"]
        else:
            return False
        #if replacement_row is None:
        #    main_id = main_row["fake_term_id"]
        #    main_source = 0
        #else:
        #    main_id = replacement_row["real_term_id"]
        #    main_source = replacement_row["source_id"]

    def __validate_question(self, hallucinative_question: str, row: pd.Series,
                            replacement_type: int = 0):
        if not replacement_type:
            main_pattern = self.__get_combined_pattern(row["nonexistent_term"])
        else:
            main_pattern = self.__get_combined_pattern(row["replacement_term"])
        secondary_pattern = self.__get_combined_pattern(row["secondary_term"])
        
        if hallucinative_question != "test content":
            if not re.search(main_pattern, hallucinative_question) and not replacement_type:
                logging.warning(f"Warning for creation {replacement_type}: {main_pattern} not found in {hallucinative_question}")
                #print(self.__get_hallucinative_messages(row))
                return False

            if not re.search(secondary_pattern, hallucinative_question):
                logging.info(f"Info for creation: {row['secondary_term']} not found in {hallucinative_question}")
                return True
        return True


    def __insert_question(self, hallucinative_question: str , row: pd.Series, 
                          replacement_type: int = 0):

        self.db.sql.execute(
            self.questions_table.insert().values(
                question = hallucinative_question,
                triplet_id = row["term_triplet_id"],
                replacement_type = replacement_type
            )
        )

    def __set_specific_term(self, fake_term_id):
        self.specific_term_df = self.hallucinative_df[
            self.hallucinative_df["fake_term_id"] == fake_term_id]
        self.madeup_term = f"""{self.specific_term_df.iloc[0]["fake_term"]}: {self.specific_term_df.iloc[0]["fake_term_explanation"]}"""
        self.topic = f"""{self.specific_term_df.iloc[0]["topic"]}: {self.specific_term_df.iloc[0]["topic_explanation"]}"""

    def __check_hallucinative_df(self, hallucinative_df: pd.DataFrame):
        if not set(hallucinative_df_columns).issubset(hallucinative_df.columns):
            raise ValueError(
                f"hallucinative_df must have columns: {hallucinative_df_columns}")
        
    def __get_combined_pattern(self, key: str):
        alt_key = re.sub(r'\([^()]*\)', '', key).strip()
        return re.compile(f"{re.escape(key)}|{re.escape(alt_key)}", re.IGNORECASE)

