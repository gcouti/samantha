#!/bin/bash

# Run database migrations
cd services/ms-nlp-processor/src
pwd
python -c "from database.database import init_db; init_db()"

# Start the application
uvicorn api:app --host 0.0.0.0 --port 8080
