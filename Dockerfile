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
    libpython2.7-dev

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

# Copy file starting tornado + celery (worker + beat)
COPY bin/start.sh /bin/start.sh

# Start the application (might move this to supervisord in the future)
CMD ["/bin/start.sh"]
