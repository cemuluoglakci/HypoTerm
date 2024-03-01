import types
from googleapiclient.discovery import build
import json


class Searcher():

    def __init__(self, settings:types.ModuleType) -> None:
        self.keys_list = settings.google_api_keys
        self.get_keys()

    def get_keys(self):
        print("Getting keys")
        keys = self.keys_list.pop()
        self.api_key = keys["key"]
        self.cse_id = keys["ctx"]

    def search(self, query):
        query = query.replace('"', '')
        query = f'"{query}"'
        try:
            with build('customsearch', 'v1', developerKey=self.api_key, static_discovery=False) as service:
                res = service.cse().list(q=query, cx=self.cse_id).execute()
                self.result = res
                return res
        except:
            self.get_keys()
            #refactor later
            return self.search(query)

    def exists(self, result=None):
        try:
            if result == None:
                result = self.result
            return result["searchInformation"]["totalResults"] != "0"
        except:
            return False
        
    def get_total_result(self, result=None):
        try:
            if result == None:
                result = self.result
            return result["searchInformation"]["totalResults"]
        except:
            return 0