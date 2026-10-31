# 打印服务镜像：Python + LibreOffice（转 PDF）+ 模板用到的字体
# 腾讯云函数 Web 函数要求监听 9000 端口；只有 /tmp 可写
ARG BASE=python:3.12-slim-bookworm
FROM ${BASE}

RUN apt-get update && apt-get install -y --no-install-recommends \
        libreoffice-writer-nogui \
        fonts-liberation fonts-crosextra-carlito fonts-crosextra-caladea \
        fonts-texgyre fonts-dejavu-core fonts-wqy-microhei fontconfig tzdata \
    && rm -rf /var/lib/apt/lists/*

# 模板里的 Palatino Linotype 没有免费版，用字形接近的 TeX Gyre Pagella 代替
COPY deploy/fonts.conf /etc/fonts/local.conf
RUN fc-cache -f

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY service service
COPY templates/official templates/official
COPY templates/hu templates/hu

ENV HOME=/tmp PORT=9000 PYTHONUNBUFFERED=1
EXPOSE 9000
# 预热：构建时先启动一次 LibreOffice，减少冷启动时间
RUN soffice -env:UserInstallation=file:///tmp/lo-profile --headless --terminate_after_init || true
CMD ["python", "-m", "service.app"]
