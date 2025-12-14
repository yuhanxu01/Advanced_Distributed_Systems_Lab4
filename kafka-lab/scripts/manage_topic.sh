#!/bin/bash

# Kafka Topic 管理脚本
# 在任意一个 broker 节点上运行

KAFKA_DIR="/opt/kafka"
BOOTSTRAP_SERVER="10.128.0.5:9092"
TOPIC_NAME="news-feed"

case "$1" in
    create)
        echo "Creating topic: $TOPIC_NAME"
        $KAFKA_DIR/bin/kafka-topics.sh --create \
            --bootstrap-server $BOOTSTRAP_SERVER \
            --topic $TOPIC_NAME \
            --partitions 3 \
            --replication-factor 3
        ;;
    list)
        echo "Listing all topics:"
        $KAFKA_DIR/bin/kafka-topics.sh --list \
            --bootstrap-server $BOOTSTRAP_SERVER
        ;;
    describe)
        echo "Describing topic: $TOPIC_NAME"
        $KAFKA_DIR/bin/kafka-topics.sh --describe \
            --bootstrap-server $BOOTSTRAP_SERVER \
            --topic $TOPIC_NAME
        ;;
    delete)
        echo "Deleting topic: $TOPIC_NAME"
        $KAFKA_DIR/bin/kafka-topics.sh --delete \
            --bootstrap-server $BOOTSTRAP_SERVER \
            --topic $TOPIC_NAME
        ;;
    *)
        echo "Usage: $0 {create|list|describe|delete}"
        exit 1
        ;;
esac
