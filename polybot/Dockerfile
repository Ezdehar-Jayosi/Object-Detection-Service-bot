# Use an official Python runtime as a parent image
FROM python:3.9-alpine

# Set the working directory to /app
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /app
COPY . /app
COPY requirements.txt .
# Install any needed packages specified in requirements.txt
RUN apk --no-cache add build-base libressl-dev musl-dev && \
    pip install --upgrade pip && \
    pip install -r requirements.txt
COPY . .
# Run app.py when the container launches
CMD ["python", "app.py"]