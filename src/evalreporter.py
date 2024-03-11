import os
import json
import pandas as pd
import logging
import matplotlib.pyplot as plt
import scienceplots

from src.sqldb import HallucinationDb
from src.utilities import get_strtime

FUNCTION = "function"

class EvalReporter():
    def __init__(self, settings):
        self.settings = settings
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        try:
            self.db = HallucinationDb(self.settings)
            self.eval_table = self.db.GetTableDefinition(self.db.ANSWER_LEVEL_LABELS)
            self.detail_table = self.db.GetTableDefinition(self.db.TERM_LEVEL_LABELS)
        except Exception as e:
            self.logger.warning(f"EvalReporter initialized without a database connection: {str(e)}")

        plt.style.use(['science','no-latex'])

        self.tag_list = ['-chat-q4_K_M', '-chat-q4_1', '-q4_1', '_August_3_2023', '-1106-preview', '-turbo']

        self.detail_columns = ["answer_source", "question_id", "answer_id", "question", "answer","isHypotheticalQuestion", "evaluator_model", "eval_id", "eval_type", "term_label_id", "term_label", "term", "term_id", "IsHypotheticalTerm", "term_source", "reflection", "answer_label_id", "answer_label"]

    def get_eval_df(self, evaluator_model:str, model_under_test:str, sample_size:str=None, analyse_df:pd.DataFrame=None):
        if analyse_df is None:
            query = self.eval_table.select(
                ).where(self.eval_table.c.evaluator_model.in_([evaluator_model,     FUNCTION])
                ).where(self.eval_table.c.answer_source == model_under_test
                )

            self.logger.info(f"sample size: {sample_size}")

            if sample_size:
                query = self._filter_for_samples(query, self.eval_table, sample_size) 

            analyse_df = pd.read_sql(query, self.db.sql.connection)
        else:
            self.logger.info("The provided DataFrame is being used. The 'sample_size' parameter is ignored when a DataFrame is provided.")
            
        # Define the order of the categories
        categories_order = ['valid', 'hallucination', 'irrelevant']
        # Replace the values and convert the column to a categorical type
        analyse_df['answer_label'] = pd.Categorical(analyse_df['answer_label'], categories=categories_order, ordered=True)

        self.logger.info(f"analyse_df shape: {analyse_df.shape}")

        all_questions = analyse_df.answer_label.value_counts(normalize=True).sort_index().mul(100).round(2)
        hypothetical_questions = analyse_df[analyse_df["isHypotheticalQuestion"] == True].answer_label.value_counts(normalize=True).sort_index().mul(100).round(2)
        valid_questions = analyse_df[analyse_df["isHypotheticalQuestion"] == False].answer_label.value_counts(normalize=True).sort_index().mul(100).round(2)

        self.eval_df = pd.DataFrame({
            "all_questions": all_questions,
            "hypothetical_questions": hypothetical_questions,
            "valid_questions": valid_questions,
        }).fillna(0)

        hypoterm_score = self.eval_df.loc["valid", "hypothetical_questions"] 
        self.logger.info(f"HypoTerm score of {model_under_test}: {hypoterm_score}%")

        return self.eval_df
    
    def get_detail_df(self, evaluator_model:str, model_under_test:str, sample_size:str=None):
        query = self.detail_table.select(
        ).where(self.detail_table.c.answer_source == model_under_test
        ).where(self.detail_table.c.evaluator_model.in_([evaluator_model, FUNCTION]))

        if sample_size:
            query = self._filter_for_samples(query, self.detail_table, sample_size) 

        detail_df = pd.read_sql(query, self.db.sql.connection)
        subset = [col for col in detail_df.columns if col != 'eval_id']
        detail_df.drop_duplicates(subset=subset, inplace=True)
        detail_df.drop_duplicates(subset=['eval_id'], inplace=True)
        return detail_df

    def get_eval_chart(self, evaluator_model:str, model_under_test:str, sample_size:str=None):
        if not hasattr(self, 'eval_df'):
            print("No eval_df found. Creating a new one...")
            self.eval_df = self.get_eval_df(evaluator_model, model_under_test, sample_size)
        evaluator_model_str = self._strip_tags(evaluator_model)   
        model_under_test_str = self._strip_tags(model_under_test).upper()
        font_size = 24

        listlist = [[0 for _ in range(len(self.eval_df.columns))] for _ in range(len(self.eval_df.  index))]
        positions = []
        for i, column in enumerate(self.eval_df.columns.values):
            col_total = self.eval_df[column].sum()
            listlist[0][i] = col_total
            position_list = []
            for j, row in enumerate(self.eval_df.index.values):
                current_total = listlist[j][i]
                current_value = self.eval_df[column][row]
                new_total = current_total - current_value
                position_list.append((
                    max(((current_total+new_total-font_size/2)/2), new_total)
                                      , current_value))
                if j+2 > len(self.eval_df.index.values):
                    break
                listlist[j+1][i] = new_total
            positions.append(position_list)


        with plt.style.context(['science','no-latex', 'grid', 'notebook',   'high-vis', 'bright']):

            plt.rcParams.update({'font.size': font_size})

            plt.figure(figsize=(8, 6))

            #for j, row in enumerate(df.index.values):
            bar_names = ['all', 'hypothetical','valid']
            colors = ['#99ddff', '#ee8866', '#dddddd']
            for j, row in enumerate(['valid', 'hallucination','irrelevant']):
                plt.bar(bar_names, listlist[j], label=row
                        ,  color=colors[j]
                        )
                for i, value in enumerate(listlist[j]):
                    plt.text(i, positions[i][j][0], str(positions[i][j][1])+"%",    ha='center', va='bottom')

            # Add labels and title
            plt.xlabel('Question Type')
            plt.ylabel('Percentage')
            plt.title(f'{model_under_test_str} Performance on HypoTermQA')

            # Add legend
            plt.legend(loc='upper right')

            plot_name = f"evaluate_{evaluator_model_str}_{model_under_test_str}_{get_strtime()}"
            if sample_size:
                plot_name = plot_name + f"_sampled_{sample_size}_"
            plot_name = plot_name + ".png"
            plt.savefig(plot_name)

            plt.show()

    def get_detail_json(self, evaluator_model:str, model_under_test:str, detail_df:pd.DataFrame=None, sample_size:str=None):
        if detail_df is None:
            detail_df = self.get_detail_df(evaluator_model, model_under_test,sample_size)
        elif sample_size is not None:
            self.logger.info("The provided DataFrame is being used. The 'sample_size' parameter is ignored when a DataFrame is provided.")

        if not set(self.detail_columns).issubset(detail_df.columns):
            missing_columns = set(self.detail_columns) - set(detail_df.columns)
            raise ValueError(f"The following required columns are missing from the DataFrame: {missing_columns}")

        json_str = ""
        first_layer = detail_df.groupby(["answer_source"])
    
        for group_name, df_group in first_layer:
            json_str += f"""{{\n"answer_source": "{group_name[0]}",\n"questions":   [\n"""
    
            second_layer = df_group.groupby(["question_id"])
    
            for group_name, df_group in second_layer:
                upper_json_row = df_group[["question_id", "answer_id", "question",  "answer", 
                                           "answer_label", 
                                           'isHypotheticalQuestion',    "evaluator_model"]].iloc[0].to_json()
                json_str += upper_json_row[:-1]
                json_str += """,\n"evaluations": [\n"""
    
                for row_index, row in df_group.iterrows():
                    json_row = row[["eval_id", "eval_type", "term_label", "term",   'term_id', 'IsHypotheticalTerm', 'term_source', "reflection"]].   to_json()
                    json_str += json_row
                    json_str += ",\n"
                json_str = json_str[:-2]
                json_str += "\n]\n},"
    
            json_str = json_str[:-1]
            json_str += "\n]\n},"
    
        json_str = json_str[:-1]
    
        parsed = json.loads(json_str)
        evaluator_model_str = self._strip_tags(evaluator_model) 
        model_under_test_str = self._strip_tags(model_under_test)

        file_name = f"evaluate_{evaluator_model_str}_{model_under_test_str}_{get_strtime()}"
        if sample_size:
            file_name = file_name + f"_sampled_{sample_size}_"
        file_name = file_name + ".json"

        with open(file_name, 'w', encoding ='utf8') as json_file: 
            json.dump(parsed, json_file, allow_nan=True, indent=4) 
        return parsed

    def _strip_tags(self, text:str):
        for tag in self.tag_list:
            text = text.replace(tag, "")
        text = text.replace(":", "_")
        return text

    def _filter_for_samples(self, query, table, sample_size):
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
            else:
                raise ValueError(f"Invalid sample size: {sample_size}. Expected '180', '1080', or None.")

        return query.where(table.c.question_id.in_(sampled_ids))
