import os

import pymongo
from bson.json_util import dumps, loads
from bson.objectid import ObjectId

from splinter import Browser
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait # available since 2.4.0
from selenium.webdriver.support import expected_conditions as EC # available since 2.26.0
from selenium.common.exceptions import TimeoutException

import pandas as pd

import re
from pprint import pprint
from datetime import datetime as dt
import time
import isodate

import sys
import pandas as pd
import json
import os
from pprint import pprint
import random

# grab full list of recipe urls

conn = 'mongodb://localhost:27017'
client = pymongo.MongoClient(conn)
mongoDb = client.serious_eats_urls

collection = mongoDb.se_urls
url_dict = collection.find_one({}, {'_id':False})

## use if url_dict is created from scratch
mongoDb = client.serious_eats_recipes
for topic, topic_list in url_dict.items():
    print(f'topic: {topic}')
    for topic_dict in topic_list:
        collection = mongoDb[topic_dict['topic']]
        collection.create_index('recipe_url', unique=True)
        for i, recipe in enumerate(topic_dict['recipes']):
            url = recipe['recipe_url']
            print(f"{topic}: {i} of {len(topic_dict['recipes'])} => {url}")
            cfTitle = re.sub(r"\s|/|\.|,|'|-|\?|\||<|>|\\|\*|:", '_', recipe['recipe_title'])
            cfTitle = re.sub(r'"', '', cfTitle)
            cfTitle = re.sub(r'__', '_', cfTitle)
            if cfTitle[0:1] == "_":
                cfTitle = cfTitle[1:]
            if cfTitle[-1:] == "_":
                cfTitle = cfTitle[:-1]
            cfTitle = cfTitle[:32]
            print(f"cfTitle: {cfTitle}")
            cacheFilePath = f"/home/shortpoet/Sources/serious_eats_html_caches/{cfTitle}.txt"
            print(f"cfp: {cacheFilePath}")
            
            if os.path.isfile(cacheFilePath):
                with open(cacheFilePath, encoding='utf-8') as cacheFile:
                    html = cacheFile.read()
            else:
                driver = webdriver.Chrome()
                driver.get(url)
                html = driver.page_source          
                with open(cacheFilePath, 'w', encoding='utf-8') as cacheFile:
                    cacheFile.write(html)
            se_soup = bs(html, 'html.parser')
            script_divs = se_soup.find_all('script', {'type': 'application/ld+json'})
            category_trees = []
            for index, div in enumerate(script_divs):
                try:
                    
                    j = json.loads(div.text, strict=False)

                    recipe.setdefault('category_trees', [])
                    recipe.setdefault('recipe', {})

                    if j['@type'] == 'BreadcrumbList':
                        category_tree = []
                        for item in j['itemListElement']:
                            category_tree.append(item['item']['name'])
                        category_trees.append(category_tree)

                    if j['@type'] == 'Recipe':
                        
                        try:
                            rating_count = j['aggregateRating']['ratingCount']
                        except:
                            rating_count = False
                        try:
                            rating_value = j['aggregateRating']['ratingValue']
                        except:
                            rating_value = False
                        try:
                            author = j['author']['name']
                        except:
                            author = False
                        try:
                            job_title = j['author']['jobTitle']
                        except:
                            job_title = False
                        try:
                            description = j['description']
                        except:
                            description = False
                        try:
                            keywords = j['keywords']
                        except:
                            keywords = False
                        try: 
                            name = j['name']
                        except:
                            name = False
                        try:
                            categories = j['recipeCategory']
                        except:
                            categories = False
                        try:
                            cuisine = j['recipeCuisine']
                        except:
                            cuisine = False
                        try:
                            ingredients = j['recipeIngredient']
                        except:
                            ingredients = False
                        try:   
                            steps = {}
                            for i, step in enumerate(j['recipeInstructions']):
                                this = 'step_' + str(i+1)
                                steps[this] = step['text']
                        except:
                            steps = False
                        try:
                            recipe_yield = j['recipeYield']
                        except:
                            recipe_yield = False
                        try:
                            time = str(isodate.parse_duration(j['totalTime']).total_seconds()/60)
                        except:
                            time = False
                        recipe['recipe'] = {
                        
                            'name': name, 'rating_count': rating_count, 'rating_value': rating_value, 'author': author,
                            'job_title': job_title, 'description': description, 'keywords': keywords, 'categories': categories,
                            'cuisine': cuisine, 'ingredients': ingredients, 'steps': steps, 'recipe_yield': recipe_yield, 'time':time
                        }
                except:
                    print(f"json error on:{url} - script_div{index}")
                    continue
            this_recipe = {
                'topic': topic_dict['topic'], 'source': 'serious_eats', 
                'recipe_title': recipe['recipe_title'], 'recipe_url': recipe['recipe_url'], 
                'category_trees': recipe['category_trees'], 'recipe': recipe['recipe'], 
                'uploaded': dt.now()
            }
            try:
                collection.insert_one(this_recipe)
            except pymongo.errors.DuplicateKeyError:
                continue
