FROM ubuntu:22.04

RUN apt update
RUN apt install -y \
    # MSP430 (telosb) build dependencies
    gcc-msp430 \
    binutils-msp430 \
    msp430-libc msp430mcu \
    # General dependencies
    git \
    make \
    python3 \
    python-is-python3 \
    python3-pip
RUN pip3 install pyserial ply wxtools
RUN git clone https://github.com/edi-riga/MansOS.git /srv/mans_os
WORKDIR /srv/mans_os
# NOTE: Pinning repo to this commit, so that our patch doesn't break.
# NOTE: A smarter script that replaces the content is probably a better idea but patching is easier
RUN git checkout 4a606f33e3eaf22ab98975183d62637e8ca0f2a8
COPY remove-hardcoded-apt-install.patch /srv/patch0.patch
# The flags are added for more robust patching
# See https://stackoverflow.com/questions/4770177/git-apply-fails-with-patch-does-not-apply-error
RUN git apply --ignore-space-change --ignore-whitespace /srv/patch0.patch
COPY Makefile /srv/Makefile
WORKDIR /srv/
RUN make --trace setup telosb


# docker run --device=/COM3 -v  "/c/python123/university-stuff/bezvadu sensoru tikli/light-source-localisation/sensor:/srv/repo" mansos-telosb bash -c "cd /srv/repo && make telosb upload"
