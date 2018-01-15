FROM ubuntu:xenial

RUN apt-get update && apt-get install -y collectd

RUN apt-get update && apt-get install -y libunwind8 liblttng-ust0 libcurl3 libssl1.0.0 libuuid1 \
    libkrb5-3 zlib1g libicu55 wget apt-transport-https apt-utils rsyslog

RUN repoPkg=azure-repoclient-https-noauth-public-xenial_1.0.2-47_amd64.deb && \
	wget --no-check-certificate https://apt-mo.trafficmanager.net/repos/azurecore/pool/main/a/azure-repoclient-https-noauth-public-xenial/$repoPkg && \
	dpkg -i $repoPkg && \
	apt-get update && \
    apt-get install -y metricsext && \
	apt-get install -y azure-mdm-metrics && \
	apt-get install -y azure-mdm-statsd && \
	apt-get install -y python-pip

RUN python -m pip install -U pip && pip install statsd requests psutil

RUN apt-get install -y vim

RUN repoPkg=azure-repoclient-https-noauth_0.1.0-2_amd64.deb && \
	wget --no-check-certificate https://apt-mo.trafficmanager.net/repos/azurecore/pool/main/a/azure-repoclient-https-noauth/$repoPkg && \
	dpkg -i $repoPkg && \
	apt-get update && \
	# forceSilent='-o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"' && \
	apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" azure-mdsd

# COPY azure-mdm-statsd_0.6.7-build.dev_amd64.deb /tmp/azure-mdm-statsd_0.6.7-build.dev_amd64.deb

# RUN apt install -y /tmp/azure-mdm-statsd_0.6.7-build.dev_amd64.deb

COPY mdm /etc/default/mdm

COPY cert.pem /etc/mdm/cert.pem

COPY key.pem /etc/mdm/key.pem

COPY mdsd /etc/default/mdsd

COPY mdsd.xml /etc/mdsd.d/mdsd.xml

RUN mkdir /opt/collector

COPY collect.py /opt/collector/collect.py

# COPY write_mdm.conf /etc/collectd/collectd.conf.d/write_mdm.conf

COPY mdmstatsd.conf /etc/mdmstatsd/mdmstatsd.conf

COPY publish /home/SignalR

WORKDIR /home/SignalR

# COPY collectd.conf /etc/collectd/collectd.conf.d/my.conf

# COPY types.db /usr/share/collectd/types.db

COPY run.sh /run.sh

EXPOSE 5001

CMD ["/bin/bash", "/run.sh"]
