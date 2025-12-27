# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code to the working directory
COPY ./src /app/src

# Copy the startup script
COPY start.sh .

# Make the startup script executable
RUN chmod +x start.sh

# Command to run the application
CMD ["./start.sh"]
