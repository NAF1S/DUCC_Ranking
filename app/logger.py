import logging
import os
from datetime import datetime

# Create logs directory if it doesn't exist
logs_dir = 'logs'
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Configure logging
def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Create a file handler
    log_file = os.path.join(logs_dir, f'{datetime.now().strftime("%Y-%m-%d")}.log')
    handler = logging.FileHandler(log_file)
    handler.setLevel(logging.INFO)
    
    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    logger.addHandler(handler)
    logger.addHandler(console_handler)
    
    return logger
