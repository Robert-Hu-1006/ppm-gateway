FROM python:3.13-rc-alpine3.20
#FROM python:3.11-rc-alpine3.16

USER root
RUN pip install FFmpeg

RUN pip install ffmpeg-python
#RUN pip install python-ffmpeg
RUN pip install pygsheets
    
RUN mkdir /app
WORKDIR /app
COPY ./ /app/

#COPY ./requirements.txt /app/requirements.txt
#RUN pip install --upgrade pip && \
#    pip install -r requirements.txt


CMD python streamer.py 
