# -*- coding: utf-8 -*-

import time
import json
import websockets
import asyncio

WS_HOST = '0.0.0.0'
WS_PORT = 1001 #端口

def log(str):
    str = "[Server] %s %s" % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), str)
    print(str)

# 存储客户端
clients = {}

def make_msg(msg_type: str, data=None) -> str:
    msg = {
        "type": msg_type,
        "data": data,
        "timestamp": time.time(),
    }
    return json.dumps(msg, ensure_ascii=False)

async def handler(websocket):
    """处理单个客户端连接"""
    peer = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
    client_id = None  # 注册后才会有
    log(f"新连接: {peer}")

    try:
        async for raw in websocket:
            # ---------- 解析 JSON ----------
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send(make_msg("error", "非法 JSON 格式"))
                continue

            msg_type = msg.get("type")
            client_id = msg.get("client_id")
            data = msg.get("data")

            # ---------- 1. 注册 ----------
            if msg_type == "register":
                if not client_id or not isinstance(client_id, str):
                    await websocket.send(make_msg("error", "client_id 非法"))
                    continue

                clients[client_id] = websocket
                log(f"注册成功: {client_id} ({peer})  当前在线: {len(clients)}")

                await websocket.send(
                    make_msg("register_ack", f"注册成功，你的标识是 {client_id}")
                )
                continue

            # ---------- 注册之前的其他消息一律拒绝 ----------
            if client_id is None:
                await websocket.send(make_msg("error", "请先发送 register 注册标识"))
                continue

            # ---------- 2. 心跳 ----------
            if msg_type == "ping":
                await websocket.send(
                    make_msg("pong", data)
                )
                continue

            # ---------- 3. 客户端 消息 ----------
            if msg_type == "message":
                data = msg.get("data")
                if not isinstance(data, dict):
                    log(f"新消息: {client_id} ({peer})  消息内容: {data}")
                else:
                    print(f"新消息: {client_id} ({peer})  消息内容: {json.dumps(data, ensure_ascii=False)}")
                continue

            # ---------- 其他类型 ----------
            await websocket.send(make_msg("error", f"未知消息类型: {msg_type}"))

    except websockets.exceptions.ConnectionClosed as e:
        log(f"连接关闭: {client_id or peer} ({e.code})")
    finally:
        if client_id:
            clients.pop(client_id, None)
            log(f"下线: {client_id}  当前在线: {len(clients)}")

# 后台运行的任务
async def thread_listen():
    while True:
        await asyncio.sleep(1) #延时必须使用这个

async def main():
    async with websockets.serve(
        handler, WS_HOST, WS_PORT,
        ping_interval=None,
        max_size=2 ** 20,
    ):
        log(f"启动成功，监听 ws://{WS_HOST}:{WS_PORT}")

       # 后台任务
        listen_task = asyncio.create_task(thread_listen())
        try:
            await asyncio.Future()   # 主协程常驻
        finally:
            listen_task.cancel()
            await asyncio.gather(listen_task, return_exceptions=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("已关闭")