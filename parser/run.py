import logging.config
from arq import Worker
from arq.connections import RedisSettings
import os
from arq.logs import default_log_config
import logging
from concurrent.futures import ProcessPoolExecutor
from dotenv import load_dotenv
load_dotenv()


REDIS_SETTINGS = RedisSettings(os.getenv('REDIS_HOST', 'localhost'), int(os.getenv('REDIS_PORT', '6379')))
FUNCTIONS = []

async def startup(ctx):
    logging.getLogger('arq').info('Startup done')

async def shutdown(ctx):
    logging.getLogger('arq').info('Shutting down...')

def start_worker():
    verbose = True
    log_level = 'DEBUG' if verbose else 'INFO'
    logging_config = default_log_config(verbose=verbose)
    logging_config['loggers']['try_on_model'] = {'level': log_level, 'handlers': ['arq.standard']}
    logging_config['loggers']['database'] = {'level': log_level, 'handlers': ['arq.standard']}
    logging_config['loggers']['payment'] = {'level': log_level, 'handlers': ['arq.standard']}
    
    logging.config.dictConfig(logging_config)
    worker = Worker(functions = FUNCTIONS,
                    on_startup = startup,
                    on_shutdown = shutdown,
                    redis_settings = REDIS_SETTINGS,
                    job_timeout=100)
    worker.run()

def main(max_workers: int):
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for _ in range(max_workers):
            executor.submit(start_worker)


if __name__ == '__main__':
    main(int(os.getenv('WORKERS_COUNT', '1')))
    
