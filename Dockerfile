FROM python:2.7

### Install dependencies

RUN apt-get update \ 
    && apt-get install -y build-essential  \
    git \
    lsb-release \
    python-apt \
    python-pip \
    python-pycurl \
    python-virtualenv \
    python2.7-dev \
    sysfsutils \
    python3 \
    python3-yaml \
    python3-setproctitle \
    python3-zmq \
    libyaml-dev \
    libpython2.7-dev \
    supervisor

### Install application

# Install code dependencies
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

# Setup working directory
WORKDIR /app

# Copy source code
COPY app /app

# App configuration file
COPY etc/backend.cfg /etc/linaro/kernelci-backend.cfg

# Celery configuration
RUN mkdir /var/log/celery /var/run/celery
COPY etc/celery.cfg /etc/linaro/kernelci-celery.cfg

# Setup supervisor to start both Celery and Tornado processes
RUN mkdir -p /var/log/supervisor
COPY etc/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Start supervisord
CMD ["/usr/bin/supervisord"]
