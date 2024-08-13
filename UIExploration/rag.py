import xml.etree.ElementTree as ET
import pandas as pd
import openai
import qdrant_client
from qdrant_client.http import models
import numpy as np
import os
import pickle
import json
from pathlib import  Path
from hierarchy import  SemanticHierarchy
import hashlib
import tiktoken

class RAG:

    def __init__(self,qdrant_path='data/qdrant_db', embeddings_dir='data/embeddings'):
        self.embeddings_dir = embeddings_dir
        self.qdrant_path = qdrant_path
        self.collection_name = 'android_gui_embeddings'
        with open('api.key', 'r') as f:
            api_key = f.read()
        openai.api_key = api_key

    def initialze(self, csv_file):
        self.csv_file = csv_file


        # Create directory to save embeddings
        os.makedirs(self.embeddings_dir, exist_ok=True)

        # Initialize Qdrant client
        self.client = qdrant_client.QdrantClient(path=self.qdrant_path)

        # Create collection in Qdrant
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
            # Adjust vector size based on model used
        )


        # Load the CSV file containing XML paths
        xml_paths = pd.read_csv(self.csv_file)['xml_path'].tolist()

        # Collect embeddings and payloads
        vectors = []
        payloads = []
        for xml_path in xml_paths:
            embedding, payload = self.process_and_collect_embeddings(xml_path)
            if embedding is not None:
                vectors.append(embedding)
                payloads.append(payload)

        # Debugging: Print the number of vectors and payloads
        print(f"Uploading {len(vectors)} embeddings to Qdrant.")

        # Upload all embeddings in a batch
        self.client.upload_collection(
            collection_name=self.collection_name,
            vectors=vectors,
            payload=payloads
        )
        print("All embeddings have been processed and saved to Qdrant.")

    def parse_xml(self,root:ET.Element):

        # root = tree.getroot()
        allowed_attributes = ['text', 'class', 'resource-id', 'content-desc', 'clickable']

        elements = []
        for elem in root.iter():
            attributes = {k: v for k, v in elem.attrib.items() if k in allowed_attributes}
            element_str = elem.tag
            if attributes:
                attribute_str = ' '.join([f"{k}={v}" for k, v in attributes.items()])
                element_str += ' ' + attribute_str
            elements.append(element_str)

        return ' '.join(elements)

    def get_embeddings(self, text):
        response = openai.Embedding.create(
            model="text-embedding-ada-002",
            input=text
        )
        return np.array(response['data'][0]['embedding'])

    def save_embeddings(self, file_path, embeddings):
        with open(file_path, 'wb') as f:
            pickle.dump(embeddings, f)

    def load_embedding(self, file_path):
        with open(file_path, 'rb') as f:
            return pickle.load(f)

    def process_and_collect_embeddings(self, xml_path):
        pkg_name = xml_path.split('/')[-2]
        index = xml_path.split('/')[-1][:-4]
        embedding_file = os.path.join(self.embeddings_dir, pkg_name + '-' + index + '.pkl')
        if Path(embedding_file).exists():
            return self.load_embedding(embedding_file), {"path": xml_path}
        xml_text = self.parse_xml(ET.parse(xml_path))
        embedding = self.get_embeddings(xml_text)

        self.save_embeddings(embedding_file, embedding)
        return embedding, {"path": xml_path}

    def SHA1(self,msg: str) -> str:
        return hashlib.sha1(msg.encode()).hexdigest()
    def query_string(self,pkg_name,xml_string):
        sha=self.SHA1(xml_string)
        embedding_file = os.path.join(self.embeddings_dir, pkg_name+'-'+sha+ '.pkl')
        if Path(embedding_file).exists():
            embedding=self.load_embedding(embedding_file)
        else:
            xml_text = self.parse_xml(ET.fromstring(xml_string))

            try:
                embedding = self.get_embeddings(xml_text)
            except:
                xml_text = xml_text[:8192]
                embedding = self.get_embeddings(xml_text)
            self.save_embeddings(embedding_file,embedding)

        # Initialize Qdrant client
        if not hasattr(self, 'client') or self.client is None:
            self.client = qdrant_client.QdrantClient(path=self.qdrant_path)

        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            limit=3  # Adjust the limit as needed
        )
        search_results = [hit.payload for hit in hits]
        return search_results
    def query_file(self, xml_file):
        pkg_name=xml_file.split('/')[-2]
        index=xml_file.split('/')[-1][:-4]
        embedding_file = os.path.join(self.embeddings_dir, pkg_name+'-'+index+ '.pkl')
        if Path(embedding_file).exists():
            embedding=self.load_embedding(embedding_file)
        else:
            xml_text = self.parse_xml(xml_file)
            embedding = self.get_embeddings(xml_text)
            self.save_embeddings(embedding_file,embedding)

        # Initialize Qdrant client
        if not hasattr(self, 'client') or self.client is None:
            self.client = qdrant_client.QdrantClient(path=self.qdrant_path)

        hits = self.client.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            limit=3  # Adjust the limit as needed
        )
        search_results = [hit.payload for hit in hits]
        return search_results
    def match_events(self,events,ad_element):
        for idx,event in enumerate(events):

            attrib=event.widget.attrib

            #1. ad_element inside a event
            def parse_bounds(bounds_str):
                bounds_list = bounds_str.replace('][', ',').strip('[]').split(',')
                return list(map(int, bounds_list))

            def is_inside(bounds1, bounds2):
                return bounds1[0] >= bounds2[0] and bounds1[1] >= bounds2[1] and bounds1[2] <= bounds2[2] and bounds1[
                    3] <= bounds2[3]

            event_bound=parse_bounds(attrib.get('bounds'))
            ad_bound=parse_bounds(ad_element.get('bounds'))
            if is_inside(ad_bound,event_bound):
                return idx


            # 2. ad_element resource-id equals to event
            event_resourceId = attrib.get('resource-id')
            ad_resourceId=ad_element.get('resource-id')
            if ad_resourceId==event_resourceId:
                return idx

            # 3. ad_element text or description equals to event
            event_cdesc=attrib.get('content-desc')
            ad_cdesc=ad_element.get('content-desc')
            if event_cdesc==ad_cdesc!='':
                return idx

            event_cdesc=attrib.get('text')
            ad_cdesc=ad_element.get('text')
            if event_cdesc==ad_cdesc!='':
                return idx
        # if none of the event matches, meaning the event is filtered in the SemanticHiearchy
        return -1
    def read_payload(self,payloads):
        rag_prompt='Below are the 3 most similar UIs of current UI. \n'
        for idx,payload in enumerate(payloads):

            # In the xml (SemanticHierarchy), find the event that specified as an ad widget in meta.json
            path=payload['path']
            with open('/'.join(path.split('/')[:-1])+"/meta.json", 'r') as file:
                meta_data = json.load(file)
            index=int(path.split('/')[-1][:-4])
            ad_element = meta_data[index].get('element')

            pkg_name=path.split('/')[-2]
            with open(path, 'r') as file:
                xml_data = file.read()
            hier = SemanticHierarchy(pkg_name=pkg_name, app_name='', _rawHierarchy=xml_data)
            events=hier.getEvents()
            if len(events) > 30:
                events = events[:30]
            filteredEvents = [(i, e.dump()) for i, e in enumerate(events)]
            elemDesc = [f"index-{i}: {x[1]}" for i, x in enumerate(filteredEvents)]


            ad_index=self.match_events(events,ad_element)
            ad_element_description = f"the View (accessibility information: {ad_element.get('content-desc')}, resourceId: {ad_element.get('resource-id')}, text: {ad_element.get('text')})"
            if ad_index!=-1:
                rag_prompt +=f"In UI-{idx}:\n we have " +'\n'.join(elemDesc) +f"\n and in thi UI index-{ad_index} {ad_element_description} is the chosen widget with advertising content\n"
            else:
                rag_prompt += f"In UI-{idx}:\n we have " + '\n'.join(elemDesc) + f"\n and in this UI {ad_element_description} is the chosen widget with advertising content\n"
        return rag_prompt
            # rag_prompt+=f"In previous UI-{idx}: {'\n'.join(filteredEvents)}, and {} is the advertising content"


if __name__=='__main__':

    # Usage
    csv_file = 'data/ad_xml.csv'
    rag = RAG()
    rag.initialze(csv_file)


## below is the code to test the query
#     xml_paths = pd.read_csv(csv_file)['xml_path'].tolist()
#     work=[]
#     for xml_path in xml_paths:
#
#         results = rag.query_file(xml_path)
#         prompt=rag.read_payload(results)
#         print(prompt)

