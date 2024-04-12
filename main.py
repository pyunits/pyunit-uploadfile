#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @Time  : 2024/3/29 10:31
# @Email: jtyoui@qq.com
import gzip
import hashlib
import json
import os
from os import path

import pandas as pd
import redis
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"])

ip = os.getenv("REDIS_IP")
password = os.getenv("REDIS_PASSWORD")
db = os.getenv("REDIS_DB", 0)

r = redis.Redis(host=ip, password=password, db=db)

dirs = path.join(path.dirname(__file__), "file")

if not path.exists(dirs):
    os.mkdir(dirs)


class Item(BaseModel):
    name: str
    md5: str
    type: str


@app.get("/")
def read_root():
    return {"Hello": "World"}


def _md5(chunk) -> str:
    m = hashlib.md5()
    m.update(chunk)
    return m.hexdigest()


@app.post("/upload", response_model=list[Item])
async def upload_file(file: UploadFile):
    items = []
    contents = await file.read(8192)
    code = _md5(contents)
    new_path = path.join(dirs, code)
    items.append({'name': file.filename, 'md5': code, 'type': file.content_type})
    if path.exists(new_path):
        return items

    os.mkdir(new_path)
    with open(path.join(new_path, file.filename), 'wb') as wp:
        wp.write(contents)
        for _ in range(0, file.size, 8192):
            data = await file.read(8192)
            wp.write(data)

    return items


@app.get("/parse")
def parse_file(md5: str):
    filename = os.listdir(path.join(dirs, md5))
    if not filename:
        return "不存在该文件"

    filename = filename[0]
    paths = path.join(dirs, md5, filename)
    if filename.endswith(".xlsx") or filename.endswith(".xls"):
        df = pd.read_excel(paths)
    elif filename.endswith(".csv"):
        df = pd.read_csv(paths)
    elif filename.endswith(".tsv"):
        df = pd.read_csv(paths, sep="\t")
    elif filename.endswith(".json"):
        df = pd.read_json(paths)
    elif filename.endswith(".feather"):
        df = pd.read_feather(paths)
    elif filename.endswith(".parquet"):
        df = pd.read_parquet(paths)
    elif filename.endswith(".xml"):
        df = pd.read_xml(paths)
    else:
        return f"{filename} 格式不支持"

    batch, keys = 100, []

    for index in range(0, df.shape[0], batch):
        key = f"{md5}:{index:08d}"
        keys.append(key)
        if r.exists(key):
            continue

        js = df.loc[index:index + batch - 1]
        data = js.to_dict(orient="list")
        byte = json.dumps(data).encode("utf-8")
        out = gzip.compress(byte)
        r.set(key, out)
    return keys
