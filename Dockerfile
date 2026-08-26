# traktor-nml-tool: a command-line tool, containerised.
#
# There is no server here and nothing listens on a port. The image exists so
# the tool can run on a machine that holds the music library without
# installing Python and three native dependencies on it. Invoke it per run:
#
#   docker run --rm -v /srv/media/Music:/Music:ro -v /srv/traktor:/work \
#     traktor-nml-tool inspect /work/collection.nml
#
FROM python:3.12-slim-bookworm

# fpcalc computes fingerprints; libchromaprint1 is the shared library that
# COMPARES them. pyacoustid needs both, and they ship separately - upstream
# publishes no prebuilt shared library for any platform, which is why the
# fingerprint tier is often dark on desktop installs. Debian packages it, so
# in this image the tier works end to end.
RUN apt-get update \
 && apt-get install --no-install-recommends -y \
      libchromaprint-tools \
      libchromaprint1 \
 && rm -rf /var/lib/apt/lists/*

# lxml is the preferred parser; mutagen reads tags for the disk-scan match
# tiers; pyacoustid drives the optional fingerprint tier. The tool degrades
# rather than failing if any are absent, but a container may as well have them.
RUN pip install --no-cache-dir --root-user-action=ignore \
      lxml \
      mutagen \
      pyacoustid

WORKDIR /app
COPY traktor_nml_tool.py ./
COPY traktor_nml/ ./traktor_nml/

# Bind-mounted collection files are written in place, so the process must own
# them on the host. Override to match the account that owns your library:
#   docker build --build-arg PUID=$(id -u) --build-arg PGID=$(id -g) .
ARG PUID=1000
ARG PGID=1000
RUN groupadd -g "${PGID}" app 2>/dev/null || true \
 && useradd -u "${PUID}" -g "${PGID}" -M -s /usr/sbin/nologin app 2>/dev/null || true
USER ${PUID}:${PGID}

# /work holds the collection and any reports; mount the library separately.
WORKDIR /work
ENTRYPOINT ["python", "/app/traktor_nml_tool.py"]
CMD ["--help"]
