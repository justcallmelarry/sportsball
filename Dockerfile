FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update
RUN apt-get -y install cron

COPY docker-cron ./
ADD docker-cron /etc/cron.d/banana-cron
RUN chmod 0644 /etc/cron.d/banana-cron
RUN touch /var/log/cron.log
RUN /usr/bin/crontab /etc/cron.d/banana-cron

COPY . .

CMD cron && tail -f /var/log/cron.log
CMD [ "python", "./google.py" ]
