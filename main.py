import uvicorn
import colorama

try:
    import winloop
except ImportError:
    winloop = None

from src.api.datas import ConfigData
from src.logger import logger

if __name__ == '__main__':
    if winloop is not None:
        winloop.install()
        logger.info('winloop is enabled!')
    colorama.init()

    is_debug = ConfigData.get_safe()['DEBUG']
    web_config = ConfigData.get_web()
    uvicorn.run(
        "src.app:app",
        reload=is_debug,
        host=web_config['host'],
        port=web_config['port'],
        workers=web_config['workers'],
        proxy_headers=bool(web_config['forward-ip']),
        forwarded_allow_ips=web_config['forward-ip'],
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
                },
                "sqlalchemy.engine": {
                    "handlers": ["default"],
                    "propagate": False,
                }
            }
        }
    )
