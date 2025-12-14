#!/usr/bin/env python3
"""
Kafka Consumer with DeepSeek LLM Agent
For CISC 5597/6935 Lab 4 Option 2

Features:
1. Read trending topics from Kafka Topic (twitter-trends)
2. Perform intelligent analysis using DeepSeek LLM
3. Write analysis results to new Topic (analysis-results)
"""

import json
import os
import sys
from datetime import datetime
from collections import defaultdict
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
from openai import OpenAI

# ==================== Configuration ====================
# Kafka Configuration
KAFKA_BROKERS = ['10.128.0.5:9092', '10.128.0.2:9092', '10.128.0.3:9092']
INPUT_TOPIC = 'twitter-trends'          # Input Topic (raw data)
OUTPUT_TOPIC = 'analysis-results'        # Output Topic (analysis results)
GROUP_ID = 'deepseek-agent-group'

# DeepSeek API Configuration
# Setup: export DEEPSEEK_API_KEY='your-key-here'
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# Analysis Settings
BATCH_SIZE = 5  # Number of topics to analyze per batch (to save API calls)
# =======================================================


class DeepSeekAgent:
    """
    DeepSeek LLM Agent - Intelligent Analysis of Twitter Trending Topics

    This Agent acts as a "Social Media Analyst" capable of:
    1. Understanding the meaning of trending topics
    2. Analyzing topic categories and sentiment
    3. Predicting social impact of topics
    4. Generating comprehensive trend reports
    """
    
    def __init__(self, api_key):
        if not api_key:
            print("[!] ERROR: DeepSeek API key not set!")
            print("    Please set: export DEEPSEEK_API_KEY='your-key-here'")
            sys.exit(1)
            
        self.client = OpenAI(
            api_key=api_key,
            base_url=DEEPSEEK_BASE_URL
        )
        self.analysis_count = 0
        self.all_topics = []
        self.category_stats = defaultdict(int)
        self.sentiment_stats = defaultdict(int)
        print(f"[✓] DeepSeek LLM Agent initialized")
        print(f"    Model: deepseek-chat")
        print(f"    Role: Social Media Trend Analyst")
    
    def analyze_single(self, topic):
        """Analyze a single trending topic"""
        prompt = f"""You are a professional social media analyst. Analyze this Twitter trending topic from the United States:

**Topic:** {topic}

Provide analysis in the following JSON format:
{{
    "topic": "{topic}",
    "explanation": "Brief explanation of what this trend is about (1-2 sentences)",
    "category": "One of: Politics, Sports, Entertainment, Technology, Breaking News, Social Issues, Business, Celebrity, Other",
    "sentiment": "One of: Positive, Negative, Neutral, Mixed",
    "potential_impact": "Brief assessment of social/cultural impact (1 sentence)",
    "confidence": "High, Medium, or Low"
}}

Return ONLY the JSON, no other text."""

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert social media analyst. Always respond with valid JSON only."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content.strip()

            # Try to parse JSON
            try:
                # Clean up possible markdown code blocks
                if result_text.startswith("```"):
                    result_text = result_text.split("```")[1]
                    if result_text.startswith("json"):
                        result_text = result_text[4:]
                result = json.loads(result_text)
            except json.JSONDecodeError:
                result = {
                    "topic": topic,
                    "explanation": result_text[:200],
                    "category": "Other",
                    "sentiment": "Neutral",
                    "potential_impact": "Unable to parse",
                    "confidence": "Low"
                }
            
            # Update statistics
            self.analysis_count += 1
            self.all_topics.append(topic)
            self.category_stats[result.get('category', 'Other')] += 1
            self.sentiment_stats[result.get('sentiment', 'Neutral')] += 1
            
            return result
            
        except Exception as e:
            return {
                "topic": topic,
                "explanation": f"Analysis error: {str(e)}",
                "category": "Error",
                "sentiment": "Unknown",
                "potential_impact": "N/A",
                "confidence": "None"
            }
    
    def analyze_batch(self, trends):
        """Batch analyze multiple trending topics"""
        if not trends:
            return []
        
        topics_list = [t.get('topic', '') for t in trends]
        topics_text = "\n".join([f"{i+1}. {t}" for i, t in enumerate(topics_list)])
        
        prompt = f"""You are a professional social media analyst. Analyze these Twitter trending topics from the United States:

{topics_text}

For EACH topic, provide analysis in this JSON array format:
[
    {{
        "topic": "topic name",
        "explanation": "what this trend is about",
        "category": "Politics/Sports/Entertainment/Technology/Breaking News/Social Issues/Business/Celebrity/Other",
        "sentiment": "Positive/Negative/Neutral/Mixed"
    }},
    ...
]

Also add a final summary object:
{{
    "type": "summary",
    "main_themes": "2-3 main themes across all trends",
    "overall_mood": "general public mood based on these trends",
    "notable_observation": "one interesting pattern you noticed"
}}

Return ONLY the JSON array, no other text."""

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert social media analyst. Always respond with valid JSON array only."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content.strip()

            # Clean and parse
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            
            try:
                results = json.loads(result_text)

                # Update statistics
                for r in results:
                    if r.get('type') != 'summary':
                        self.analysis_count += 1
                        self.all_topics.append(r.get('topic', ''))
                        self.category_stats[r.get('category', 'Other')] += 1
                        self.sentiment_stats[r.get('sentiment', 'Neutral')] += 1
                
                return results
            except json.JSONDecodeError:
                return [{"error": "Failed to parse response", "raw": result_text[:500]}]
            
        except Exception as e:
            return [{"error": str(e)}]
    
    def generate_final_report(self):
        """Generate final analysis report"""
        if not self.all_topics:
            return "No trends were analyzed."
        
        topics_sample = ", ".join(self.all_topics[:15])
        
        prompt = f"""Based on analyzing {len(self.all_topics)} Twitter trending topics from the US today, including:
{topics_sample}

Category distribution: {dict(self.category_stats)}
Sentiment distribution: {dict(self.sentiment_stats)}

Generate a comprehensive summary report (4-5 sentences) covering:
1. Main topics Americans are discussing today
2. Overall public sentiment and mood
3. Any concerning or positive trends
4. Prediction for what might trend next"""

        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a senior social media analyst writing an executive summary."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating report: {str(e)}"
    
    def get_statistics(self):
        """Get statistics"""
        return {
            "total_analyzed": self.analysis_count,
            "unique_topics": len(set(self.all_topics)),
            "category_distribution": dict(self.category_stats),
            "sentiment_distribution": dict(self.sentiment_stats)
        }


