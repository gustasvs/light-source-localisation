# telosb-mansos-docker

## Setup

1. Build the docker image

``` sh
docker build . -t mansos-telosb
```

2. Go to your C code repo and adapt Makefile to reference MansOS inside the container. MansOS is located in `/srv/mans_os` in the container. Example makefile:

``` makefile
SOURCES = main.c

APPMOD = PD1

PROJDIR = $(CURDIR)
ifndef MOSROOT
  MOSROOT = /srv/mans_os
  #MOSROOT = $(PROJDIR)/../MansOS
endif

# Include the main makefile
include ${MOSROOT}/mos/make/Makefile
```

3. Build your project

``` sh
# Go to your project root
docker run -v ${PWD}:/srv/repo mansos-telosb bash -c "cd /srv/repo && make telosb"
```

4. Flash your project

``` sh
docker run --device=/dev/ttyUSB0 -v ${PWD}:/srv/repo mansos-telosb bash -c "cd /srv/repo && make telosb upload"
```

## Notes

- Allegedly the flashing doesn't actually need MSP430 toolchain
- The flashing command might be different for different OS. Flashing might not work on MacOS.
- If you need to unpin the commit of the repo and the `RUN git apply --ignore-space-change --ignore-whitespace /srv/patch0.patch` fails, you will need to provide your own patch. Basically you need to remove `sudo apt install` from those 2 locations defined in `remove-hardcoded-apt-install.patch`
  - How to make a patch? Clone MansOS repo, do the changes, stage the changes (but do not commit) and then run `git diff --staged` and copy this output into `remove-hardcoded-apt-install.patch` file
- If something doesn't work, remove `build/` folder and try again
