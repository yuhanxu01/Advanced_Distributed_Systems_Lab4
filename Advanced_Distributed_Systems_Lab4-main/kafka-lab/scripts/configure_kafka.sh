#!/bin/bash

# Kafka KRaft 配置脚本
# 用法: ./configure_kafka.sh <node_id>
# node_id: 1 for node0, 2 for node1, 3 for node2

NODE_ID=$1

if [ -z "$NODE_ID" ]; then
    echo "Usage: ./configure_kafka.sh <node_id>"
    echo "  node_id: 1 (for node0), 2 (for node1), 3 (for node2)"
    exit 1
fi

# 节点 IP 配置 - 根据你的 GCP 节点
NODE0_IP="10.128.0.5"
NODE1_IP="10.128.0.2"
NODE2_IP="10.128.0.3"

KAFKA_DIR="/opt/kafka"
CONFIG_FILE="$KAFKA_DIR/config/kraft/server.properties"

# 备份原配置
cp $CONFIG_FILE ${CONFIG_FILE}.bak

# 生成集群 ID (只需在一个节点上生成一次，然后所有节点用同一个)
CLUSTER_ID="MkU3OEVBNTcwNTJENDM2Qk"

cat > $CONFIG_FILE << EOF
# KRaft 配置文件
process.roles=broker,controller
node.id=${NODE_ID}
controller.quorum.voters=1@${NODE0_IP}:9093,2@${NODE1_IP}:9093,3@${NODE2_IP}:9093

# 监听器配置
listeners=PLAINTEXT://:9092,CONTROLLER://:9093
inter.broker.listener.name=PLAINTEXT
advertised.listeners=PLAINTEXT://$(hostname -I | awk '{print $1}'):9092
controller.listener.names=CONTROLLER
listener.security.protocol.map=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT

# 日志目录
log.dirs=/var/kafka-logs

# 集群设置
num.network.threads=3
num.io.threads=8
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600

# 日志设置
num.partitions=3
num.recovery.threads.per.data.dir=1
offsets.topic.replication.factor=3
transaction.state.log.replication.factor=3
transaction.state.log.min.isr=2
log.retention.hours=168
log.segment.bytes=1073741824
log.retention.check.interval.ms=300000
EOF

echo "=== Configuration complete for Node $NODE_ID ==="
echo ""
echo "Now format the storage directory with:"
echo "  /opt/kafka/bin/kafka-storage.sh format -t $CLUSTER_ID -c $CONFIG_FILE"
echo ""
echo "Then start Kafka with:"
echo "  /opt/kafka/bin/kafka-server-start.sh -daemon $CONFIG_FILE"
