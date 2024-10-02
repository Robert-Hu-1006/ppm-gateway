FROM python:3.13-rc-alpine3.20

USER root
RUN pip install FFmpeg
RUN pip install asyncio
RUN pip install aiomqtt
RUN pip install pygsheets
RUN pip install psutil
RUN pip install python-dotenv
RUN pip install aiohttp
RUN mkdir /app
WORKDIR /app
COPY ./ /app/

#COPY ./requirements.txt /app/requirements.txt
#RUN pip install --upgrade pip && \
#    pip install -r requirements.txt


CMD python streamer.py 
