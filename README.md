# Basic SSH Honeypot
A basic SSH honeypot built in Python and containerised in Docker. Part of my blog post: [How to build a malware-collecting SSH honeypot in Python and Docker - Part 1](https://securehoney.net/blog/how-to-build-an-ssh-honeypot-in-python-and-docker-part-1.html).

# Installation

## Port forwarding
Setup port forwarding (e.g. from 22 to 2222)

iptables -A PREROUTING -t nat -p tcp --dport 22 -j REDIRECT --to-port 2222

## Generate server key
ssh-keygen -t rsa -f server.key

## Build
docker build -t basic_honeypot .

## Run
docker run -v ${PWD}:/usr/src/app -p 2222:2222 basic_honeypot
