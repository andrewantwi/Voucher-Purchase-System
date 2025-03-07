import logging


class Log:
    
    
    __log_level = {
        "info": logging.INFO,
        "debug": logging.DEBUG,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
        "warning": logging.WARNING
    }
    
    
    
    def __init__(self, log_level: str = "info"):
        
        self__formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%d-%b-%y %H:%M:%S")
        self.__handler = logging.StreamHandler()
        self.__handler.setFormatter(self__formatter)
        self.__logger = logging.getLogger(__name__)
        self.__logger.setLevel(self.__log_level.get(log_level.lower()))
        self.__logger.addHandler(self.__handler)
        
    
    
    def info(self, message: str) -> None:
        self.__logger.info(message)
        
    
    def debug(self, message: str) -> None:
        self.__logger.debug(message)
        
    def error(self, message: str) -> None:
        self.__logger.error(message)
        