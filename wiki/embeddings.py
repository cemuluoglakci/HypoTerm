import pandas as pd
import logging

from sentence_transformers import SentenceTransformer
from pymilvus import connections
from pymilvus import CollectionSchema, FieldSchema, DataType
from pymilvus import Collection
from pymilvus import utility
from pymilvus.exceptions import MilvusException

import torch

from wiki.search import WikiSearcher

PARTITION_SIZE = 100000


class Embeddings():
    def __init__(self, settings) -> None:
        self.settings = settings
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_name = "sentence-transformers/msmarco-distilbert-base-tas-b"

        self.model = SentenceTransformer(self.model_name).to(device)

        connections.connect(
            alias=settings.milvus_alias,
            host=settings.milvus_host,
            port=settings.milvus_port,
        )
        Id = FieldSchema(
            name="id",
            dtype=DataType.INT64,
            is_primary=True,
            max_length=50,
        )
        title = FieldSchema(
            name="title",
            dtype=DataType.VARCHAR,
            max_length=1000,
        )
        text = FieldSchema(
            name="text",
            dtype=DataType.VARCHAR,
            max_length=10000,
        )
        embeddings = FieldSchema(
            name="embeddings",
            dtype=DataType.FLOAT_VECTOR,
            dim=768
        )
        self.title_schema = CollectionSchema(
            fields=[Id, title, embeddings],
            description=self.model_name
        )
        self.text_schema = CollectionSchema(
            fields=[Id, title, text, embeddings],
            description=self.model_name
        )

    def create_collection(self, collection_name, schema):
        if not utility.has_collection(collection_name):
            collection = Collection(
                name=collection_name,
                schema=schema,
                using='default',
                shards_num=2
            )
            index_params = {
                "metric_type": "L2",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024}
            }
            collection.create_index(
                field_name="embeddings",
                index_params=index_params
            )
            logging.info(f"Collection {collection_name} created")
            return collection
        else:
            logging.warning("Collection already exists")

    def get_collection(self, collection_name):
        if utility.has_collection(collection_name):
            return Collection(name=collection_name)
        else:
            logging.warning("Collection does not exist")

    def delete_collection(self, collection_name):
        if utility.has_collection(collection_name):
            utility.drop_collection(collection_name)
        else:
            logging.warning("Collection does not exist")

    def vector_search(self, collection_name, search_text: str, partition_names=None):

        search_data = [self.model.encode(search_text)]
        output_fields = ["title"]

        search_collection = Collection(name=collection_name)
        if collection_name == "wiki_text":
            output_fields.append("text")

        try:
            search_collection.load(partition_names=partition_names)
        except MilvusException:
            logging.warning("Reloading Collection...")
            search_collection.release()
            search_collection.load(partition_names=partition_names)

        search_collection.load(partition_names=partition_names)
        search_params = {"metric_type": "L2", "params": {"nprobe": 100}}
        results = search_collection.search(
            data=search_data,
            anns_field="embeddings",
            param=search_params,
            limit=10,
            expr=None,
            consistency_level="Strong",
            output_fields=output_fields
        )

        search_collection.release()
        return results


class EmbeddingIterator(Embeddings):
    def __init__(self, settings) -> None:
        super().__init__(settings)
        self.ITERATOR_CHUNK_SIZE = 500
        self.iterator_start_from = 0
        self.wikiSearcher = WikiSearcher()
        self.projection = {"wikipedia_title": 1}
        self.columns = ['id', 'title']

    def set_collection(self, collection_name, schema):
        self.collection_name = collection_name
        self.collection = self.get_collection(self.collection_name)
        if not self.collection:
            self.create_collection(self.collection_name, schema)
            self.collection = self.get_collection(self.collection_name)
            self.partition = 1
            self.collection.create_partition(
                partition_name=str(self.partition))

    def reset_iterator(self, iterator_start_from=0):
        self.iterator_start_from = iterator_start_from
        self.chunk_iterator = self.wikiSearcher.iterate_by_chunks(
            chunksize=self.ITERATOR_CHUNK_SIZE,
            start_from=self.iterator_start_from, query={},
            projection=self.projection)
        self.partition = (self.iterator_start_from//PARTITION_SIZE) + 1

    def insert(self):
        logging.info("Starting from: ", self.iterator_start_from)
        logging.info("Chunk size: ", self.ITERATOR_CHUNK_SIZE)

        chunk_n = 0
        total_docs = 0
        for chunk in self.chunk_iterator:
            chunk_n += 1
            chunk_len = 0

            if self.iterator_start_from > (self.partition * PARTITION_SIZE):
                self.partition += 1
                self.collection.create_partition(
                    partition_name=str(self.partition))
                logging.info(f"***\nPartition: {self.partition}\n***")

            data = []
            for doc in chunk:
                chunk_len += 1
                total_docs += 1

                self.append_data(data, doc)

            df = pd.DataFrame(data, columns=self.columns)
            embeddings = self.model.encode(df[self.columns[-1]].tolist())
            df['embeddings'] = embeddings.tolist()
            self.collection.insert(df, partition_name=str(self.partition))

            self.iterator_start_from += self.ITERATOR_CHUNK_SIZE

            logging.info(f'chunk #: {chunk_n}, chunk_len: {chunk_len}')
        logging.info("total docs iterated: ", total_docs)

    def append_data(self, data, doc):
        None


class EmbeddingTextIterator(EmbeddingIterator):
    def __init__(self, settings) -> None:
        super().__init__(settings)
        self.set_collection("wiki_text", self.text_schema)
        self.projection["text"] = 1
        self.reset_iterator()
        self.columns.append("text")

    def append_data(self, data, doc):
        for paragraph in doc['text'][1:]:
            if ("::::" in paragraph) or ("may refer to:" in paragraph) or (len(paragraph) < 20):
                continue
            data.append(
                [int(doc['_id']), doc['wikipedia_title'], paragraph[:9000]])

    def insert_discard(self):
        if self.iterator_start_from > 0:
            self.reset_iterator(self.iterator_start_from)
        logging.info("Starting from: ", self.iterator_start_from)
        logging.info("Chunk size: ", self.ITERATOR_CHUNK_SIZE)

        chunk_n = 0
        total_docs = 0
        for chunk in self.chunk_iterator:
            chunk_n += 1
            chunk_len = 0

            data = []
            for doc in chunk:
                chunk_len += 1
                total_docs += 1

                for paragraph in doc['text'][1:]:
                    if "::::" in paragraph:
                        continue
                    data.append(
                        [int(doc['_id']), doc['wikipedia_title'], paragraph[:9999]])
            df = pd.DataFrame(data, columns=self.columns)
            embeddings = self.model.encode(df[self.columns[-1]].tolist())
            df['embeddings'] = embeddings.tolist()
            self.collection.insert(df[["id", "title", "text", "embeddings"]])

            self.iterator_start_from += self.ITERATOR_CHUNK_SIZE

            logging.info(f'chunk #: {chunk_n}, chunk_len: {chunk_len}')
        logging.info("total docs iterated: ", total_docs)


class EmbeddingTitleIterator(EmbeddingIterator):
    def __init__(self, settings) -> None:
        super().__init__(settings)
        self.set_collection("wiki_title", self.title_schema)
        self.ITERATOR_CHUNK_SIZE = 10000
        self.reset_iterator()

    def append_data(self, data, doc):
        data.append([int(doc['_id']), doc['wikipedia_title']])