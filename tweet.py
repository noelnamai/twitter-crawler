#!/usr/bin/env python

import re
import logging
import mysql.connector as mysql

from os import path
from datetime import datetime
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

class Tweet(object):

    #class attributes
    tweet_id = None
    created_at = None
    text = None
    retweeted_status = None
    symbols = list()

    logging.basicConfig(
        level = logging.INFO,
        datefmt = "%Y-%m-%d %H:%M:%S",
        format = "%(asctime)s %(levelname)s: %(message)s"
        )

    def __init__(self, status):
        self.tweet_id = status["id"]
        self.created_at = datetime.strptime(status["created_at"], "%a %b %d %H:%M:%S %z %Y")
        self.text = status["text"].replace("\r", "").replace("\n", "")
        self.symbols = [item["text"].upper() for item in status["entities"]["symbols"]]
        self.retweeted_status = status["retweeted_status"] if "retweeted_status" in status else None

    def save_tweet(self, mydb):
        #save processed tweet
        cursor = mydb.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS twitter")
        cursor.execute("USE twitter")
        cursor.execute("CREATE TABLE IF NOT EXISTS tweets (tweet_id VARCHAR(255) PRIMARY KEY, created_at DATE, text VARCHAR(255), symbols VARCHAR(255))")

        if self.retweeted_status:
            pass
        else:
            try:
                sql = "INSERT INTO tweets (tweet_id, created_at, text, symbols) VALUES (%s, %s, %s, %s)"
                values = (self.tweet_id, self.created_at, self.text, ",".join(self.symbols))
                cursor.execute(sql, values)
            except mysql.Error as error:
                if error.errno == mysql.errorcode.ER_DUP_ENTRY:
                    logging.info(error)
                else:
                    raise
        cursor.close()

    def save_to_graph(self, tweet, mydb, search_term):
        #save processed tweet
        cursor = mydb.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS twitter")
        cursor.execute("USE twitter")
        cursor.execute("CREATE TABLE IF NOT EXISTS graph (id INT AUTO_INCREMENT PRIMARY KEY, tweet_id VARCHAR(255), created_at DATETIME, source VARCHAR(255), target VARCHAR(255))")

        if tweet.retweeted_status:
            pass
        else:
            for symbol in tweet.symbols:
                source = re.sub("[^a-zA-Z]+", "", search_term).upper()
                target = symbol.upper()
                if source != target:
                    sql = "INSERT INTO graph (tweet_id, created_at, source, target) VALUES (%s, %s, %s, %s)"
                    values = (self.tweet_id, self.created_at, source, target)
                    cursor.execute(sql, values)
        cursor.close()
