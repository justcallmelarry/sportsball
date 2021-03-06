FROM python:3-slim

WORKDIR /usr/src/app

COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# RUN apt-get update
# RUN apt-get -y install cron
# RUN apt-get -y install procps

# ADD /settings/crontab /etc/cron.d/banana-cron
# RUN chmod 0644 /etc/cron.d/banana-cron
# RUN touch /var/log/cron.log
# RUN /usr/bin/crontab /etc/cron.d/banana-cron

# CMD ./tools/run.sh
CMD ["python", "./sportsball.py"]
