# Use the official Alpine Linux as the base image
FROM python:3.11-alpine

# Install Git
RUN apk update && apk add --no-cache git

# Set the working directory in the container
WORKDIR /app

# Copy the package files to the working directory
COPY . .

# Install Python dependencies
RUN python -m pip install --upgrade pip
RUN pip install .

# Set PYTHONPATH to the app directory
ENV PYTHONPATH=/app

# Expose the port that FastAPI will run on
EXPOSE 8000

# Command to run the FastAPI server
CMD ["python", "semantic_matcher/service.py"]
