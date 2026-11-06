FROM quay.io/jupyterhub/jupyterhub:5.2.1
USER root
RUN pip install --no-cache-dir oauthenticator dockerspawner
COPY jupyterhub_config.py /srv/jupyterhub/jupyterhub_config.py
USER jupyterhub
WORKDIR /srv/jupyterhub
CMD ["jupyterhub", "-f", "/srv/jupyterhub/jupyterhub_config.py"]
