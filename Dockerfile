FROM nginx:1.13

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

# Copy source code
COPY app /app

# App configuration file
COPY etc/kernelci-backend.cfg /etc/linaro/kernelci-backend.cfg

# Celery configuration
RUN mkdir /var/log/celery /var/run/celery
COPY etc/kernelci-celery.cfg /etc/linaro/kernelci-celery.cfg

#TODO
# start celery process when container starts

### Nginx configuration

# Create root directory
RUN mkdir -p /usr/share/nginx/html/kernelci \
    && chown www-data:www-data /usr/share/nginx/html/kernelci

# Backend configuration
COPY etc/backend-nginx.conf /etc/nginx/conf.d/kernelci.conf

# Upstream definitions
COPY etc/backend-upstreams.conf /etc/nginx/conf.d/backend-upstreams.conf

# Proxy / Proxy-cache
COPY etc/backend-proxy*.conf /etc/nginx/custom/

#TODO
# - maintenance configuration + page
# - backup (in another service)
# - firewall (in another service => proxy)
