# 创建应用实例
import sys
from wxcloudrun import app

# 启动 Flask Web 服务，接受命令行参数指定主机和端口
if __name__ == '__main__':
    host = sys.argv[1] if len(sys.argv) > 1 else '0.0.0.0'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    app.run(debug=True,host='0.0.0.0', port=port)
    