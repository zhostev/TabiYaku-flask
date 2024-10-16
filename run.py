# 创建应用实例
import sys
from wxcloudrun import app

# 启动 Flask Web 服务
if __name__ == '__main__':
    host = sys.argv[1] if len(sys.argv) > 1 else '0.0.0.0'
    port = sys.argv[2] if len(sys.argv) > 2 else '80'
    app.run(host=host, port=port)