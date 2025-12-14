# CISC 5597/6935 Lab 4 Option 2
# Twitter Trends Analysis with Kafka & DeepSeek LLM Agent

## 📋 Project Overview

This project implements a **real-time data streaming pipeline** that:
1. Collects trending topics from Twitter (via trends24.in)
2. Streams data through a distributed Apache Kafka cluster
3. Analyzes trends using **DeepSeek LLM** as an intelligent agent
4. Outputs analysis results to a separate Kafka topic

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GCP Cloud Infrastructure                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                     │
│  │   node0     │    │   node1     │    │   node2     │                     │
│  │ 10.128.0.5  │◄──►│ 10.128.0.2  │◄──►│ 10.128.0.3  │                     │
│  │  Broker 1   │    │  Broker 2   │    │  Broker 3   │                     │
│  │ (Controller)│    │             │    │             │                     │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                     │
│         │                  │                  │                             │
│         └──────────────────┼──────────────────┘                             │
│                            │                                                │
│              ┌─────────────┴─────────────┐                                  │
│              │      KAFKA CLUSTER        │                                  │
│              │                           │                                  │
│              │  ┌─────────────────────┐  │                                  │
│              │  │ Topic:              │  │                                  │
│              │  │ twitter-trends      │  │                                  │
│              │  │ (3 partitions)      │  │                                  │
│              │  └──────────┬──────────┘  │                                  │
│              │             │             │                                  │
│              │  ┌──────────▼──────────┐  │                                  │
│              │  │ Topic:              │  │                                  │
│              │  │ analysis-results    │  │                                  │
│              │  │ (LLM output)        │  │                                  │
│              │  └─────────────────────┘  │                                  │
│              └─────────────┬─────────────┘                                  │
│                            │                                                │
│         ┌──────────────────┼──────────────────┐                             │
│         │                  │                  │                             │
│         ▼                  │                  ▼                             │
│  ┌─────────────┐           │           ┌─────────────┐                     │
│  │  PRODUCER   │           │           │  CONSUMER   │                     │
│  │             │           │           │ (LLM Agent) │                     │
│  │ trends24.in │──────────►│◄──────────│             │                     │
│  │  Scraper    │   write   │   read    │  DeepSeek   │                     │
│  └─────────────┘           │           │    API      │                     │
│       node3                │           └──────┬──────┘                     │
│    10.128.0.4              │                  │                             │
│                            │                  ▼                             │
│                            │           ┌─────────────┐                     │
│                            │           │  Analysis   │                     │
│                            │           │  Results    │                     │
│                            │           └─────────────┘                     │
│                            │                                                │
└────────────────────────────┴────────────────────────────────────────────────┘

External Services:
┌─────────────────┐         ┌─────────────────┐
│  trends24.in    │         │   DeepSeek API  │
│  (Data Source)  │         │   (LLM Engine)  │
└─────────────────┘         └─────────────────┘
```

---

## 📊 Data Flow

```
[trends24.in] ──► [Producer] ──► [Kafka: twitter-trends] ──► [LLM Consumer] ──► [Kafka: analysis-results]
                                         │                          │
                                         │                          ▼
                                         │                   [DeepSeek API]
                                         │                          │
                                         │                          ▼
                                         │                   [AI Analysis]
                                         │                          │
                                         └──────────────────────────┘
```

---

## 🖥️ Node Configuration

| Node | IP Address | Role | Components |
|------|------------|------|------------|
| node0 | 10.128.0.5 | Kafka Broker 1 | Kafka (Controller), KRaft |
| node1 | 10.128.0.2 | Kafka Broker 2 | Kafka, KRaft |
| node2 | 10.128.0.3 | Kafka Broker 3 | Kafka, KRaft |
| node3 | 10.128.0.4 | Application | Producer, LLM Consumer |

---

## 📁 Project Structure

```
kafka-lab/
├── producer/
│   ├── trends_producer.py      # Scrapes trends24.in, sends to Kafka
│   └── news_producer.py        # Alternative: RSS news producer
├── consumer/
│   ├── llm_consumer.py         # DeepSeek LLM Agent consumer (MAIN)
│   ├── trends_consumer.py      # Basic consumer (no LLM)
│   └── news_consumer.py        # Alternative: news consumer
├── scripts/
│   ├── install_kafka.sh        # Kafka installation script
│   ├── configure_kafka.sh      # Configuration script
│   ├── kafka_service.sh        # Start/stop Kafka
│   ├── manage_topic.sh         # Topic management
│   └── check_cluster.sh        # Cluster health check
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## 🚀 Deployment Guide

### Step 1: Deploy Kafka Cluster (node0, node1, node2)

**On each broker node:**

