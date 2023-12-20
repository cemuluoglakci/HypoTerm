import pandas as pd
import re
import logging

from prompts import templates
from prompts.templates import llama2Templates
from src.answerevaluator import AnswerEvaluator

class OpenQuestionGenerator():
    def __init__(self, settings, 
                 model_name = "llama2:70b-chat-q4_K_M") -> None:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        self.settings = settings
        self.prompt_generator = llama2Templates(templates.question_generator_system)
        self.replace_prompt_generator = llama2Templates(templates.fresh_replacement_system)
        self.evaluator = AnswerEvaluator(model_name, self.settings)

    def process_df(self, df:pd.DataFrame):
        df['questions_and_types'] = df.apply(self.generate_questions_and_types, axis=1)
        df = df.explode('questions_and_types')
        df[['question', 'type']] = pd.DataFrame(df['questions_and_types'].tolist(), index=df.index)
        df = df.drop(columns=['questions_and_types'])
        return df

    def generate_questions_and_types(self, row):
        questions = []
        replacement_types = []
        self.logger.info(f"\n\n---\n\nProcessing row")

        madeup_term = f"{row['hypothetical_terms']}: {row['hypothetical_terms_meaning']}"
        topic = f"{row['topics']}: {row['topics_meaning']}"
        real_term = f"{row['secondary_terms']}: {row['secondary_terms_meaning']}"
        replacement_term = f"{row['replacement_terms']}: {row['replacement_terms_meaning']}"

        #Hypothetical question
        user_prompt = templates.question_generator_user.format(topic=topic, 
                                                                madeup_term=madeup_term,
                                                                real_term=real_term)   
        halu_prompt = self.prompt_generator.generate_message([user_prompt], [])
        hypothetical_question = self.evaluator.model.try_model_call(halu_prompt)
        questions.append(hypothetical_question)
        replacement_types.append(0)
        self.logger.info(f"Hypothetical question: {hypothetical_question}")

        #Programmatic replacement question
        pattern = self.get_combined_pattern(row["hypothetical_terms"])
        programmatically_replaced_q = pattern.sub(row["replacement_terms"], hypothetical_question)
        questions.append(programmatically_replaced_q)
        replacement_types.append(1)

        if programmatically_replaced_q == hypothetical_question:
            self.logger.warning(f"Warning for replacement: {row['hypothetical_terms']} not found in {hypothetical_question}")
        else:
            self.logger.info(f"Programmatic replacement question: {programmatically_replaced_q}")
        #Replacement question
        replacement_user_prompt = templates.fresh_replacement_user.format(
                topic = topic,
                main_term = replacement_term,
                secondary_term = real_term
            )
        replacement_prompt = self.replace_prompt_generator.generate_message([replacement_user_prompt], [])
        replacement_question = self.evaluator.model.try_model_call(replacement_prompt)
        questions.append(replacement_question)
        replacement_types.append(3)
        self.logger.info(f"Replacement question: {replacement_question}") 
        return [{'question': q, 'replacement_type': t} for q, t in zip(questions, replacement_types)]

    def get_combined_pattern(self, key: str):
        alt_key = re.sub(r'\([^()]*\)', '', key).strip()
        return re.compile(f"{re.escape(key)}|{re.escape(alt_key)}", re.IGNORECASE)
