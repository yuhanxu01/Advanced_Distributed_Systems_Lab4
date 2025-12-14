#!/usr/bin/env python3
"""
Kafka Consumer - Read news from Kafka and perform analysis
For CISC 5597/6935 Lab 4 Option 2
"""

import json
import re
from datetime import datetime
from collections import defaultdict
from kafka import KafkaConsumer
from kafka.errors import KafkaError

# Kafka Configuration
KAFKA_BROKERS = ['10.128.0.5:9092', '10.128.0.2:9092', '10.128.0.3:9092']
TOPIC_NAME = 'news-feed'
GROUP_ID = 'news-analyzer-group'

# Simple sentiment analysis keywords (no LLM API needed)
POSITIVE_WORDS = {'good', 'great', 'success', 'win', 'positive', 'growth', 'breakthrough', 
                  'improve', 'gain', 'rise', 'advance', 'achievement', 'celebrate', 'peace'}
NEGATIVE_WORDS = {'bad', 'fail', 'crisis', 'war', 'death', 'negative', 'loss', 'crash',
                  'decline', 'disaster', 'conflict', 'attack', 'threat', 'danger', 'fear'}

class NewsAnalyzer:
    """Simple news analyzer"""
    
    def __init__(self):
        self.stats = defaultdict(int)
        self.sentiment_counts = {'positive': 0, 'negative': 0, 'neutral': 0}
        self.source_counts = defaultdict(int)
    
    def simple_sentiment(self, text):
        """Simple sentiment analysis"""
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        pos_count = len(words & POSITIVE_WORDS)
        neg_count = len(words & NEGATIVE_WORDS)
        
        if pos_count > neg_count:
            return 'positive', pos_count - neg_count
        elif neg_count > pos_count:
            return 'negative', neg_count - pos_count
        else:
            return 'neutral', 0
    
    def extract_keywords(self, text, top_n=5):
        """Extract keywords (simple word frequency statistics)"""
        # Stop words
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                    'could', 'should', 'may', 'might', 'must', 'shall', 'can',
                    'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                    'as', 'into', 'through', 'during', 'before', 'after', 'above',
                    'below', 'between', 'under', 'again', 'further', 'then', 'once',
                    'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either',
                    'neither', 'not', 'only', 'own', 'same', 'than', 'too', 'very',
                    'just', 'that', 'this', 'these', 'those', 'it', 'its', 'his',
                    'her', 'their', 'our', 'your', 'he', 'she', 'they', 'we', 'you',
                    'who', 'which', 'what', 'when', 'where', 'why', 'how', 'all',
                    'each', 'every', 'any', 'some', 'such', 'no', 'more', 'most',
                    'other', 'new', 'said', 'says', 'also', 'been', 'being'}
        
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        word_freq = defaultdict(int)
        
        for word in words:
            if word not in stopwords:
                word_freq[word] += 1
        
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:top_n]]
    
    def analyze(self, article):
        """Analyze a single article"""
        title = article.get('title', '')
        summary = article.get('summary', '')
        source = article.get('source', 'unknown')


        full_text = f"{title} {summary}"

        # Sentiment analysis
        sentiment, score = self.simple_sentiment(full_text)
        self.sentiment_counts[sentiment] += 1

        # Source statistics
        self.source_counts[source] += 1

        # Extract keywords
        keywords = self.extract_keywords(full_text)
        
        return {
            'sentiment': sentiment,
            'sentiment_score': score,
            'keywords': keywords,
        }
    
    def get_summary(self):
        """Get statistical summary"""
        total = sum(self.sentiment_counts.values())
        return {
            'total_articles': total,
            'sentiment_distribution': dict(self.sentiment_counts),
            'articles_by_source': dict(self.source_counts),
        }


def create_consumer():
    """Create Kafka Consumer"""
    try:
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers=KAFKA_BROKERS,
            group_id=GROUP_ID,
            auto_offset_reset='earliest',  # Start reading from earliest message
            enable_auto_commit=True,
            auto_commit_interval_ms=5000,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            consumer_timeout_ms=10000,  # Return after 10 seconds without new messages
        )
        print(f"[✓] Connected to Kafka cluster: {KAFKA_BROKERS}")
        print(f"[✓] Subscribed to topic: {TOPIC_NAME}")
        print(f"[✓] Consumer group: {GROUP_ID}")
        return consumer
    except KafkaError as e:
        print(f"[✗] Failed to connect to Kafka: {e}")
        raise


def main():
    """Main function"""
    print("=" * 70)
    print("Kafka News Consumer & Analyzer - Lab 4 Option 2")
    print("=" * 70)
    
    consumer = create_consumer()
    analyzer = NewsAnalyzer()
    
    message_count = 0
    
    try:
        print("\n[INFO] Waiting for messages... (Press Ctrl+C to stop)\n")


        while True:
            # Pull messages
            for message in consumer:
                message_count += 1
                article = message.value

                # Analyze article
                analysis = analyzer.analyze(article)

                # Print results
                print(f"{'─' * 70}")
                print(f"[Message #{message_count}] Partition: {message.partition}, Offset: {message.offset}")
                print(f"  Source: {article.get('source', 'N/A')}")
                print(f"  Title: {article.get('title', 'N/A')[:80]}...")
                print(f"  Sentiment: {analysis['sentiment'].upper()} (score: {analysis['sentiment_score']})")
                print(f"  Keywords: {', '.join(analysis['keywords'])}")
                print(f"  Published: {article.get('published', 'N/A')}")

                # Print statistics every 10 messages
                if message_count % 10 == 0:
                    summary = analyzer.get_summary()
                    print(f"\n{'=' * 70}")
                    print(f"[STATISTICS after {message_count} messages]")
                    print(f"  Sentiment: Positive={summary['sentiment_distribution']['positive']}, "
                          f"Negative={summary['sentiment_distribution']['negative']}, "
                          f"Neutral={summary['sentiment_distribution']['neutral']}")
                    print(f"  By Source: {dict(summary['articles_by_source'])}")
                    print(f"{'=' * 70}\n")

            # If no more messages, print statistics and continue waiting
            if message_count > 0:
                print(f"\n[INFO] No more messages. Processed {message_count} total. Waiting for new messages...")
            else:
                print("[INFO] No messages yet. Waiting...")
            
    except KeyboardInterrupt:
        print(f"\n\n[INFO] Stopping consumer...")

        # Final statistics
        summary = analyzer.get_summary()
        print(f"\n{'=' * 70}")
        print("FINAL STATISTICS")
        print(f"{'=' * 70}")
        print(f"Total articles processed: {summary['total_articles']}")
        print(f"\nSentiment Distribution:")
        for sentiment, count in summary['sentiment_distribution'].items():
            pct = (count / max(summary['total_articles'], 1)) * 100
            print(f"  {sentiment.capitalize()}: {count} ({pct:.1f}%)")
        print(f"\nArticles by Source:")
        for source, count in sorted(summary['articles_by_source'].items(), key=lambda x: -x[1]):
            print(f"  {source}: {count}")
        print(f"{'=' * 70}")
        
    finally:
        consumer.close()
        print("[✓] Consumer closed")


if __name__ == "__main__":
    main()
