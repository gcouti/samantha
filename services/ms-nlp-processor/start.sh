#!/bin/bash

# Run database migrations
python -c "from src.database.database import init_db; init_db()"

# Start the application
uvicorn src.api:app --host 0.0.0.0 --port 8080
