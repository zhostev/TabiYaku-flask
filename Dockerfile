# 选择基础镜像。如需更换，请到[dockerhub官方仓库](https://hub.docker.com/_/alpine?tab=tags)自行选择后替换。
# 已知 alpine 镜像与 pytorch 有兼容性问题会导致构建失败，如需使用 pytorch 请务必按需更换基础镜像。
FROM alpine:3.13

# 容器默认时区为 UTC，如需使用上海时间请启用以下时区设置命令
# RUN apk add tzdata && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo Asia/Shanghai > /etc/timezone

# 使用 HTTPS 协议访问容器云调用证书安装
RUN apk add ca-certificates

# 安装依赖包，如需其他依赖包，请到 alpine 依赖包管理查找。
# 选用国内镜像源以提高下载速度
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

# 安装依赖到指定的 /install 文件夹
# 选用国内镜像源以提高下载速度
RUN pip config set global.index-url http://mirrors.cloud.tencent.com/pypi/simple \
    && pip config set global.trusted-host mirrors.cloud.tencent.com \
    && pip install --upgrade pip \
    && pip install --user -r requirements.txt

# 暴露端口。
# 此处端口必须与「服务设置」-「流水线」以及「手动上传代码包」部署时填写的端口一致，否则会部署失败。
EXPOSE 80

# 执行启动命令
CMD ["python3", "run.py", "0.0.0.0", "80"]