import datetime as dt
import pandas as pd
import pymongo
import requests
import string

from config import API_KEY
from countries import countries, country_codes

from rake_nltk import Rake, Metric
from py_translator import Translator

#connect to mongodb
conn = 'mongodb://localhost:27017/top_headlines'
client = pymongo.MongoClient(conn)
# Declare the database
db = client["top_headlines"]
# Declare the collection
collection = db["countries_data"]

#get data
data = collection.find()

#get alphabet list
alphabet = list(string.ascii_lowercase)

#set empty list for dates
dates = []
#find latest date
for article in data[0]["articles"]:
    dates.append(article["date"])
latestDate = max(dates)
print(f"Latest Date in Database: {latestDate}")

#find today's date
today = dt.datetime.strftime(dt.date.today(), "%Y-%m-%d")

#initialize countryWords dict and allWords string
countryWords = {}
allWords = ''

#if ran create db today#otherwise comment this out #same day or comment out
latestDate = '2019-01-01'

#if latest date is before today,
if latestDate < today:
    #for length of country_code list
    for i in range(len(country_codes)):
        #visit news api
        query_url = f"https://newsapi.org/v2/top-headlines?country={country_codes[i]}&apiKey={API_KEY}"
        #get response
        response = requests.get(query_url).json()

        #initialize countryWords dict and date list
        countryWords[countries[i]] = ''
        date_list = []
        
        #for each article
        for article in response["articles"]:
            #set date and title
            date = article["publishedAt"][:10]
            title = article["title"].split(" - ")[0]
            #add date to date list
            date_list.append(date)

            #construct article dictionary
            articleDict = {"source": article["source"]["name"], 
                        "title": title, 
                        "url": article["url"], 
                        "date": date}
            #set the collection
            collection = db["countries_data"]
            #add article dict to countries data db

            #comment out this line if running same day as createDB
            collection.update_one({"country": countries[i]}, {"$push": {"articles": articleDict}})
            
            #add title text to countryWords dict
            countryWords[countries[i]] = countryWords[countries[i]] + title + ' '
            ####end of articles loop
            ########################

        #untranslated string of article titles
        untranslated = countryWords[countries[i]]
        # print(untranslated)

        #try to translate
        try:
            translated = Translator().translate(text=untranslated, dest='en').text
            # print(translated)
            print('translated')

            #set the collection
            collection = db["countries_words"]
            #add translated string to countries_words collection
            collection.update_one({"country": countries[i]}, {"$set": {max(date_list): translated}}, upsert=True)
        
        except:
            print(f"{countries[i]}: failed to translate")
            print(untranslated)
            
        #add translated string to string of all titles
        allWords = allWords + translated + ' '

        #unRaked word list
        
        collectionBlob = db["countries_wordblob"]
        zz = collectionBlob.find_one({"country": countries[i]})
        #print(type(zz))
        splitWords = translated.split()
        if splitWords is None:
            print("alerttttt EMPLY WORD LIST")
       # print(splitWords)
        if zz is not None:
            print(countries[i] + " country exists")
            #print(zz)
            #print(zz['words'])
            if zz["words"] != None:
                print("WORDS TO ADD FROM DATABASE:")
                print(zz["words"])
                print("NEW WORDS TO ADD:")
                print(splitWords)
                newWordGroup = zz["words"] + splitWords
                print('checking comparison for dups')
                if (zz['words'][-len(splitWords):] == splitWords):
                    print('dubs found, aborting add')
                    continue
                print("NEW JOINED LIST:")
                print(newWordGroup)
            else:
                print("NO PREVIOUS DATA")
                newWordGroup = splitWords
                print(newWordGroup)

        else:
            print(countries[i] + "was null")
            newWordGroup = splitWords
        print("------------------------------------------------")
        #update countries_keywords collection with keywords_dict
        collectionBlob.update_one({"country": countries[i]}, {'$set': {"words": newWordGroup }}, upsert=True)

        #set rake settings
        r = Rake(max_length=2, ranking_metric=Metric.WORD_DEGREE)
        #extract keywords with scores from translated string
        r.extract_keywords_from_text(translated)
        phrasesScores = r.get_ranked_phrases_with_scores()
        # print(phrasesScores)
        
        #initialize keywords dict
        keywords_dict = {"keywords": {}}
        #for index and keyword-score pair,
        for j, pair in enumerate(phrasesScores):

            #format pair into score and word
            pair = list(pair)
            score = pair[0]
            word = pair[1]

            #set special character list
            special_chars = ["-", "'", ":", ".", "’", "‘", "\\", "(", ")", "”", "“", "!", "?", "【", "】", "\"","🔥"]
            # print(j, word)
            #if any special characters in word or word less than 2 characters,
            if any(x in word for x in special_chars) or len(word) < 2:
                # print(j)
                #remove word-score pair
                phrasesScores.pop(j)

            else:
                #for character in word
                for char in word:
                    #if any letter matches character,
                    if any(letter == char for letter in alphabet):
                        #word has letters, exit loop
                        hasLetters = True
                        break
                    else:
                        hasLetters = False

                #if word has letters, 
                if hasLetters == True:
                    #add word-score pair to keywords_dict
                    keywords_dict["keywords"][word] = score

                #if word has no letters,
                else:
                    #remove word-score pair
                    # print(word + " has no letters")
                    phrasesScores.pop(j)

        #set collection
        collection = db["countries_keywords"]
        #update countries_keywords collection with keywords_dict
        collection.update_one({"country": countries[i]}, {"$set": {"keywords": keywords_dict["keywords"]}}, upsert=True)
        ###end of country loop
        ######################

    ##add global string of allWords to countries_words
    #set collection
    collection = db["countries_words"]
    #update countries_words collection with global data of allWords
    collection.update_one({"country": "Global"}, {"$set": {today: allWords}}, upsert=True)
    
    ##extract keywords from allWords
    #set rake settings
    r = Rake(max_length=2, ranking_metric=Metric.WORD_DEGREE)
    #extrake keywords with scores from allWords
    r.extract_keywords_from_text(allWords)
    phrasesScores = r.get_ranked_phrases_with_scores()
    # print(phrasesScores)

    #initialize keywords dict
    keywords_dict = {"keywords": {}}
    #for index and keyword-score pair,
    for j, pair in enumerate(phrasesScores):

        #format pair into score and word
        pair = list(pair)
        score = pair[0]
        word = pair[1]

        #set special character list
        special_chars = ["-", "'", ":", ".", "’", "‘", "\\", "(", ")", "”", "“", "!", "?", "【", "】", "\""]
        # print(j, word)
        #if any special characters in word or word less than 2 characters,
        if any(x in word for x in special_chars) or len(word) < 2:
            # print(j)
            #remove word-score pair
            phrasesScores.pop(j)

        else:
            #for character in word
            for char in word:
                #if any letter matches charcter,
                if any(letter == char for letter in alphabet):
                    #word has letters, break loop
                    hasLetters = True
                    break
                else:
                    hasLetters = False

            #if word has letters, 
            if hasLetters == True:
                #add word-score pair to keywords_dict
                keywords_dict["keywords"][word] = score

            #if word has no letters,
            else:
                #remove word-score pair
                # print(word + " has no letters")
                phrasesScores.pop(j)

    #set collection
    collection = db["countries_keywords"]
    #update countries_keywords collection with global keywords_dict
    collection.update_one({"country":"Global"}, {"$set": {"keywords": keywords_dict["keywords"]}}, upsert=True)
    print("Database updated.")
else:
    print("Database is up to date.")