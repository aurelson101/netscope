import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload={"timestamp":datetime.now(timezone.utc).isoformat(),"level":record.levelname,"logger":record.name,"service":os.getenv("SERVICE_NAME","netscope"),"message":record.getMessage()}
        for key in ("method","path","status","duration_ms","job_id","target","source"):
            if hasattr(record,key):payload[key]=getattr(record,key)
        if record.exc_info:payload["exception"]=self.formatException(record.exc_info)
        return json.dumps(payload,ensure_ascii=False,default=str)


def configure_logging() -> None:
    path=os.getenv("LOG_FILE")
    if not path:return
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    root=logging.getLogger()
    if any(getattr(handler,"baseFilename",None)==str(Path(path).resolve()) for handler in root.handlers):return
    handler=RotatingFileHandler(path,maxBytes=10*1024*1024,backupCount=5,encoding="utf-8");handler.setFormatter(JsonFormatter());root.addHandler(handler);root.setLevel(os.getenv("LOG_LEVEL","INFO"))
