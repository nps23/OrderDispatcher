- Add a compose.yaml that can build the backend and database into a single image. Once you have this, update the README. Note: this is not a recommended dev flow since we lose  FastAPI hot reloading, but useful for quick demo purposes. Make sure to note that in the README.
- Update pyproject.toml with all of the exiting deps in this directory right now: ordering_system/order_dispatcher/backend
- In my ingest_mocks directory, I want:
    1. A simple python CLI that accepts a CSV path and calls my POST /ingest/csv endpoint to simulate users uploading a CSV.
    2. A simple python CLI that continously simulates random bursty traffic in a while loop. Burst quantities and sleep between burst should be configurable, but random ranges in each. 
- Take a look at my ingest_mocks directory. I have a polling endpoint on the GraceRouterAPI that is not filled in at the moment. In a prod env, this would poll some external API, but for now, it should just return the api_responses.jsonl in /data. I want you to skeleton a function in ingest_mocks that does this for me. It can keep the file in json format, since I'll just use pydantic to validate it in the endpoint.
- Supporting user-defined extenral API URLs in the polling simulator is overengineering. This is for testing purposes, don't overcomplicate.
- Moving everything from ingest_mocks  to scripts to make it cleaner and adjacent to the pipeline simulator
- Give me a short example on pagination with SQLAlchemy

