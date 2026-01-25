# Centralized logging setup
import logging
import os

def setup_logging(level=logging.INFO):
    '''
    Sets up centralized logging for the PROMETHEUS-NOVEL project.
    Logs to console and a file.
    '''
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "prometheus_novel.log")

    # Clear existing handlers to prevent duplicate logs
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    for handler in logging.getLogger().handlers[:]:
        logging.getLogger().removeHandler(handler)

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    # Set specific log levels for noisy libraries if needed
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('tenacity').setLevel(logging.INFO) # Keep retries visible
    
    logger = logging.getLogger(__name__)
    logger.info("Logging configured.")

if __name__ == '__main__':
    setup_logging(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")
