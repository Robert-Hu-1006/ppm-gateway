FROM python:3.13-rc-alpine3.20

USER root

RUN mkdir /app
WORKDIR /app
COPY ./ /app/

RUN apk update && apk upgrade && \
    apk add gcc libc-dev musl-dev glib-dev bluez-dev py3-bluez python3-dev git

RUN pip install git+https://github.com/pybluez/pybluez.git#egg=pybluez
#RUN pip install --upgrade setuptools==57.5.0 wheel pybluez
    
CMD ["python", "rfcommServer.py"]