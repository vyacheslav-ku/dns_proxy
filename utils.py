import yaml

from constants import WWW, EMPTY


def load_config() -> dict:
    with open('config.yaml', 'r') as file:
        cfg = yaml.safe_load(file)
    return cfg


def build_db(config_data):
    db = {}
    for d in config_data:
        db = add_record(db, d)
    return db


def add_record(db, record):
    d = record.replace(WWW, EMPTY).strip() + "."
    symbol1 = d[0]
    symbol2 = d[1]
    if symbol1 not in db.keys():
        db[symbol1] = {symbol2: []}

    if symbol2 not in db[symbol1].keys():
        db[symbol1][symbol2] = []

    db[symbol1][symbol2].append(d)
    return db


def load_black_list(db: dict):
    with open("blacklist.txt") as f:
        for line in f:
            db = add_record(db, line)
    return db
