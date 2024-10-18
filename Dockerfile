# 使用基础镜像 Alpine 3.13
FROM alpine:3.13

# 使用 HTTPS 协议访问容器云调用证书安装
RUN apk add --no-cache ca-certificates

# 选用国内镜像源以提高下载速度，并安装必要依赖
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tencent.com/g' /etc/apk/repositories \
    && apk add --update --no-cache \
        python3 \
        py3-pip \
        mysql-client \
        build-base \
        linux-headers \
        mariadb-connector-c-dev \
    && rm -rf /var/cache/apk/*

# 拷贝当前项目到 /app 目录下（.dockerignore 中文件除外）
COPY . /app

# 设定当前的工作目录
WORKDIR /app

# 设置 pip 镜像源并安装依赖
RUN pip config set global.index-url http://mirrors.cloud.tencent.com/pypi/simple \
    && pip config set global.trusted-host mirrors.cloud.tencent.com \
    && pip install --upgrade pip \
    && pip install --user -r requirements.txt

# 确保 /app/uploads 目录存在
RUN mkdir -p /app/uploads

# 添加 /root/.local/bin 到 PATH
ENV PATH=/root/.local/bin:$PATH

# 暴露端口
EXPOSE 80

# 执行启动命令
# CMD ["python3", "run.py", "0.0.0.0", "80"]
CMD ["gunicorn", "--bind", "0.0.0.0:80", "run:app"]