FROM python:3.13-rc-alpine3.20

USER root
RUN apk update && apk upgrade && \
    apk add --no-cache ffmpeg gcc python3-dev musl-dev linux-headers

RUN pip install --upgrade pip \
    #FFmpeg \
    ffmpeg-python \
    ffprobe-python \
    asyncio \
    aiomqtt \
    pygsheets \
    aiofiles \
    #--no-binary :all: psutil \
    psutil \
    python-dotenv \
    aiohttp \
    aiojobs \
    requests \
    pytz

RUN mkdir /app
WORKDIR /app
COPY ./ /app/

#COPY ./requirements.txt /app/requirements.txt
#RUN pip install --upgrade pip && \
#    pip install -r requirements.txt

CMD ["python", "streamer.py"] 
