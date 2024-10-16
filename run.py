# 创建应用实例
import sys
from wxcloudrun import app

# 启动 Flask Web 服务
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 run.py <host> <port>")
        sys.exit(1)
    host = sys.argv[1]
    port = int(sys.argv[2])
    app.run(host=host, port=port)