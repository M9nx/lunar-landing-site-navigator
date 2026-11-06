FROM quay.io/jupyterhub/jupyterhub:5.2.1
USER root
RUN pip install --no-cache-dir oauthenticator dockerspawner
COPY hub_url_config.py jupyterhub_config.py /srv/jupyterhub/
WORKDIR /srv/jupyterhub
# Base image has no jupyterhub passwd entry; Hub runs as root here (Docker socket access).
CMD ["jupyterhub", "-f", "/srv/jupyterhub/jupyterhub_config.py"]
