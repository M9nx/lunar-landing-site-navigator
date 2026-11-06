FROM quay.io/jupyterhub/jupyterhub:5.2.1
USER root
RUN pip install --no-cache-dir oauthenticator dockerspawner
COPY hub_url_config.py jupyterhub_config.py /srv/jupyterhub/
USER jupyterhub
WORKDIR /srv/jupyterhub
CMD ["jupyterhub", "-f", "/srv/jupyterhub/jupyterhub_config.py"]
