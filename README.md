# Basic SSH Honeypot
A basic SSH honeypot built with Python and containerised in Docker. 

Forked from sjbell, read his blog about the original here: [How to build an SSH honeypot in Python and Docker - Part 1](https://securehoney.net/blog/how-to-build-an-ssh-honeypot-in-python-and-docker-part-1.html).

Uses the [Paramiko](https://github.com/paramiko/paramiko) Python SSH protocol library.

# Installation

## Port forwarding
We will not use port forwarding in this instance, as collection of public IPs is preferred over potential sandbox breaches.

## Generate server key
```
ssh-keygen -t rsa -f server.key
```
## Build
```
docker build -t basic_honeypot .
```
## Run
```
docker run -v ${PWD}:/usr/src/app -p 22:22 basic_honeypot
```
Logs are recorded in the auto-generated ```ssh_honeypot.log``` file
