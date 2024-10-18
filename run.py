# run.py
import sys
from wxcloudrun import app

# 启动Flask Web服务
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python3 run.py <host> <port>")
        sys.exit(1)
    host = sys.argv[1]
    try:
        port = int(sys.argv[2])
    except ValueError:
        print("Port must be an integer.")
        sys.exit(1)
    app.run(host=host, port=port, debug=True)