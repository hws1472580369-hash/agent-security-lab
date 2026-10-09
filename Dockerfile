FROM python:3.13-slim

# 容器内不要写 .pyc、日志实时输出（方便 docker logs 观察）
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 依赖单独一层，改代码时不用重装依赖
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 只把运行网关需要的代码和资源放进镜像
COPY src ./src
COPY data ./data

# 用非 root 用户跑网关：就算被攻破，容器内也没有 root
RUN useradd --create-home --uid 10001 gateway \
    && chown -R gateway:gateway /app
USER gateway

EXPOSE 8001

# 先初始化数据库（可重复执行，不会清空已有数据），再启动网关
CMD ["sh", "-c", "python -m src.database.models && python -m src.mcp.server"]
