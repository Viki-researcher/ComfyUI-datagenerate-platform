#!/bin/bash
# PostgreSQL 安装与初始化脚本
# 适用于 Ubuntu/Debian 系统

set -e

echo "=== 开始安装 PostgreSQL ==="

# 安装 PostgreSQL
sudo apt update
sudo apt install -y postgresql postgresql-contrib

# 启动 PostgreSQL 服务
sudo systemctl start postgresql
sudo systemctl enable postgresql

echo "=== PostgreSQL 安装完成 ==="

# 设置 postgres 用户密码
echo "请设置 postgres 用户密码："
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'postgres';"

# 创建数据库
sudo -u postgres psql -c "CREATE DATABASE data_generation OWNER postgres;"

echo "=== 数据库创建完成 ==="
echo "数据库: data_generation"
echo "用户: postgres"
echo "密码: postgres"
echo ""
echo "连接字符串: host=127.0.0.1 port=5432 user=postgres dbname=data_generation"
