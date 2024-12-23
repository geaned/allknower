from confluent_kafka import Producer
from confluent_kafka.admin import AdminClient, NewTopic
import logging
from multiprocessing import Queue
from typing import Any, Dict


def write_messages_file(queue: Queue):
    while True:
        path, msg = queue.get()
        with open(path, 'w') as result:
            result.write(msg)


def write_messages_kafka(queue: Queue, config: Dict[str, Any]):
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
    def delivery_report(err, msg):
        if err is not None:
            logging.error(f'Message delivery to {msg.topic()} [{msg.partition()}] failed: {err}')

    while True:
        _, msg = queue.get()
        producer.produce(config['topic'], value=msg, callback=delivery_report)
        producer.flush()