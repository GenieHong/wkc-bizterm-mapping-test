#!/usr/bin/env python3
__author__ = "Kiyeon Jeon"
__copyright__ = 'Copyright 2023, Watson Knowledge Catalog'
__date__ = "02/16/2023"
__version__ = "1.0"
__email__ = "kiyeon.jeon@ibm.com"


import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import json
import pandas as pd
import time
from abc import *


class WatsonKnowledgeCatalog(metaclass=ABCMeta):
    def __init__(self, cpd_cluster_host):
        self.cpd_cluster_host = cpd_cluster_host
        self.token = None
        self.metadata = {
            "catalog2id":{},
            "category2id":{},
        }
    @abstractmethod
    def get_token(self):
        pass

    def get_catalog_id(self, catalog_name):
        if catalog_name in self.metadata['catalog2id'].keys():
            return self.metadata['catalog2id'][catalog_name]
        s = requests.session()
        headers = {
            'Content-Type': "application/json",
            'Authorization': "Bearer "+self.token
        }
        try:
            r = s.get(
                f"{self.cpd_cluster_host}/v2/catalogs", 
                verify=False, 
                headers=headers
            )
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)
        s.close()
        catalogs = json.loads(r.text)['catalogs']

        catalog_id = None
        for catalog in catalogs:
            if catalog['entity']['name'] == catalog_name:
                catalog_id = catalog['metadata']['guid']
                self.metadata['catalog2id'][catalog_name] = catalog_id
                break
        if catalog_id is None:
            print(f"The provided catalog name ({catalog_name}) does not exist!")
        
        return catalog_id
    
    def get_category_id(self, category_path):
        if category_path in self.metadata['category2id'].keys():
            return self.metadata['category2id'][category_path]
        s = requests.session()
        headers = {
            'Content-Type': "application/json",
            'Authorization': "Bearer "+self.token,
            'Cache-Control': "no-cache",
            'Connection': "keep-alive"
        }
        payload = {
            "_source": ["artifact_id","metadata.name","categories"],
            "query": {
                "bool": {
                    "must":[
                        {"match": {"metadata.name":category_path}},
                        {"match": {"metadata.artifact_type": "category"}}
                    ]

                }
            }
        }
        try:
            r = s.post(
                f"{self.cpd_cluster_host}/v3/search",
                verify=False,
                json=payload,
                headers=headers
            )
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)
        s.close()
        rows = json.loads(r.text)['rows']

        category_hierarchy = [each.strip() for each in category_path.split('>>')]
        category_name= category_hierarchy[-1]
        is_root = True if len(category_hierarchy)==1 else False
        category_parent_name = category_hierarchy[-2] if not is_root else None

        category_id = None
        for row in rows:
            if row['metadata']['name']== category_name:
                if is_root or (not is_root and row["categories"]["primary_category_name"]==category_parent_name):
                    category_id = row["artifact_id"]
                    self.metadata['category2id'][category_path] = category_id
                    break
        if category_id is None:
            print(f"The provided catalog name ({category_path}) does not exist!")
        return category_id
    
    def get_asset_id(self, asset_name, catalog_name):
        catalog_id = self.get_catalog_id(catalog_name)
        if catalog_id is None:
            return None
        s = requests.session()
        search_body={
            "query": f"asset.name:{asset_name}"
        }
        headers = {
            'Content-Type': "application/json",
            'Authorization': "Bearer "+self.token
        }
        try:
            r = s.post(
                f"{self.cpd_cluster_host}/v2/asset_types/asset/search?catalog_id="+catalog_id,
                json=search_body,
                verify=False, 
                headers=headers
            )
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)
        s.close()
        
        res = json.loads(r.text)['results']
        if len(res)>0:
            asset_id = json.loads(r.text)['results'][0]['metadata']['asset_id']
        else:
            print(f"The provided asset name ({asset_name}) does not exist in catalog name ({catalog_name})!")
            asset_id = None
        return asset_id
    def get_asset_info(self, asset_name, catalog_name):
        catalog_id = self.get_catalog_id(catalog_name)
        asset_id = self.get_asset_id(asset_name, catalog_name)
        
        s = requests.session()
        headers = {
            'Content-Type': "application/json",
            'Authorization': "Bearer "+self.token
        }
        try:
            r = s.get(
                f"{self.cpd_cluster_host}/v2/assets/{asset_id}?catalog_id={catalog_id}", 
                verify=False, 
                headers=headers
            )
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)
        s.close()
        r_json = json.loads(r.text)
        print(json.dumps(r_json, indent=4))

    def create_attribute(self, asset_name, catalog_name):
        catalog_id = self.get_catalog_id(catalog_name)
        asset_id = self.get_asset_id(asset_name, catalog_name)
        
        s = requests.session()
        headers = {
            'Content-Type': "application/json",
            'Authorization': "Bearer "+self.token
        }
        payload = {
            "name": "column_info",
            "entity":{
            }
        }
        try: 
            r=s.post(
                f"{self.cpd_cluster_host}/v2/assets/{asset_id}/attributes?catalog_id={catalog_id}",
                json=payload,
                headers=headers,
                verify=False
            )
        except requests.exceptions.RequestException as e:
            print('Fail to create attribute')
            raise SystemExit(e)
        s.close()
    def get_attribute(self, asset_name, catalog_name):
        catalog_id = self.get_catalog_id(catalog_name)
        asset_id = self.get_asset_id(asset_name, catalog_name)
        
        s = requests.session()
        headers = {
            'Content-Type': "application/json",
            'Authorization': "Bearer "+self.token
        }
        try: 
            r=s.get(
                f"{self.cpd_cluster_host}/v2/assets/{asset_id}/attributes/column_info?catalog_id={catalog_id}",
                headers=headers,
                verify=False
            )
        except requests.exceptions.RequestException as e:
            print('Fail to get attribute')
            raise SystemExit(e)
        s.close()
        r_json = json.loads(r.text)
        print(json.dumps(r_json, indent=4))
            
    def delete_attribute(self, asset_name, catalog_name):
        catalog_id = self.get_catalog_id(catalog_name)
        asset_id = self.get_asset_id(asset_name, catalog_name)
        
        s = requests.session()
        headers = {
            'Content-Type': "application/json",
            'Authorization': "Bearer "+self.token
        }
        try: 
            r=s.delete(
                f"{self.cpd_cluster_host}/v2/assets/{asset_id}/attributes/column_info?catalog_id={catalog_id}",
                headers=headers,
                verify=False
            )
        except requests.exceptions.RequestException as e:
            print('Fail to delete attribute')
            raise SystemExit(e)
        s.close()
    def get_bizterm_id(self, bizterm, category_path):
        category_id = self.get_category_id(category_path)
        if category_id is None:
            return None
        s = requests.session()
        headers = {
            'Content-Type': "application/json",
            'Authorization': "Bearer "+self.token,
            'Cache-Control': "no-cache",
            'Connection': "keep-alive"
        }

        payload={
            "size": 300, 
            "from": 0, 
            "_source": [
                "artifact_id",
                "metadata.artifact_type",
                "metadata.name",
                "metadata.description",
                "categories",
                "entity.artifacts"],
            "query": {
                "bool": {
                    "filter": {
                        "bool": {
                            "should": [
                                {"match": {"metadata.name": bizterm}}
                            ],
                            "must_not": {
                                "terms": {
                                    "metadata.artifact_type": ["category"]
                                }
                            }
                        }
                    }
                }
            }
        }
        try:
            r = s.post(
                f"{self.cpd_cluster_host}/v3/search",
                headers=headers,
                json=payload,
                verify=False
            )
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)
        s.close()
        bizterm_id = None
        if len(json.loads(r.text)["rows"])>0:
            for row in json.loads(r.text)["rows"]:
                if row['metadata']['name']==bizterm: 
                    bizterm_id = json.loads(r.text)["rows"][0]["artifact_id"]
                    break
        if bizterm_id is None:
            print(f"The provided business term ({bizterm}) does not exist!")
        return bizterm_id
        
        
        
        
        
    def update_attribute(self, asset_name, catalog_name,column_name, bizterm, category_path):
        catalog_id = self.get_catalog_id(catalog_name)
        asset_id = self.get_asset_id(asset_name, catalog_name)
        bizterm_id = self.get_bizterm_id(bizterm, category_path)
        if None in set([catalog_id, asset_id, bizterm_id]):
            return
        
        s = requests.session()
        headers = {
            'Content-Type': "application/json",
            'Authorization': "Bearer "+self.token
        }
        payload=[
            {
                "op":"add",
                "path":"/"+column_name,
                "value":{
                    "column_terms":[
                        {
                            "term_display_name":bizterm,
                            "term_id":bizterm_id
                        }
                    ]
                }
            }
        ]
        try: 
            r=s.patch(
                f"{self.cpd_cluster_host}/v2/assets/{asset_id}/attributes/column_info?catalog_id={catalog_id}",
                json=payload,
                headers=headers,
                verify=False
            )
        except requests.exceptions.RequestException as e:
            print('Fail to delete attribute')
            raise SystemExit(e)
        s.close()
    
    def map_bizterm(self, map_bizterm_csv='map-bizterm-glossary.csv'):
        df = pd.read_csv(map_bizterm_csv)
        start = time.time()

        df_attribute = df[['Catalog', 'DataAsset']].drop_duplicates(ignore_index=True)
        print(f"1. Creating attribute..")
        print('='*100)
        for idx, row in df_attribute.iterrows():
            print(f"{idx}-{row.DataAsset} of {row.Catalog}..")
            self.create_attribute(row.DataAsset, row.Catalog)
        print('='*100)
        print(f"2. Patching column info attribute into data asset in catalogs..")
        print('='*100)
        for idx, row in df.iterrows():
            print(f"{idx}-{row.BusinessTerm} is mapped to {row.ColumnHeader} in {row.DataAsset} of {row.Catalog}..")
            self.update_attribute(row.DataAsset, row.Catalog, row.ColumnHeader, row.BusinessTerm, row.Category)
        end = time.time()
        elapsed_time = end-start
        print('='*100)
        print(f"it takes {elapsed_time} seconds / ({elapsed_time/len(df)} sec per column)")
        print('='*100)

    def map_bizterm_allatonce(self, map_bizterm_csv='map-bizterm-glossary.csv'):
        s = requests.session()
        headers = {
            'Content-Type': "application/json",
            'Authorization': "Bearer "+self.token
        }
        
        df = pd.read_csv(map_bizterm_csv)
        start = time.time()
        for (catalog_name, asset_name), rows in df.groupby(['Catalog','DataAsset']):
            catalog_id = self.get_catalog_id(catalog_name)
            asset_id = self.get_asset_id(asset_name, catalog_name)
            payload = dict()
            payload['name'] = "column_info"
            payload['entity'] = dict()
            for idx, row in rows.iterrows():
                payload['entity'][row.ColumnHeader]=dict()
                bizterm_id = self.get_bizterm_id(row.BusinessTerm, row.Category)
                payload['entity'][row.ColumnHeader]['column_terms'] = [
                    {
                        'term_display_name': row.BusinessTerm, 'term_id': bizterm_id
                    }
                ]
            print(f"Creating and patching attribute on {asset_name} of {catalog_name}..")
            try: 
                r=s.post(
                    f"{self.cpd_cluster_host}/v2/assets/{asset_id}/attributes?catalog_id={catalog_id}",
                    json=payload,
                    headers=headers,
                    verify=False
                )
            except requests.exceptions.RequestException as e:
                print('Fail to create attribute')
                raise SystemExit(e)
        s.close()
        end = time.time()
        elapsed_time = end - start
        print('='*100)
        print(f"it takes {elapsed_time} seconds / ({elapsed_time/len(df)} sec per column)")
        

