#!/bin/bash

# 检查 Kafka 集群状态
# 在任意一个 broker 节点上运行

KAFKA_DIR="/opt/kafka"
BOOTSTRAP_SERVER="10.128.0.5:9092"

echo "=========================================="
echo "Kafka Cluster Status Check"
echo "=========================================="

echo ""
echo "[1] Checking Kafka process..."
if pgrep -f kafka > /dev/null; then
    echo "    ✓ Kafka is running (PID: $(pgrep -f kafka.Kafka))"
else
    echo "    ✗ Kafka is NOT running"
fi

echo ""
echo "[2] Broker metadata..."
$KAFKA_DIR/bin/kafka-broker-api-versions.sh --bootstrap-server $BOOTSTRAP_SERVER 2>/dev/null | head -5

echo ""
echo "[3] Cluster ID..."
$KAFKA_DIR/bin/kafka-metadata.sh --snapshot /var/kafka-logs/__cluster_metadata-0/00000000000000000000.log --command cluster-id 2>/dev/null || echo "    (Run this on a controller node)"

echo ""
echo "[4] Topics in cluster..."
$KAFKA_DIR/bin/kafka-topics.sh --list --bootstrap-server $BOOTSTRAP_SERVER 2>/dev/null

echo ""
echo "[5] Consumer groups..."
$KAFKA_DIR/bin/kafka-consumer-groups.sh --list --bootstrap-server $BOOTSTRAP_SERVER 2>/dev/null

echo ""
echo "=========================================="
