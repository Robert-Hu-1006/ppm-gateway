FROM python:3.13-rc-alpine3.20

USER root

RUN mkdir /app
WORKDIR /app
COPY ./ /app/

#COPY ./requirements.txt /app/requirements.txt
#RUN pip install --upgrade pip && \
#    pip install -r requirements.txt

#RUN pip install aioredis redis>=4.2.0rc1 hiredis
#RUN pip install docker
#RUN pip install docxtpl
#RUN pip install Jinja2
#RUN pip install pandas
#RUN pip install openpyxl 

#RUN pip install --upgrade pip setuptools
#RUN pip install setuptools --upgrade
#RUN apk add gcc

RUN pip install pygsheets aiomysql \
asyncio \
python-dotenv \
#prometheus-client \
aiohttp \
aiohttp_tokenauth \
#aiojobs \
aiohttp_cors \
logging 
#pybase64 \
#aioredis \
#aiomqtt \
#cryptography 

CMD ["python", "apiserver.py"]
