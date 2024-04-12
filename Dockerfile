FROM python:3.9.19-alpine

LABEL authors="张伟"

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt requirements.txt

# 加入pip源
ENV pypi https://mirrors.aliyun.com/pypi/simple/

# 更换APK源
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories

# 安装依赖
RUN pip3 install --no-cache-dir -r requirements.txt -i ${pypi}

# 设置时区
RUN apk add --no-cache --virtual mypacks tzdata \
            && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
            apk del mypacks

# 复制代码
COPY main.py main.py

# 启动
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]