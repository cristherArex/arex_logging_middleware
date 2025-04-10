from enum import Enum
import logging
from typing import Optional
import uuid
import os

from fastapi import Request
import httpx


class LoggingAPIConfig:
    _url = None

    @classmethod
    def configure_url(cls, url: str):
        cls._url = url
        print(f"Logging API URL set to: {cls._url}")

    @classmethod
    def get_url(cls):
        if cls._url is None:
            raise ValueError("Logging API URL has not been set. Call 'configure_logging_api' first.")
        return cls._url
    

# Create the 'es_logs' directory and set up the logging fallback file
LOG_DIR = os.path.join(os.getcwd(), "es_logs")
LOG_FILE = os.path.join(LOG_DIR, "logging_fallback.log")

if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.ERROR
)


class LogLevelEnum(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


async def url_check():
    logging_api_url = LoggingAPIConfig.get_url()
    if not logging_api_url:
        return {
            "Error": "URL must be set for usage."
        }


async def log_context(request: Request):
    execution_uuid = request.headers.get('X-Execution-UUID', str(uuid.uuid4()))

    # token = request.headers.get('authorization')
    # if not token:
    #     raise ValueError("Authorization token is missing from the headers.")
    
    return {
        "execution_uuid": execution_uuid,
        "request": request,
        # "token": token,
    }


async def logging_es(
    level: LogLevelEnum, 
    message: str, 
    user_id: int, 
    context: dict,
    status: Optional[str] = None,
    process_info: Optional[dict] = None
):
    await url_check()
    execution_uuid = context['execution_uuid']
    request = context['request']
    # token = context['token']

    # headers = {
    #     "Authorization": token
    # }

    headers_content = dict(request.headers)

    log_entry = {
        "execution_UUID": execution_uuid,
        "user_id": user_id,
        "host": headers_content["host"],
        # "authorization": headers_content["authorization"],
        "ip": request.client.host,
        "port": request.client.port,
        "method": request.method,
        "path": request.url.path,
        "level": level.value,  # Ensure enum is a string
        "message": message
    }

    if status is not None:
        log_entry["status"] = status
    if process_info is not None:
        log_entry["process_info"] = process_info

    try:
        async with httpx.AsyncClient(verify=False) as client:
            logging_api_url = LoggingAPIConfig.get_url()
            # response = await client.post(logging_api_url, headers=headers, json=log_entry)
            response = await client.post(logging_api_url, json=log_entry)
            if response.status_code != 200:
                print(f"Failed to log to API. Status code: {response.status_code}. Log Entry: {log_entry}")
                raise ValueError(
                    f"Failed to log to API. Error: {str(response.status_code)} -- {response}"
                )
            return response
    except Exception as e:
        print(f"Exception occurred while logging to API: {e}. Log Entry: {log_entry}")
        raise ValueError(f"Failed to log to API. Error: {str(e)}")