```bash
# Install Java
sudo apt-get update
sudo apt-get install -y openjdk-17-jdk wget

# Download Kafka 3.9.0
cd /opt
sudo wget https://downloads.apache.org/kafka/3.9.0/kafka_2.13-3.9.0.tgz
sudo tar -xzf kafka_2.13-3.9.0.tgz
sudo mv kafka_2.13-3.9.0 kafka
sudo rm kafka_2.13-3.9.0.tgz

# Create data directory
sudo mkdir -p /var/kafka-logs
sudo chown -R $USER:$USER /opt/kafka /var/kafka-logs
```

### Step 2: Configure Kafka (Different for each node!)

**node0 (10.128.0.5):**
```bash
cat > /opt/kafka/config/kraft/server.properties << 'EOF'
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@10.128.0.5:9093,2@10.128.0.2:9093,3@10.128.0.3:9093
listeners=PLAINTEXT://:9092,CONTROLLER://:9093
inter.broker.listener.name=PLAINTEXT
advertised.listeners=PLAINTEXT://10.128.0.5:9092
controller.listener.names=CONTROLLER
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
log.dirs=/var/kafka-logs
num.partitions=3
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2
EOF
```

**node1 (10.128.0.2):**
```bash
cat > /opt/kafka/config/kraft/server.properties << 'EOF'
process.roles=broker,controller
node.id=2
controller.quorum.voters=1@10.128.0.5:9093,2@10.128.0.2:9093,3@10.128.0.3:9093
listeners=PLAINTEXT://:9092,CONTROLLER://:9093
inter.broker.listener.name=PLAINTEXT
advertised.listeners=PLAINTEXT://10.128.0.2:9092
controller.listener.names=CONTROLLER
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
log.dirs=/var/kafka-logs
num.partitions=3
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2
EOF
```

**node2 (10.128.0.3):**
```bash
cat > /opt/kafka/config/kraft/server.properties << 'EOF'
process.roles=broker,controller
node.id=3
controller.quorum.voters=1@10.128.0.5:9093,2@10.128.0.2:9093,3@10.128.0.3:9093
listeners=PLAINTEXT://:9092,CONTROLLER://:9093
inter.broker.listener.name=PLAINTEXT
advertised.listeners=PLAINTEXT://10.128.0.3:9092
controller.listener.names=CONTROLLER
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
log.dirs=/var/kafka-logs
num.partitions=3
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2
EOF
```

### Step 3: Start Kafka Cluster

**On each node (use the SAME cluster ID):**
```bash
CLUSTER_ID="MkU3OEVBNTcwNTJENDM2Qk"
/opt/kafka/bin/kafka-storage.sh format -t $CLUSTER_ID -c /opt/kafka/config/kraft/server.properties
/opt/kafka/bin/kafka-server-start.sh -daemon /opt/kafka/config/kraft/server.properties
```

### Step 4: Create Topics

**On node0:**
```bash
# Create input topic
/opt/kafka/bin/kafka-topics.sh --create \
    --bootstrap-server 10.128.0.5:9092 \
    --topic twitter-trends \
    --partitions 3 \
    --replication-factor 3

# Create output topic for analysis results
/opt/kafka/bin/kafka-topics.sh --create \
    --bootstrap-server 10.128.0.5:9092 \
    --topic analysis-results \
    --partitions 3 \
    --replication-factor 3

# Verify
/opt/kafka/bin/kafka-topics.sh --list --bootstrap-server 10.128.0.5:9092
```

### Step 5: Setup Application Node (node3)

```bash
# Install Python dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip

pip3 install kafka-python beautifulsoup4 requests openai --break-system-packages

# Set DeepSeek API Key
export DEEPSEEK_API_KEY='your-deepseek-api-key-here'
```

### Step 6: Run the System

**Terminal 1 - Start LLM Consumer:**
```bash
cd ~/Advanced_Distributed_Systems_Lab4/kafka-lab/consumer
export DEEPSEEK_API_KEY='your-key-here'
python3 llm_consumer.py
```

**Terminal 2 - Start Producer:**
```bash
cd ~/Advanced_Distributed_Systems_Lab4/kafka-lab/producer
python3 trends_producer.py
```

---

## 🤖 LLM Agent Architecture

### Agent Design

The DeepSeek LLM Agent acts as an intelligent **Social Media Analyst**:

