#!/usr/bin/env python3
"""
Kafka Producer - Fetch Twitter trending topics from trends24.in and send to Kafka
For CISC 5597/6935 Lab 4 Option 2
"""

import json
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from kafka import KafkaProducer
from kafka.errors import KafkaError

# Kafka Configuration
KAFKA_BROKERS = ['10.128.0.5:9092', '10.128.0.2:9092', '10.128.0.3:9092']
TOPIC_NAME = 'twitter-trends'

# trends24.in URL
TRENDS_URL = 'https://trends24.in/united-states/'

# Request headers to simulate browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def create_producer():
    """Create Kafka Producer"""
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3,
            batch_size=16384,
            linger_ms=10,
        )
        print(f"[✓] Connected to Kafka cluster: {KAFKA_BROKERS}")
        return producer
    except KafkaError as e:
        print(f"[✗] Failed to connect to Kafka: {e}")
        raise


def fetch_trends():
    """Fetch trending topics from trends24.in"""
    try:
        print(f"[INFO] Fetching trends from {TRENDS_URL}")
        response = requests.get(TRENDS_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        trends = []

        # trends24.in structure: trends for each time period in .trend-card
        # Trending topics in li elements within ol.trend-card__list
        trend_cards = soup.find_all('div', class_='trend-card')

        if not trend_cards:
            # Fallback selector
            trend_cards = soup.find_all('ol', class_='trend-card__list')

        rank = 1
        seen_topics = set()  # Avoid duplicates

        for card in trend_cards[:3]:  # Only get first 3 time periods
            # Get time period header
            time_header = card.find_previous('div', class_='trend-card__header')
            time_slot = ""
            if time_header:
                time_slot = time_header.get_text(strip=True)

            # Get all topics for this time period
            list_items = card.find_all('li')
            if not list_items:
                list_items = card.find_all('a')

            for item in list_items:
                # Get topic text
                topic_text = item.get_text(strip=True)

                # Clean text
                if topic_text and len(topic_text) > 1 and topic_text not in seen_topics:
                    seen_topics.add(topic_text)

                    # Get link (if available)
                    link = item.find('a')
                    topic_url = ""
                    if link and link.get('href'):
                        topic_url = link.get('href')
                        if not topic_url.startswith('http'):
                            topic_url = f"https://twitter.com/search?q={topic_text}"
                    
                    trend_data = {
                        'rank': rank,
                        'topic': topic_text,
                        'time_slot': time_slot,
                        'url': topic_url,
                        'source': 'trends24.in',
                        'region': 'United States',
                        'fetched_at': datetime.now().isoformat(),
                    }
                    trends.append(trend_data)
                    rank += 1

                    if rank > 30:  # Limit to max 30 topics
                        break

            if rank > 30:
                break
        
        print(f"[✓] Fetched {len(trends)} trending topics")
        return trends
        
    except requests.RequestException as e:
        print(f"[✗] Error fetching trends: {e}")
        return []
    except Exception as e:
        print(f"[✗] Parsing error: {e}")
        return []


def fetch_trends_simple():
    """Fallback method: simpler parsing"""
    try:
        print(f"[INFO] Fetching trends (simple method)...")
        response = requests.get(TRENDS_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        trends = []

        # Find all links containing twitter or trend-related content
        all_links = soup.find_all('a')

        rank = 1
        seen = set()

        for link in all_links:
            text = link.get_text(strip=True)
            href = link.get('href', '')

            # Filter condition: text that looks like a topic
            if (text and
                len(text) > 1 and
                len(text) < 100 and
                text not in seen and
                not text.lower().startswith(('http', 'www', 'trend', 'home', 'about'))):

                # Check if it's a hashtag or trending topic format
                if text.startswith('#') or 'trend' in href.lower() or len(text.split()) <= 5:
                    seen.add(text)
                    trends.append({
                        'rank': rank,
                        'topic': text,
                        'url': href if href.startswith('http') else f"https://twitter.com/search?q={text}",
                        'source': 'trends24.in',
                        'region': 'United States',
                        'fetched_at': datetime.now().isoformat(),
                    })
                    rank += 1
                    
                    if rank > 20:
                        break
        
        print(f"[✓] Fetched {len(trends)} topics (simple method)")
        return trends
        
    except Exception as e:
        print(f"[✗] Simple fetch error: {e}")
        return []


def send_to_kafka(producer, trends):
    """Send to Kafka"""
    success_count = 0
    
    for trend in trends:
        try:
            future = producer.send(
                TOPIC_NAME,
                key=f"rank-{trend['rank']}",
                value=trend
            )
            record_metadata = future.get(timeout=10)
            success_count += 1
            print(f"  → [{trend['rank']:2d}] {trend['topic'][:40]:<40} | Partition {record_metadata.partition}, Offset {record_metadata.offset}")
        except KafkaError as e:
            print(f"  [✗] Failed to send: {e}")
    
    return success_count


def main():
    """Main function"""
    print("=" * 70)
    print("Twitter Trends Producer - Lab 4 Option 2")
    print("Data Source: trends24.in/united-states")
    print("=" * 70)
    
    producer = create_producer()
    print(f"\n[INFO] Publishing to topic: {TOPIC_NAME}")
    
    total_sent = 0
    round_num = 1
    
    try:
        while True:
            print(f"\n{'='*70}")
            print(f"Round {round_num} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 70)

            # Try main method, fallback to simple method if fails
            trends = fetch_trends()
            if not trends:
                print("[INFO] Trying simple method...")
                trends = fetch_trends_simple()
            
            if trends:
                print(f"\n[Sending to Kafka]")
                sent = send_to_kafka(producer, trends)
                total_sent += sent
                producer.flush()
                print(f"\n[Summary] Sent {sent} trends this round, {total_sent} total")
            else:
                print("[WARN] No trends fetched this round")


            print(f"\n[INFO] Waiting 5 minutes before next fetch...")
            print("Press Ctrl+C to stop")

            round_num += 1
            time.sleep(300)  # Fetch every 5 minutes (avoid frequent requests)
            
    except KeyboardInterrupt:
        print(f"\n\n[INFO] Stopping producer...")
        print(f"[Summary] Total messages sent: {total_sent}")
    finally:
        producer.close()
        print("[✓] Producer closed")


if __name__ == "__main__":
    main()
