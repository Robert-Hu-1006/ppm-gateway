FROM python:3.13-rc-alpine3.20

USER root

RUN mkdir /app
WORKDIR /app
COPY ./ /app/

COPY ./requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

#RUN pip install \
#asyncio \
#python-dotenv \
#netifaces2 \
#prometheus-client \
#aiohttp \
#aiohttp_tokenauth \
#aiojobs \
#aiohttp_cors \
#logging 

CMD ["python", "apiserver.py"]