class MapTermsJSON(WatsonKnowledgeCatalog):
    def __init__(self, cpd_cluster_host, info_json):
        super().__init__(cpd_cluster_host)
        self.token = self.get_token(info_json)
    
                
    def get_token(self, info_json):
        s = requests.session()
        info = json.load(open(info_json))
        headers = {
            'cache-control': 'no-cache',
            'content-type': 'application/json'
        }

        payload = json.dumps({"username":info["username"], "password":info["password"]})
        try:
            r = s.post(f'{self.cpd_cluster_host}/icp4d-api/v1/authorize', headers=headers, data=payload, verify=False)
            token=json.loads(r.text)['token']
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            raise SystemExit(e)
        s.close()
        return token
    
        
class MapTermsInput(WatsonKnowledgeCatalog):
    def __init__(self, cpd_cluster_host):
        super().__init__(cpd_cluster_host)
        self.token = self.get_token()
    def get_token(self):
        def user_input():
            from getpass import getpass
            username = input("1) ID를 입력하세요:")
            password = getpass("2) 비밀번호: ")
            return username, password
        username, password = user_input()

        s = requests.session()
        headers = {
            'cache-control': 'no-cache',
            'content-type': 'application/json'
        }

        payload = json.dumps({"username":username, "password":password})
        try:
            r = s.post(f'{self.cpd_cluster_host}/icp4d-api/v1/authorize', headers=headers, data=payload, verify=False)
            token=json.loads(r.text)['token']
        except requests.exceptions.RequestException as e:  
            raise SystemExit(e)
        s.close()
        return token
    

class MapTermsJob(WatsonKnowledgeCatalog):
    def __init__(self, cpd_cluster_host, username, password, filename):
        super().__init__(cpd_cluster_host)
        self.token = self.get_token(username, pasword)
    def get_token(self, username, password):
        s = requests.session()
        headers = {
            'cache-control': 'no-cache',
            'content-type': 'application/json'
        }

        payload = json.dumps({"username":username, "password":password})
        try:
            r = s.post(f'{self.cpd_cluster_host}/icp4d-api/v1/authorize', headers=headers, data=payload, verify=False)
            token=json.loads(r.text)['token']
        except requests.exceptions.RequestException as e:  
            raise SystemExit(e)
        s.close()
        return token