```
┌─────────────────────────────────────────────────────────────┐
│                    DeepSeek LLM Agent                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Input: Raw trending topic (e.g., "#SNME196K")              │
│                           │                                 │
│                           ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Prompt Engineering                      │   │
│  │  "You are a social media analyst. Analyze this      │   │
│  │   Twitter trending topic from the United States..." │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              DeepSeek API Call                       │   │
│  │  Model: deepseek-chat                               │   │
│  │  Temperature: 0.3 (for consistent analysis)         │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│                           ▼                                 │
│  Output:                                                    │
│  {                                                          │
│    "topic": "#SNME196K",                                    │
│    "explanation": "WWE Saturday Night's Main Event...",    │
│    "category": "Entertainment",                             │
│    "sentiment": "Positive",                                 │
│    "potential_impact": "Drives fan engagement..."          │
│  }                                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Analysis Capabilities

| Feature | Description |
|---------|-------------|
| Topic Explanation | Understands what each trend is about |
| Categorization | Politics, Sports, Entertainment, Technology, etc. |
| Sentiment Analysis | Positive, Negative, Neutral, Mixed |
| Impact Assessment | Predicts social/cultural impact |
| Batch Analysis | Efficiently processes multiple topics |
| Summary Generation | Creates executive summaries |

---

## 📊 Kafka Topics

| Topic Name | Purpose | Partitions | Replication |
|------------|---------|------------|-------------|
| `twitter-trends` | Raw trending data from Producer | 3 | 3 |
| `analysis-results` | LLM analysis output from Consumer | 3 | 3 |

---

## 🔧 Configuration Parameters

### Kafka Cluster
- **Mode**: KRaft (no Zookeeper)
- **Brokers**: 3
- **Replication Factor**: 3
- **Min ISR**: 2

### Producer
- **Data Source**: trends24.in/united-states
- **Fetch Interval**: 5 minutes
- **Batch Size**: Up to 30 topics per fetch

### LLM Consumer
- **Model**: deepseek-chat
- **Batch Size**: 5 topics per API call
- **Temperature**: 0.3 (for consistency)
- **Max Tokens**: 1000 per batch

---

## 📝 Sample Output

### Producer Output
```
======================================================================
Twitter Trends Producer - Lab 4 Option 2
Data Source: trends24.in/united-states
======================================================================
[✓] Connected to Kafka cluster
[✓] Fetched 30 trending topics

[Sending to Kafka]
→ [ 1] #SNME196K                    | Partition 0, Offset 13
→ [ 2] #ThankYouCena270K            | Partition 2, Offset 9
→ [ 3] John Cena295K                | Partition 2, Offset 10
...
```

### LLM Consumer Output
```
======================================================================
🤖 DeepSeek LLM Agent - Twitter Trends Analyzer
======================================================================
[✓] Kafka Consumer connected
[✓] DeepSeek LLM Agent initialized
    Model: deepseek-chat
    Role: Social Media Trend Analyst

📥 [1] Received: Rank #1 - #SNME196K
📥 [2] Received: Rank #2 - #ThankYouCena270K
...

🤖 DeepSeek Agent Analyzing 5 Topics...
======================================================================

   📌 #SNME196K
      └─ WWE Saturday Night's Main Event episode 196K trending...
      └─ Category: Entertainment | Sentiment: Positive

   📌 John Cena295K  
      └─ WWE legend John Cena's retirement tour generating buzz...
      └─ Category: Sports | Sentiment: Positive

📊 BATCH SUMMARY:
   Main Themes: Sports entertainment, WWE wrestling events
   Overall Mood: Excited and nostalgic
   Notable: Strong wrestling community engagement

✅ Results sent to 'analysis-results' topic
======================================================================
```

---

## 📋 Requirements Checklist

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| Cluster deployment (not local) | ✅ | 3-node Kafka cluster on GCP |
| External data source | ✅ | trends24.in Twitter trends |
| Store data in Kafka (Producer) | ✅ | trends_producer.py |
| LLM Agent Consumer | ✅ | llm_consumer.py with DeepSeek |
| Results to new Topic | ✅ | analysis-results topic |
| Complete code | ✅ | All scripts included |
| Comprehensive report | ✅ | This README |
| Screen recording | ⬜ | To be recorded |

---

## 🔍 Commands Reference

```bash
# List all topics
/opt/kafka/bin/kafka-topics.sh --list --bootstrap-server 10.128.0.5:9092

# Describe a topic
/opt/kafka/bin/kafka-topics.sh --describe --bootstrap-server 10.128.0.5:9092 --topic twitter-trends

# Read from analysis-results topic
/opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server 10.128.0.5:9092 --topic analysis-results --from-beginning

# Check consumer groups
/opt/kafka/bin/kafka-consumer-groups.sh --list --bootstrap-server 10.128.0.5:9092

# Check Kafka process
jps
```

---

## 👤 Author: Yuhan Xu

- **Course**: CISC 5597/6935 - Distributed Systems
- **Assignment**: Lab 4 Option 2
- **Date**: December 14th 2024
