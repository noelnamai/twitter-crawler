#!/usr/bin/env python3

"""
Usage:
    crawler.py --search-term <SEARCH> --sqs-queue-url <QUEUE>
    crawler.py (-h | --help)
    crawler.py (-v | --version)

Options:
    -h --help               Show this screen and exit.
    -v --version            Show version and exit.
    --search-term=SEARCH    The term to search Twitter API.
    --sqs-queue-url=QUEUE   The Amazon SQS URL where messages will be sent.
"""

import json
import sys
import time
import traceback
import warnings
from datetime import date

import jsonpickle
import mysql.connector
import requests
import requests_oauthlib
from docopt import docopt
from mysql.connector import pooling

import credentials
import tweet as twtr
import util

if sys.version_info < (3, 7):
    raise Exception("Requires atleast Python 3.7.x")

warnings.filterwarnings("ignore", category = FutureWarning)
warnings.filterwarnings("ignore", category = DeprecationWarning)

class Crawler(object):

    def __init__(self, args):
        self.pool        = None
        self.date        = str(date.today())
        self.search_term = args["--search-term"]
        self.sqs_url     = args["--sqs-queue-url"]

    def connect_twitter(self):
        """
        log into the twitter API and return the api object
        """
        try:
            oauth = requests_oauthlib.OAuth1(
                client_key = credentials.api_key,
                client_secret = credentials.api_secret_key,
                resource_owner_key = credentials.access_token_key,
                resource_owner_secret = credentials.access_token_secret
            )
            util.logger.info(f"Connected to Twitter API")
        except:
            util.logger.error(f"Twitter API authentication failed")
        return oauth

    def connect_db(self):
        """
        connect to db
        """
        try:
            self.pool = pooling.MySQLConnectionPool(
                pool_name = "pool",
                pool_size = 30,
                autocommit = True,
                buffered = True,
                host = credentials.host,
                user = credentials.user,
                passwd = credentials.passwd
            )
            db = self.pool.get_connection()
            util.logger.info(f"Connected to MySQL Server {db.get_server_info()} at {db.server_host}:{db.server_port}")
        except mysql.connector.Error as error:
            util.logger.error(error)

    def twitter_stream(self, oauth):
        """
        get twitter stream with search term(s)
        """
        response = requests.post(
            stream = True,
            auth = oauth,
            timeout = 60,
            url = "https://stream.twitter.com/1.1/statuses/filter.json",
            data = {
                "track": self.search_term, 
                "language": "en"
            }
        )

        return response

if __name__ == "__main__":
    args = docopt(__doc__, version='Twitter Crawler Version:1.0')
    client = Crawler(args)
    oauth = client.connect_twitter()
    client.connect_db()
    response = client.twitter_stream(oauth)

    for status in response.iter_lines(chunk_size = 10000):
        if status:
            try:
                status = json.loads(status)
                tweet  = twtr.Tweet(status)
                if tweet.retweeted_status or tweet.text == "":
                    pass
                else:
                    frozen = jsonpickle.encode(tweet.__dict__)
                    thawed = jsonpickle.decode(frozen)
                    util.logger.info(f"{tweet.text}")
                    mydb = client.pool.get_connection()
                    tweet.save_tweet(mydb)
                    tweet.save_to_graph(tweet, mydb, client.search_term)
                    mydb.close()
            except Exception as error:
                if status["limit"]:
                    util.logger.warning(f"{status['limit']['track']}")
                else:
                    print(json.dumps(status, indent = 4, sort_keys = True))
                    traceback.print_exc(file = sys.stdout)
        #break
        #time.sleep(0.1)

    client.pool.close()
    util.logger.info(f"MySQL connection is closed")
