# core/twitter_sentiment.py

import pandas as pd
import vaderSentiment
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import snscrape.modules.twitter as sntwitter

class TwitterSentimentAnalyzer:
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()

    def get_sentiment(self, keyword="BTC", limit=100):
        try:
            tweets = []
            for i, tweet in enumerate(sntwitter.TwitterSearchScraper(keyword).get_items()):
                if i >= limit:
                    break
                tweets.append(tweet.content)

            if not tweets:
                return 0.5

            sentiments = [self.analyzer.polarity_scores(t)['compound'] for t in tweets]
            avg_sentiment = sum(sentiments) / len(sentiments)  # 范围[-1, 1]
            return (avg_sentiment + 1) / 2  # 归一化到[0, 1]
        except Exception as e:
            print(f"Twitter Sentiment Error: {e}")
            return 0.5

if __name__ == "__main__":
    analyzer = TwitterSentimentAnalyzer()
    sentiment = analyzer.get_sentiment()
    print(f"Twitter Sentiment: {sentiment}")