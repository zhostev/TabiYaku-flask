# 选择基础镜像
FROM alpine:3.13

# 安装依赖包和证书
RUN apk add --no-cache \
    ca-certificates \
    python3 \
    py3-pip \
    mysql-client \
    build-base \
    mariadb-connector-c-dev \
    && rm -rf /var/cache/apk/*

# 设置 pip 镜像源
RUN pip config set global.index-url http://mirrors.cloud.tencent.com/pypi/simple && \
    pip config set global.trusted-host mirrors.cloud.tencent.com

# 拷贝当前项目到 /app 目录下（.dockerignore 中文件除外）
COPY . /app

# 设置工作目录
WORKDIR /app

# 安装 Python 依赖
RUN pip install --upgrade pip && \
    pip install --user -r requirements.txt

# 设置环境变量 PATH
ENV PATH=/root/.local/bin:$PATH

# 创建上传文件夹
RUN mkdir -p /app/uploads

# 暴露端口
EXPOSE 80

# 执行启动命令
CMD ["python3", "run.py", "0.0.0.0", "80"]