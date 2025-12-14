#!/usr/bin/env python3
"""
Kafka Consumer - Read Twitter trending topics from Kafka and analyze
For CISC 5597/6935 Lab 4 Option 2
"""

import json
import re
from datetime import datetime
from collections import defaultdict, Counter
from kafka import KafkaConsumer
from kafka.errors import KafkaError

# Kafka Configuration
KAFKA_BROKERS = ['10.128.0.5:9092', '10.128.0.2:9092', '10.128.0.3:9092']
TOPIC_NAME = 'twitter-trends'
GROUP_ID = 'trends-analyzer-group'


class TrendsAnalyzer:
    """Twitter trending topics analyzer"""
    
    def __init__(self):
        self.all_topics = []
        self.topic_frequency = Counter()
        self.hashtag_count = 0
        self.regular_count = 0
        self.rounds_processed = set()
    
    def analyze(self, trend):
        """Analyze a single topic"""
        topic = trend.get('topic', '')
        rank = trend.get('rank', 0)

        # Statistics
        self.all_topics.append(topic)
        self.topic_frequency[topic] += 1

        # Check if it's a hashtag
        is_hashtag = topic.startswith('#')
        if is_hashtag:
            self.hashtag_count += 1
        else:
            self.regular_count += 1

        # Extract keywords (remove special characters)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', topic.lower())

        # Simple categorization
        categories = self._categorize(topic)
        
        return {
            'is_hashtag': is_hashtag,
            'word_count': len(topic.split()),
            'keywords': words[:3],
            'categories': categories,
        }
    
    def _categorize(self, topic):
        """Simple topic categorization"""
        topic_lower = topic.lower()
        categories = []

        # Keyword categorization rules
        category_keywords = {
            'Politics': ['trump', 'biden', 'congress', 'senate', 'election', 'vote', 'democrat', 'republican', 'president'],
            'Sports': ['nfl', 'nba', 'mlb', 'game', 'team', 'player', 'win', 'championship', 'football', 'basketball'],
            'Entertainment': ['movie', 'music', 'celebrity', 'star', 'show', 'concert', 'album', 'film', 'netflix'],
            'Technology': ['ai', 'tech', 'apple', 'google', 'microsoft', 'crypto', 'bitcoin', 'app', 'software'],
            'Breaking News': ['breaking', 'just in', 'alert', 'update', 'happening', 'live'],
        }
        
        for category, keywords in category_keywords.items():
            if any(kw in topic_lower for kw in keywords):
                categories.append(category)
        
        if not categories:
            categories.append('General')
        
        return categories
    
    def get_summary(self):
        """Get statistical summary"""
        total = len(self.all_topics)

        # Most frequently appearing topics
        top_topics = self.topic_frequency.most_common(10)
        
        return {
            'total_trends_processed': total,
            'unique_topics': len(set(self.all_topics)),
            'hashtags': self.hashtag_count,
            'regular_topics': self.regular_count,
            'top_recurring_topics': top_topics,
        }


def create_consumer():
    """Create Kafka Consumer"""
    try:
        consumer = KafkaConsumer(
            TOPIC_NAME,
            bootstrap_servers=KAFKA_BROKERS,
            group_id=GROUP_ID,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            auto_commit_interval_ms=5000,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            consumer_timeout_ms=30000,  # 30 seconds timeout
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
    print("Twitter Trends Consumer & Analyzer - Lab 4 Option 2")
    print("=" * 70)
    
    consumer = create_consumer()
    analyzer = TrendsAnalyzer()
    
    message_count = 0
    
    try:
        print("\n[INFO] Waiting for trends... (Press Ctrl+C to stop)\n")
        
        while True:
            for message in consumer:
                message_count += 1
                trend = message.value

                # Analyze
                analysis = analyzer.analyze(trend)

                # Print
                topic = trend.get('topic', 'N/A')
                rank = trend.get('rank', '?')

                # Color indicator (hashtag vs regular topic)
                tag_indicator = "🏷️ " if analysis['is_hashtag'] else "📰 "
                
                print(f"{'─' * 70}")
                print(f"[#{message_count}] Partition: {message.partition}, Offset: {message.offset}")
                print(f"  {tag_indicator}Rank #{rank}: {topic}")
                print(f"  Categories: {', '.join(analysis['categories'])}")
                print(f"  Keywords: {', '.join(analysis['keywords']) if analysis['keywords'] else 'N/A'}")
                print(f"  Fetched: {trend.get('fetched_at', 'N/A')}")

                # Show statistics every 20 messages
                if message_count % 20 == 0:
                    summary = analyzer.get_summary()
                    print(f"\n{'=' * 70}")
                    print(f"[STATISTICS after {message_count} messages]")
                    print(f"  Total processed: {summary['total_trends_processed']}")
                    print(f"  Unique topics: {summary['unique_topics']}")
                    print(f"  Hashtags: {summary['hashtags']} | Regular: {summary['regular_topics']}")
                    if summary['top_recurring_topics']:
                        print(f"  Top recurring:")
                        for topic, count in summary['top_recurring_topics'][:5]:
                            print(f"    - {topic}: {count}x")
                    print(f"{'=' * 70}\n")
            
            print(f"\n[INFO] No more messages. Total: {message_count}. Waiting for new data...")
            
    except KeyboardInterrupt:
        print(f"\n\n[INFO] Stopping consumer...")

        # Final statistics
        summary = analyzer.get_summary()
        print(f"\n{'=' * 70}")
        print("FINAL STATISTICS")
        print(f"{'=' * 70}")
        print(f"Total trends processed: {summary['total_trends_processed']}")
        print(f"Unique topics: {summary['unique_topics']}")
        print(f"Hashtags: {summary['hashtags']} ({summary['hashtags']/max(1,summary['total_trends_processed'])*100:.1f}%)")
        print(f"Regular topics: {summary['regular_topics']}")
        
        if summary['top_recurring_topics']:
            print(f"\nMost Recurring Topics:")
            for i, (topic, count) in enumerate(summary['top_recurring_topics'], 1):
                print(f"  {i}. {topic} ({count}x)")
        
        print(f"{'=' * 70}")
        
    finally:
        consumer.close()
        print("[✓] Consumer closed")


if __name__ == "__main__":
    main()
