import pandas as pd
import logging
from sqlalchemy import update, insert, text as sa_text
from enum import Enum
from src.sqldb import HallucinationDb
from src.utilities import get_strtime
EVAL_LABELS = {0: "valid", 1: "hallucination", 2: "irrelevant"}
EVAL_TYPES = {1: "human", 2: "acceptance", 3: "definition", 4: "code check"}

class Eval(Enum):
    VALID = 0
    HALLUCINATION = 1
    IRRELEVANT = 2

class AnswerLabel:
    def __init__(self, answer_id:int, answer_label:int, evaluator_model_id:int):
        self.answer_id = answer_id
        self.answer_label = answer_label
        self.evaluator_model_id = evaluator_model_id

INCLUSION_CHECK = 4
ACCEPTANCE_CHECK = 2
MEANING_CHECK = 3

PROGRAMMATIC_CHECK_MODEL_ID = 10
HUMAN_EVAL_MODEL_ID = 0

class AnswerLabeler():
    def __init__(self, settings):
        self.settings = settings
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        try:
            self.db = HallucinationDb(self.settings)
            self.evals_table = self.db.GetTableDefinition(self.db.TERMS_ANSWERS_EVAL_TABLE)
            self.labels_table = self.db.GetTableDefinition(self.db.ANSWER_LABELS_TABLE)
        except Exception as e:
            self.logger.warning(f"AnswerLabeler initialized without a database connection: {str(e)}")

    def max_eval(self, eval_list:list) -> Eval:
        if Eval.HALLUCINATION.value in eval_list: return Eval.HALLUCINATION
        if Eval.IRRELEVANT.value in eval_list: return Eval.IRRELEVANT
        return Eval.VALID

    def label_validity_checks(self, df:pd.DataFrame) -> bool:
        return True
    
    def assign_labels(self, evals_df:pd.DataFrame=None, truncate_table:bool=True):
        if evals_df is None:

            if truncate_table:
                self.db.sql.connection.engine.execute(sa_text(f'''TRUNCATE  TABLE {self.db.ANSWER_LABELS_TABLE}''').execution_options    (autocommit=True))
    
            evals_df = pd.read_sql(self.evals_table.select(), self.db.sql.  connection)
    
            evals_df.drop_duplicates(subset=["answer_id", "eval_type_id",   "term_source", "term_id", "model_id"], inplace=True)
            self.logger.info(f"Term level evaluation count: {evals_df.shape[0]} ")
        
        evaluator_model_ids = sorted(evals_df.model_id.unique())
        if HUMAN_EVAL_MODEL_ID in evaluator_model_ids and hasattr(self, 'db'):
            evaluator_model_ids.remove(HUMAN_EVAL_MODEL_ID)
        if PROGRAMMATIC_CHECK_MODEL_ID in evaluator_model_ids and hasattr(self, 'db'):
            evaluator_model_ids.remove(PROGRAMMATIC_CHECK_MODEL_ID)
        
        for evaluator_model_id in evaluator_model_ids:

            answer_ids = sorted(evals_df[evals_df["model_id"]==evaluator_model_id].answer_id.unique())
            self.logger.info(f"Unique answer count: {len(answer_ids)} for model id: {evaluator_model_id}")

            answer_label_list = []
            for answer_id in answer_ids:
                answer_eval_df = evals_df[(evals_df["answer_id"]==answer_id) & ((evals_df["model_id"]==PROGRAMMATIC_CHECK_MODEL_ID) | (evals_df["model_id"]==evaluator_model_id))]
                if hasattr(self, 'db'):
                    eval_labels = answer_eval_df.eval_label.values
                else:
                    eval_labels = answer_eval_df.eval_label_id.values
                answer_eval_label = self.max_eval(eval_labels)

                input_dict = {}
                input_dict['answer_id'] = answer_id
                input_dict['answer_label'] = answer_eval_label.value
                input_dict['evaluator_model_id'] = evaluator_model_id
                answer_label_list.append(input_dict)
            if hasattr(self, 'db'):
                self.db.sql.connection.engine.execute(self.labels_table.insert(), answer_label_list)
            else:
                answer_label_df = pd.DataFrame(answer_label_list).rename(columns={'answer_label': 'answer_label_id'})
                answer_label_df['answer_label'] = answer_label_df['answer_label_id'].map(EVAL_LABELS)
                evals_df = pd.merge(evals_df, answer_label_df, how='left', on='answer_id')
                evals_df.to_csv(f"evals_df_{get_strtime()}.csv", index=False)
                return evals_df

