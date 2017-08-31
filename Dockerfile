FROM python:3.6.1

ADD requirements.txt /src/requirements.txt
ADD ./flask-restful /src/flask-restful
ADD . /opt/swt/swt-api
WORKDIR /src
RUN pip install -r requirements.txt
WORKDIR /src/flask-restful
RUN python3 setup.py install
RUN mkdir /var/log/swt
RUN mkdir /var/log/swt/api
RUN ["apt-get", "update"]
RUN ["apt-get", "install", "-y", "vim"]

WORKDIR /opt/swt/swt-api

EXPOSE  5000

#- CMD ["python3", "/opt/swt/swt-api/server.py"]
#- to enable shell functions, and redirecting output, use:
#- CMD "python index.py > server.log 2>&1"
#- or
#CMD ["/bin/sh", "-c", "python3 /opt/swt/swt-api/server.py > /var/log/swt/api/server_output.log 2>&1"]

CMD tox -c /opt/swt/swt-api/tox.ini


#     docker run --name swt-api -dit --restart always -v /var/log/swt/api:/var/log/swt/api -p 5001:5000 lfcunha/swt-py-api
#sudo docker run --name swt-api -itd -p 5000:5000 swt-api