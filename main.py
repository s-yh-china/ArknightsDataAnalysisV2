import uvicorn
import colorama

try:
    import winloop
except ImportError:
    winloop = None

from src.config import conf
from src.logger import logger

if __name__ == '__main__':
    if winloop is not None:
        winloop.install()
        logger.info('winloop is enabled!')
    colorama.init()

    is_debug = conf.safe.DEBUG
    uvicorn.run(
        "src.app:app",
        reload=is_debug,
        host=conf.web.host,
        port=conf.web.port,
        workers=conf.web.workers,
        proxy_headers=bool(conf.web.forward_ip),
        forwarded_allow_ips=conf.web.forward_ip,
        log_config={
            "version": 1,
            "disable_existing_loggers": True,
            "formatters": {
                "default": {"()": "uvicorn.logging.DefaultFormatter", "fmt": "%(levelprefix)s %(message)s"},
            },
            "handlers": {
                "default": {"class": "src.logger.InterceptHandler"},
                "access": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["default"],
                    "level": "INFO",
                    "propagate": False,
                },
                "uvicorn.error": {"level": "INFO"},
                "uvicorn.access": {
                    "handlers": ["default"],
                    "level": "INFO",
                    "propagate": False,
                }
            }
        }
    )
