import os
import logging.config
from arq import Worker
from arq.connections import RedisSettings
from arq.logs import default_log_config
import logging
from src.parser import Parser
from src.telegram import Telegram
from concurrent.futures import ProcessPoolExecutor
from dotenv import load_dotenv
from arq.cron import cron
load_dotenv()


REDIS_SETTINGS = RedisSettings(os.getenv('REDIS_HOST', 'localhost'), int(os.getenv('REDIS_PORT', '6379')))
PARSER_FUNCTIONS = [Parser.get_channel_info]
TELEGRAM_FUNCTIONS = [Telegram.add_client]


async def startup(ctx):
    telegram = Telegram(os.getenv('REDIS_HOST', 'localhost'),
                        int(os.getenv('REDIS_PORT', '6379')),
                        int(os.getenv('TELEGRAM_CLIENTS_REDIS_DB', '5')))
    await telegram.init_database()
    parser = Parser(telegram)
    ctx['Parser_instance'] = parser
    ctx['Telegram_instance'] = telegram
    logging.getLogger('arq').info(f'Startup done {ctx["worker_id"]} / {ctx["workers_count"]}')
    

async def shutdown(ctx):
    logging.getLogger('arq').info('Shutting down...')
    await ctx['Telegram_instance'].close()

def start_worker(worker_id: int, workers_count: int, functions, queue_name, cron_jobs=None):
    verbose = os.getenv('VERBOSE', '1') == '1'
    log_level = 'DEBUG' if verbose else 'INFO'
    logging_config = default_log_config(verbose=verbose)
    logging_config['loggers']['telegram'] = {'level': log_level, 'handlers': ['arq.standard']}
    logging_config['loggers']['parser'] = {'level': log_level, 'handlers': ['arq.standard']}
    
    logging.config.dictConfig(logging_config)
    worker = Worker(functions = functions,
                    cron_jobs=cron_jobs,
                    on_startup = startup,
                    on_shutdown = shutdown,
                    redis_settings = REDIS_SETTINGS,
                    queue_name = queue_name,
                    job_timeout=100,
                    max_jobs=int(os.getenv('MAX_JOBS', '10')))
    worker.ctx['worker_id'] = worker_id
    worker.ctx['workers_count'] = workers_count
    worker.run()

def main(max_workers: int):
    with ProcessPoolExecutor(max_workers=max_workers + 1) as executor:
        for i in range(max_workers):
            executor.submit(start_worker, i + 1, max_workers, 
                            PARSER_FUNCTIONS, 
                            os.getenv('PARSER_QUEUE_NAME', 'parser'),
                            [cron(Parser.update_client, minute={i + 1})])
        executor.submit(start_worker, 1, 1, TELEGRAM_FUNCTIONS, os.getenv('TELEGRAM_QUEUE_NAME', 'telegram'))


if __name__ == '__main__':
    main(int(os.getenv('WORKERS_COUNT', '1')))
    
