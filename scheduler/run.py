import logging.config
from arq import Worker
from arq.connections import RedisSettings
import os
from arq.logs import default_log_config
import logging
from src.scheduler import Scheduler
from dotenv import load_dotenv
from arq.cron import cron
load_dotenv()


REDIS_SETTINGS = RedisSettings(os.getenv('REDIS_HOST', 'localhost'), int(os.getenv('REDIS_PORT', '6379')))
FUNCTIONS = [Scheduler.add_channel]
CRON = [cron(Scheduler.run_iteration, minute={*list(range(0, 59))})]


async def startup(ctx):
    scheduler = Scheduler(144, 10, 
                          REDIS_SETTINGS, os.getenv('PARSER_QUEUE_NAME', 'parser'), 
                          REDIS_SETTINGS, os.getenv('DATABASE_QUEUE_NAME', 'database'),
                          REDIS_SETTINGS, os.getenv('STORAGE_QUEUE_NAME', 'storage'))
    await scheduler.init()
    ctx['Scheduler_instance'] = scheduler
    logging.getLogger('arq').info(f'Startup done')
    

async def shutdown(ctx):
    logging.getLogger('arq').info('Shutting down...')


def main():
    verbose = os.getenv('VERBOSE', '1') == '1'
    log_level = 'DEBUG' if verbose else 'INFO'
    logging_config = default_log_config(verbose=verbose)
    logging_config['loggers']['scheduler'] = {'level': log_level, 'handlers': ['arq.standard']}
    
    logging.config.dictConfig(logging_config)
    worker = Worker(functions = FUNCTIONS,
                    on_startup = startup,
                    on_shutdown = shutdown,
                    redis_settings = REDIS_SETTINGS,
                    queue_name = os.getenv('SCHEDULER_QUEUE_NAME', 'scheduler'),
                    job_timeout=100,
                    cron_jobs=CRON,
                    max_jobs=int(os.getenv('MAX_JOBS', '10')))
    worker.run()


if __name__ == '__main__':
    main()
    
