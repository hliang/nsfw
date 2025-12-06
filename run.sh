#!/bin/sh
ARG1=$1

# 数据库路径
DB_PATH="/opt/zhiyuan/app/data/db"

# 启动redis
runRedis(){
    redis-server app/config/redis.conf --daemonize yes
    # 检查 Redis 是否启动成功
    if [ $? -eq 0 ]; then
        echo "Redis started successfully."
    else
        echo "Failed to start Redis."
        exit 1
    fi
}

# 检查数据库路径是否存在，如果不存在则创建
exist_db(){
    if [ ! -d "$DB_PATH" ]; then
        mkdir -p "$DB_PATH"
    fi
}

# 启动定时任务
runScheduler(){
    # 创建日志目录
    mkdir -p ./app/data/logs
    # 检查任务中是否存在app.utils.cron的进程，如果不存在则启动
    pgrep -f "python3 -m app.utils.cron" > /dev/null
    if [ $? -eq 0 ]; then
        echo "Scheduler is already running."
    else
        # 后台启动任务
        nohup python3 -m app.utils.cron > ./app/data/logs/app_cron.log 2>&1 &
    fi
}


# 启动主进程
runMain(){
    # 获取环境变量WORKERS
    WORKERS=${WORKERS}
    # 判断变量是否存在
    if [ -z "$WORKERS" ]; then
        WORKERS=1
    fi
    # 启动主进程
    source myenv/bin/activate
    # runScheduler
    # 执行数据库迁移
    # alembic upgrade head
    uvicorn app.main:app --workers ${WORKERS} --host 0.0.0.0 --port 6086 --log-config app/logging_config.ini
}

# 获取第一个参数，如果不存在，则执行下面的命令，如果为dev则执行另外的命令
if [ -z "$ARG1" ]; then
    runMain
elif [ "$ARG1" = "dev" ]; then
    # exist_db
    echo "Running in development mode..."
    source myenv/bin/activate
    # 执行数据库迁移
    # alembic upgrade head
    # runScheduler
    uvicorn app.main:app --reload --host 0.0.0.0 --port 6086 --log-config app/logging_config.ini
else
    echo "Unknown argument: $ARG1"
    echo "Usage: $0 [dev]"
    exit 1
fi