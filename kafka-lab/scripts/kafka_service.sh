#!/bin/bash

# Kafka 服务管理脚本
# 在每个 broker 节点上运行

KAFKA_DIR="/opt/kafka"
CONFIG_FILE="$KAFKA_DIR/config/kraft/server.properties"
LOG_FILE="/tmp/kafka.log"

case "$1" in
    start)
        echo "Starting Kafka..."
        nohup $KAFKA_DIR/bin/kafka-server-start.sh $CONFIG_FILE > $LOG_FILE 2>&1 &
        sleep 3
        if pgrep -f kafka.Kafka > /dev/null; then
            echo "✓ Kafka started successfully (PID: $(pgrep -f kafka.Kafka))"
            echo "  Log file: $LOG_FILE"
        else
            echo "✗ Failed to start Kafka. Check $LOG_FILE"
        fi
        ;;
    stop)
        echo "Stopping Kafka..."
        $KAFKA_DIR/bin/kafka-server-stop.sh
        sleep 2
        if pgrep -f kafka.Kafka > /dev/null; then
            echo "  Force killing..."
            pkill -9 -f kafka.Kafka
        fi
        echo "✓ Kafka stopped"
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        if pgrep -f kafka.Kafka > /dev/null; then
            echo "✓ Kafka is running (PID: $(pgrep -f kafka.Kafka))"
        else
            echo "✗ Kafka is NOT running"
        fi
        ;;
    log)
        tail -f $LOG_FILE
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|log}"
        exit 1
        ;;
esac
