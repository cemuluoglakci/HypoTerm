import pandas as pd
import pymysql
import sqlalchemy
from sqlalchemy.orm import sessionmaker
import time

class SqlConnection():
    def __init__(self, settings) -> None:
        self.settings=settings
        connectionString = self.createConnectionString()
        self.engine = sqlalchemy.create_engine(connectionString)
        self.metadata = sqlalchemy.MetaData()
        self.session = sessionmaker(bind=self.engine)
        self.connect()


    def connect(self):
        self.connection = self.engine.connect()
        return self.connection

    def setTableDefinition(self, tableName:str) -> sqlalchemy.Table:
        return sqlalchemy.Table(
            tableName, 
            self.metadata, 
            autoload=True, 
            autoload_with=self.engine)

    def execute(self, statement):
        #Retry mechanism implemented as database and pymysql library usually gives connection error.
        for i in range(5):
            try:
                result = self.connection.execute(statement)
                return result
            except (pymysql.err.IntegrityError, sqlalchemy.exc.IntegrityError) as error:
                print(f"Integrity error. Statement discarded... \n{str(error)}")
                #raise error
                break
            except pymysql.err.OperationalError as error:
                print(f"Database connection lost. Retrying... \n{str(error)}")
                time.sleep(0.3)
                continue
            except Exception as e:
                print(f"error type: {type(e)}")
                if hasattr(e, "message"):
                    print(f"General DB Error: {str(e.message)}")
                print(f"Database connection lost. Sleeping for 2 seconds... \n")
                time.sleep(0.2)
                continue

    def createConnectionString(self):
        return ("mysql+pymysql://"
        f"{self.settings.DB_USER}:"
        f"{self.settings.DB_PASSWORD}@"
        f"{self.settings.DB_HOST}:"
        f"{self.settings.DB_PORT}/"
        f"{self.settings.DB}")

class HallucinationDb():
    TOPIC_TABLE = "topic"
    NONEXISTENT_TABLE = "nonexistent"
    REAL_TERMS_TABLE = "real_terms"
    NONEXISTENT_REAL_TABLE = "nonexistent_real"
    TERMS_COMBINED_TABLE = "terms_combined"
    TERMS_QUESTIONS_TABLE = "terms_questions"
    COMBINED_TERMS_QUESTIONS = "combined_terms_questions"
    TERMS_ANSWERS_TABLE = "terms_answers"
    MODELS_TABLE = "models"
    COMBINED_TERMS_ANSWERS = "combined_terms_answers"
    TERM_TRIPLETS_TABLE = "term_triplets"
    TERM_TRIPLETS_COMBINED = "term_triplets_combined"
    TERMS_ANSWERS_EVAL_TABLE = "terms_answers_eval"
    ANSWER_LABELS_TABLE = "terms_eval_answer_labels"
    ANSWER_LEVEL_LABELS= "label_answer_level"
    TERM_LEVEL_LABELS= "label_term_level"
    

    def __init__(self, settings) -> None:
        self.settings = settings
        self.sql = SqlConnection(settings)
        self.session = self.sql.session

    def GetTableDefinition(self, tableName:str) -> sqlalchemy.Table:
        if not hasattr(self, tableName):
            setattr(self, tableName, self.sql.setTableDefinition(tableName))
        return getattr(self, tableName)

    def GetTableAsDf(self, tableName:str) -> pd.DataFrame:
        tableDefinition = self.GetTableDefinition(tableName)
        query = tableDefinition.select()
        return pd.read_sql(query, self.sql.connection)
