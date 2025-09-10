import logging
from logging.handlers import RotatingFileHandler
from config import MAIN_LOG_FILE, SUBPROCESS_LOG_FILE, MAX_LOG_SIZE, BACKUP_COUNT

def setup_logger(name, log_file, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler = RotatingFileHandler(log_file, maxBytes=MAX_LOG_SIZE, backupCount=BACKUP_COUNT)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def log_subprocess_output(logger, process, context):
    """Log subprocess output with context"""
    stdout = process.stdout.decode('utf-8', errors='ignore') if process.stdout else ''
    stderr = process.stderr.decode('utf-8', errors='ignore') if process.stderr else ''
    if stdout:
        logger.info(f"{context} stdout: {stdout}")
    if stderr:
        logger.error(f"{context} stderr: {stderr}")

main_logger = setup_logger("isolator", MAIN_LOG_FILE)
subprocess_logger = setup_logger("isolator.subprocess", SUBPROCESS_LOG_FILE)
