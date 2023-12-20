from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from pymongo.collation import Collation

class WikiSearcher():

    def __init__(self) -> None:
        self.client = MongoClient('localhost', 27017, serverSelectionTimeoutMS=30000)
        self.db = self.client.kilt
        self.collection = self.db.knowledgesource

    def search(self, query):
        try:
            return self.collection.find({"wikipedia_title": query}).collation(Collation(locale='en', strength=1)).next()
        except StopIteration:
            return None
        
    def search_by_id(self, id):
        try:
            return self.collection.find({"_id": id}).next()
        except StopIteration:
            return None


    def get_definition(self, query):
        result = self.search(query)
        definition = "None"
        try:
            if result:
                first_paragraph = result['text'][1]
                if "refer to" in first_paragraph:
                    definition = "ambiguous"
                elif "::::" in first_paragraph:
                    definition = result['text'][2]
                else:
                    definition =  first_paragraph
        except:
            pass
        return definition
    
    def get_definition_by_id(self, id):
        result = self.search_by_id(id)
        definition = "None"
        try:
            if result:
                first_paragraph = result['text'][1]
                if "refer to" in first_paragraph:
                    definition = "ambiguous"
                elif "::::" in first_paragraph:
                    definition = result['text'][2]
                else:
                    definition =  first_paragraph
        except:
            pass
        return definition

    def iterate_by_chunks(self, chunksize=1, start_from=0, query={}, projection={}):
       print("Iterating by chunks...")
       print("Total number of documents: ", self.collection.find(query).count())
       chunks = range(start_from, self.collection.find(query).count(), int(chunksize))
       num_chunks = len(chunks)
       for i in range(1,num_chunks+1):
          if i < num_chunks:
              yield self.collection.find(query, projection=projection)[chunks[i-1]:chunks[i]]
          else:
              yield self.collection.find(query, projection=projection)[chunks[i-1]:chunks.stop]