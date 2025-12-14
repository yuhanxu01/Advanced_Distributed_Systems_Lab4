#!/bin/bash

# Kafka 安装脚本 - 在 node0, node1, node2 上运行
# 使用 KRaft 模式（不需要 Zookeeper）

set -e

echo "=== Installing Java and Kafka ==="

# 安装 Java
sudo apt-get update
sudo apt-get install -y openjdk-17-jdk wget

# 下载 Kafka
cd /opt
sudo wget https://downloads.apache.org/kafka/3.7.0/kafka_2.13-3.7.0.tgz
sudo tar -xzf kafka_2.13-3.7.0.tgz
sudo mv kafka_2.13-3.7.0 kafka
sudo rm kafka_2.13-3.7.0.tgz

# 创建数据目录
sudo mkdir -p /var/kafka-logs
sudo chown -R $USER:$USER /opt/kafka
sudo chown -R $USER:$USER /var/kafka-logs

echo "=== Kafka installed at /opt/kafka ==="
echo "Now run the configuration script with your node ID"
