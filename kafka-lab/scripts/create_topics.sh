#!/bin/bash

# 创建 Lab 4 需要的所有 Topics
# 在任意一个 Kafka broker 节点上运行

KAFKA_DIR="/opt/kafka"
BOOTSTRAP_SERVER="10.128.0.5:9092"

echo "=========================================="
echo "Creating Kafka Topics for Lab 4"
echo "=========================================="

# 创建输入 Topic（原始数据）
echo ""
echo "[1/2] Creating 'twitter-trends' topic..."
$KAFKA_DIR/bin/kafka-topics.sh --create \
    --bootstrap-server $BOOTSTRAP_SERVER \
    --topic twitter-trends \
    --partitions 3 \
    --replication-factor 3 \
    --if-not-exists

# 创建输出 Topic（LLM 分析结果）
echo ""
echo "[2/2] Creating 'analysis-results' topic..."
$KAFKA_DIR/bin/kafka-topics.sh --create \
    --bootstrap-server $BOOTSTRAP_SERVER \
    --topic analysis-results \
    --partitions 3 \
    --replication-factor 3 \
    --if-not-exists

# 验证
echo ""
echo "=========================================="
echo "Verifying Topics"
echo "=========================================="
$KAFKA_DIR/bin/kafka-topics.sh --list --bootstrap-server $BOOTSTRAP_SERVER

echo ""
echo "=========================================="
echo "Topic Details"
echo "=========================================="
$KAFKA_DIR/bin/kafka-topics.sh --describe --bootstrap-server $BOOTSTRAP_SERVER --topic twitter-trends
echo ""
$KAFKA_DIR/bin/kafka-topics.sh --describe --bootstrap-server $BOOTSTRAP_SERVER --topic analysis-results

echo ""
echo "✓ All topics created successfully!"
