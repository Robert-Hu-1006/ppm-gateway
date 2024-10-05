FROM python:3.13-rc-alpine3.20

USER root

RUN apk add gcc python3-dev musl-dev linux-headers

RUN pip install FFmpeg \
    asyncio \
    aiomqtt \
    pygsheets \
    #--no-binary :all: psutil \
    psutil \
    python-dotenv \
    aiohttp 

RUN mkdir /app
WORKDIR /app
COPY ./ /app/

#COPY ./requirements.txt /app/requirements.txt
#RUN pip install --upgrade pip && \
#    pip install -r requirements.txt

CMD ["python", "streamer.py"] 
