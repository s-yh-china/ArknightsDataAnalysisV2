from src.config.config import ConfigData
from src.config.config_model import ServerConfig

ConfigData.init()
conf: ServerConfig = ServerConfig.model_validate(ConfigData.data)
