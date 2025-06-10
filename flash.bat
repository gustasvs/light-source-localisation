@echo off
REM Build firmware (optional, comment out if already built)
docker run -v "/c/python123/university-stuff/bezvadu sensoru tikli/light-source-localisation/sensor:/srv/repo" mansos-telosb bash -c "cd /srv/repo && make telosb"

REM Flash firmware to TelosB/Tmote Sky

docker run --device=/dev/ttyUSB0 -v "/c/python123/university-stuff/bezvadu sensoru tikli/light-source-localisation/sensor:/srv/repo" mansos-telosb bash -c "cd /srv/repo && make telosb upload"