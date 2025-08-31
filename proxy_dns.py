# https://github.com/paulc/dnslib

from dnslib import DNSRecord, DNSQuestion, QTYPE, RR, A
import socket
import threading
from constants import PROXY_HOST, PROXY_PORT, WWW, EMPTY, FAKE_MESSAGE, FAKE_RESPONSE_COUNT, REPLACE_DNS, REPLACED
from utils import load_config, build_db, load_black_list
import sys
from loguru import logger

cfg = load_config()
# Убираем все хендлеры, включая дефолтный
logger.remove()

# Добавляем только то, что нам нужно
logger.add(sys.stdout, colorize=True, level=cfg.get("LOG_LEVEL", "DEBUG"))

logger.remove()
logger.propagate = False

logger.add(sys.stdout, colorize=True)

# Define the IP and port for your DNS proxy server
proxy_host = cfg.get(PROXY_HOST, "0.0.0.0")  # Listen on all available network interfaces
proxy_port = cfg.get(PROXY_PORT, 53)

# Define the DNS server you want to forward requests to
forward = cfg.get("dns_forwarders")
dns_server = (forward.get("host"), forward.get("port"))

local_db = build_db(cfg.get("black_list_domains"))
logger.debug(f"Loaded from config : {local_db}")
if cfg.get("load_black_list"):
    local_db = load_black_list(local_db, cfg)

fttl = cfg.get("fake_response").get("ttl")
fA = A(cfg.get("fake_response").get("host"))

status_dict = {
    FAKE_RESPONSE_COUNT: 0,
    REPLACE_DNS: 0
}


def fake_response(q: DNSRecord, query_name, fake_ip=None):
    lfA = fA
    if fake_ip:
        lfA = A(fake_ip)
    a = q.reply()

    a.add_answer(RR(query_name, QTYPE.A, rdata=lfA, ttl=fttl))

    response = a.pack()
    return response


def check_black_list(query_name):
    query_name = query_name.replace(WWW, EMPTY).lower()
    if query_name == ".":
        return True
    return query_name in local_db.get(query_name[0], {}).get(query_name[1], [])


def check_for_replace_dns(dns_name: str = ""):
    return cfg.get(REPLACE_DNS).get(dns_name, False)


def dns_proxy(query_data, client_address):
    query_name = EMPTY
    try:
        q = DNSRecord.parse(query_data)

        query_name = q.q.qname.idna()
        fake_msg = EMPTY
        replace_dns = check_for_replace_dns(query_name)
        if replace_dns:
            response = fake_response(q, query_name, fake_ip=replace_dns)
            fake_msg = REPLACED
            status_dict[REPLACE_DNS] = status_dict[REPLACE_DNS] + 1
        elif check_black_list(query_name):
            response = fake_response(q, query_name)
            fake_msg = FAKE_MESSAGE
            status_dict[FAKE_RESPONSE_COUNT] = status_dict[FAKE_RESPONSE_COUNT] + 1
            if status_dict[FAKE_RESPONSE_COUNT] % 100 == 0:
                logger.debug(status_dict)
        else:
            response = forward_dns_query(query_data, dns_server)
        logger.debug(f"[{client_address[0]}] : {query_name}{fake_msg}")
        server_socket.sendto(response, client_address)
    except Exception as e:
        logger.exception(f"Error handling DNS request query '{query_name}'")
        logger.exception(e)


def forward_dns_query(query_data, server_address):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(query_data, server_address)
        response, _ = sock.recvfrom(1024)
        return response


# Create a socket to listen for DNS queries
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
    logger.debug(f"DNS proxy server listening on {proxy_host} port {proxy_port}")
    server_socket.bind((proxy_host, proxy_port))

    while True:
        try:
            query_data, client_address = server_socket.recvfrom(1024)
            thread = threading.Thread(target=dns_proxy, args=(query_data, client_address))
            thread.daemon = True  # Set the thread as a daemon
            thread.start()
        except Exception as e:
            logger.exception("Error receiving DNS query")
            logger.exception(e)
