# Python Semantic Matching Service

This is a proof-of-concept implementation of a semantic matching service using Python. 
The idea behind this service is to create a uniform interface for exchanging semantic matches, that are stored
decentralized across multiple semantic matching services. 

> [!warning]
> This project is **not** about finding semantic matches or semantic similarities, it rather requires these as input.

## Structure
The project is structured as follows:
- `algorithm.py` implements the decentralized match aggregation algorithm
- `service.py` offers the service implementation using the [FastAPI](https://fastapi.tiangolo.com/) framework.
  Note that you can find a detailed interface description (OpenAPI) by [running](#how-to-use) the server locally and 
  navigating to `<endpoint>/docs`.

## How to Use
There are two main options to run:

### Run `service.py`
You need a working Python installation (3.11 or higher).
- Clone this repository
- Create a new virtual environment: `python3 -m venv venv` (Note that the service is only tested on Linux systems)
- Activate the virtual environment: `source venv/bin/activate`
- Install the package: `pip install .`
- Copy the `config.ini.default` to `config.ini` and adapt the fields as necessary
- Run the service: `python3 semantic_matcher/service.py`

### Run via Docker
To run via docker, you obviously need a working docker installation.
- Clone the repository
- Copy the `config.ini.default` to `config.ini` and adapt the fields as necessary
- Choose one of the two options below:

**Option 1:** Build and run manually

In the project root directory:
```commandline
docker build -t semantic_matching_service .
```
```commandline
docker run -d -p 8000:8000 semantic_matching_service
```

> [!note]
> You may have to change the port in the run command if you changed it in your `config.ini`. 

**Option 2:** Use the docker compose file

In the project root directory:
```commandline
docker compose up
```

> [!note]
> If you changed your `config.ini`, you might need to adapt the respective fields in the `compose.yaml`. 
