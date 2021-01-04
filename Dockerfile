# set base image (host OS)
FROM python:3.9

# set the working directory in the container
WORKDIR /code

# install make 
RUN apt-get update && apt-get install -y \
  make \
  && rm -rf /var/lib/apt/lists/*
# copy the dependencies file to the working directory
COPY requirements.txt .
# copy the dev-dependencies file to the working directory

COPY requirements-dev.txt .

# install dependencies
RUN pip install -r requirements.txt
# install dev dependencies
RUN pip install -r requirements-dev.txt


# copy the source to container working directory
COPY testslide ./testslide
COPY tests ./tests
COPY util ./util
COPY Makefile .
COPY mypy.ini .

# command to run on container start
CMD ["/usr/bin/make", "tests"]
