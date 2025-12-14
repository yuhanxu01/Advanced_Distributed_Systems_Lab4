#!/usr/bin/env python3
"""
Kafka Producer - Fetch news from RSS Feed and send to Kafka
For CISC 5597/6935 Lab 4 Option 2
"""

import json
import time
import feedparser
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Kafka Configuration
KAFKA_BROKERS = ['10.128.0.5:9092', '10.128.0.2:9092', '10.128.0.3:9092']
TOPIC_NAME = 'news-feed'

# RSS Feed sources (can add more)
RSS_FEEDS = {
    'bbc_world': 'http://feeds.bbci.co.uk/news/world/rss.xml',
    'bbc_tech': 'http://feeds.bbci.co.uk/news/technology/rss.xml',
    'reuters': 'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best',
    'cnn_top': 'http://rss.cnn.com/rss/edition.rss',
    'nyt_world': 'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
}

def create_producer():
    """Create Kafka Producer"""
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',  # Wait for all replicas to acknowledge
            retries=3,
            batch_size=16384,
            linger_ms=10,
        )
        print(f"[✓] Connected to Kafka cluster: {KAFKA_BROKERS}")
        return producer
    except KafkaError as e:
        print(f"[✗] Failed to connect to Kafka: {e}")
        raise

def fetch_rss_feed(feed_name, feed_url):
    """Fetch news from RSS Feed"""
    try:
        feed = feedparser.parse(feed_url)
        articles = []

        for entry in feed.entries[:10]:  # Get first 10 from each source
            article = {
                'source': feed_name,
                'title': entry.get('title', 'No Title'),
                'link': entry.get('link', ''),
                'summary': entry.get('summary', '')[:500],  # Limit summary length
                'published': entry.get('published', ''),
                'fetched_at': datetime.now().isoformat(),
            }
            articles.append(article)
        
        print(f"[✓] Fetched {len(articles)} articles from {feed_name}")
        return articles
    except Exception as e:
        print(f"[✗] Error fetching {feed_name}: {e}")
        return []

def send_to_kafka(producer, articles):
    """Send articles to Kafka"""
    success_count = 0


    for article in articles:
        try:
            # Use source as key to ensure messages from same source go to same partition
            future = producer.send(
                TOPIC_NAME,
                key=article['source'],
                value=article
            )
            # Wait for send to complete
            record_metadata = future.get(timeout=10)
            success_count += 1
            print(f"  → Sent to partition {record_metadata.partition}, offset {record_metadata.offset}")
        except KafkaError as e:
            print(f"  [✗] Failed to send: {e}")
    
    return success_count

def main():
    """Main function"""
    print("=" * 60)
    print("Kafka News Producer - Lab 4 Option 2")
    print("=" * 60)

    # Create producer
    producer = create_producer()

    # Create topic (will be auto-created if doesn't exist)
    print(f"\n[INFO] Publishing to topic: {TOPIC_NAME}")
    
    total_sent = 0
    round_num = 1
    
    try:
        while True:
            print(f"\n{'='*60}")
            print(f"Round {round_num} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)

            # Fetch and send from each RSS source
            for feed_name, feed_url in RSS_FEEDS.items():
                print(f"\n[Fetching] {feed_name}...")
                articles = fetch_rss_feed(feed_name, feed_url)
                
                if articles:
                    sent = send_to_kafka(producer, articles)
                    total_sent += sent

            # Ensure all messages are sent
            producer.flush()

            print(f"\n[Summary] Total messages sent so far: {total_sent}")
            print(f"[INFO] Waiting 60 seconds before next round...")
            print("Press Ctrl+C to stop")

            round_num += 1
            time.sleep(60)  # Fetch every 60 seconds
            
    except KeyboardInterrupt:
        print(f"\n\n[INFO] Stopping producer...")
        print(f"[Summary] Total messages sent: {total_sent}")
    finally:
        producer.close()
        print("[✓] Producer closed")

if __name__ == "__main__":
    main()
