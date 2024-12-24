from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
import logging
from multiprocessing import Queue
from pathlib import Path
from typing import Any, Dict


def write_messages_file(queue: Queue, log_dir: str = '.'):
    logging.basicConfig(
        level=logging.INFO,
        filename=Path(log_dir, f'output_writer.log'),
        filemode='a',
        format='%(asctime)s %(levelname)s %(message)s'
    )

    while True:
        page_id, path, msg = queue.get()
        logging.info(f'Writing page {page_id}')

        try:
            with open(path, 'w') as result:
                result.write(msg)
        except Exception as e:
            logging.error(f'While writing to file: {str(e)}')


def write_messages_kafka(queue: Queue, log_dir: str = '.', config: Dict[str, Any] = dict()):
    logging.basicConfig(
        level=logging.INFO,
        filename=Path(log_dir, f'output_writer.log'),
        filemode='a',
        format='%(asctime)s %(levelname)s %(message)s'
    )

    bootstrap_servers = ','.join(config["bootstrap_servers"])
    admin_client = AdminClient({
        'bootstrap.servers': bootstrap_servers,
        'client.id': config['client_id']
    })
    producer = Producer({
        'bootstrap.servers': bootstrap_servers,
        'client.id': config['client_id'],
        'message.max.bytes': config['max_message_size']
    })
    topic = NewTopic(
        config['topic'],
        config={'max.message.bytes': config['max_message_size']}
    )
    admin_client.create_topics([topic])

    @staticmethod
    def delivery_report(err, msg):  # type: ignore
        if err is not None:
            logging.error(f'While writing to {msg.topic()} [{msg.partition()}] (via callback): {err}')

    while True:
        page_id, _, msg = queue.get()
        logging.info(f'Writing page {page_id}')

        try:
            producer.produce(config['topic'], value=msg, callback=delivery_report)
        except Exception as e:
            logging.error(f'While writing to {config['topic']}: {e}')
        producer.flush()