def create_consumer():
    """Create Kafka Consumer"""
    try:
        consumer = KafkaConsumer(
            INPUT_TOPIC,
            bootstrap_servers=KAFKA_BROKERS,
            group_id=GROUP_ID,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            auto_commit_interval_ms=5000,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None,
            consumer_timeout_ms=60000,  # 60 seconds timeout
        )
        print(f"[✓] Kafka Consumer connected")
        print(f"    Brokers: {KAFKA_BROKERS}")
        print(f"    Input Topic: {INPUT_TOPIC}")
        print(f"    Consumer Group: {GROUP_ID}")
        return consumer
    except KafkaError as e:
        print(f"[✗] Failed to connect Consumer: {e}")
        raise


def create_producer():
    """Create Kafka Producer (for outputting analysis results)"""
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
        )
        print(f"[✓] Kafka Producer connected")
        print(f"    Output Topic: {OUTPUT_TOPIC}")
        return producer
    except KafkaError as e:
        print(f"[✗] Failed to connect Producer: {e}")
        raise


def main():
    """Main function"""
    print("=" * 70)
    print("🤖 DeepSeek LLM Agent - Twitter Trends Analyzer")
    print("   CISC 5597/6935 Lab 4 Option 2")
    print("=" * 70)
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")

    # Initialize components
    consumer = create_consumer()
    producer = create_producer()
    agent = DeepSeekAgent(DEEPSEEK_API_KEY)
    
    print("\n" + "=" * 70)
    print("📊 Starting Real-time Analysis Pipeline")
    print("=" * 70)
    print(f"   Input:  {INPUT_TOPIC} (raw trending data)")
    print(f"   Output: {OUTPUT_TOPIC} (LLM analysis results)")
    print("=" * 70 + "\n")
    
    message_count = 0
    batch_buffer = []
    
    try:
        print("[INFO] Waiting for trending topics... (Press Ctrl+C to stop)\n")
        
        while True:
            for message in consumer:
                message_count += 1
                trend = message.value
                topic = trend.get('topic', 'N/A')
                rank = trend.get('rank', '?')
                
                print(f"{'─' * 70}")
                print(f"📥 [{message_count}] Received: Rank #{rank} - {topic}")
                print(f"    Partition: {message.partition}, Offset: {message.offset}")

                batch_buffer.append(trend)

                # Batch analysis
                if len(batch_buffer) >= BATCH_SIZE:
                    print(f"\n{'=' * 70}")
                    print(f"🤖 DeepSeek Agent Analyzing {len(batch_buffer)} Topics...")
                    print("=" * 70)

                    # Call LLM analysis
                    analysis_results = agent.analyze_batch(batch_buffer)

                    # Print results and send to output Topic
                    for result in analysis_results:
                        if result.get('type') == 'summary':
                            print(f"\n📊 BATCH SUMMARY:")
                            print(f"   Main Themes: {result.get('main_themes', 'N/A')}")
                            print(f"   Overall Mood: {result.get('overall_mood', 'N/A')}")
                            print(f"   Notable: {result.get('notable_observation', 'N/A')}")
                        elif 'error' not in result:
                            print(f"\n   📌 {result.get('topic', 'N/A')}")
                            print(f"      └─ {result.get('explanation', 'N/A')}")
                            print(f"      └─ Category: {result.get('category', 'N/A')} | Sentiment: {result.get('sentiment', 'N/A')}")

                        # Send to output Topic
                        result['analyzed_at'] = datetime.now().isoformat()
                        producer.send(OUTPUT_TOPIC, value=result)
                    
                    producer.flush()
                    print(f"\n✅ Results sent to '{OUTPUT_TOPIC}' topic")
                    print("=" * 70 + "\n")

                    batch_buffer = []

            # Process remaining
            if batch_buffer:
                print(f"\n🤖 Analyzing remaining {len(batch_buffer)} topics...")
                analysis_results = agent.analyze_batch(batch_buffer)
                for result in analysis_results:
                    result['analyzed_at'] = datetime.now().isoformat()
                    producer.send(OUTPUT_TOPIC, value=result)
                producer.flush()
                batch_buffer = []
            
            print(f"\n[INFO] Processed {message_count} messages. Waiting for more...\n")
            
    except KeyboardInterrupt:
        print(f"\n\n[INFO] Stopping DeepSeek Agent...")

        # Generate final report
        print(f"\n{'=' * 70}")
        print("📋 FINAL ANALYSIS REPORT")
        print("=" * 70)
        
        stats = agent.get_statistics()
        print(f"\n📊 Statistics:")
        print(f"   Total topics analyzed: {stats['total_analyzed']}")
        print(f"   Unique topics: {stats['unique_topics']}")
        print(f"\n   Category Distribution:")
        for cat, count in sorted(stats['category_distribution'].items(), key=lambda x: -x[1]):
            pct = count / max(stats['total_analyzed'], 1) * 100
            print(f"      {cat}: {count} ({pct:.1f}%)")
        print(f"\n   Sentiment Distribution:")
        for sent, count in sorted(stats['sentiment_distribution'].items(), key=lambda x: -x[1]):
            pct = count / max(stats['total_analyzed'], 1) * 100
            print(f"      {sent}: {count} ({pct:.1f}%)")
        
        print(f"\n{'─' * 70}")
        print("🤖 AI-Generated Summary:")
        print("─" * 70)
        final_report = agent.generate_final_report()
        print(final_report)
        print("=" * 70)

        # Send final report to Topic
        final_result = {
            "type": "final_report",
            "statistics": stats,
            "summary": final_report,
            "generated_at": datetime.now().isoformat()
        }
        producer.send(OUTPUT_TOPIC, value=final_result)
        producer.flush()
        print(f"\n✅ Final report sent to '{OUTPUT_TOPIC}'")
        
    finally:
        consumer.close()
        producer.close()
        print("[✓] All connections closed")


if __name__ == "__main__":
    main()
