# Rename this file as settings.py and fill in or replace the required values

# Google custom search key
google_api_keys = [
    {
        "account": "",
        "ctx": "",
        "key": ""
    }]

# Milvus server for vector search
milvus_alias="default"
milvus_host='localhost'
milvus_port='19530'

# Sql Server for persisting data
DB_USER = "testuser"
DB_PASSWORD = "ch4ng3m3"
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB = "hallucinative"

# Email server for sending notification emails about process status
email_settings = {
    "email": "",
    "password": "",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "recipient_email": "",
    "subject": "Hallucination Server Work",
    "message": "Hallucination Server Message"
}

# OpenAI API key for prompting GPT models
openai_api_key = ""