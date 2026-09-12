# -*- coding: utf-8 -*-

import asyncio
import json
import time
import websockets

WS_URI = "ws://127.0.0.1:1001"

HEARTBEAT_INTERVAL = 10.0   # 心跳发送间隔(秒)
HEARTBEAT_TIMEOUT = 5.0     # 等待 pong 超时(秒)

m_client_id = 'test' #标记客户端ID 初次链接将发送register消息给服务端

state = {
    "ws": None,
    "connected": asyncio.Event(),
    "registered": False,
    "last_pong": 0.0,
    "stop": False,
}

def log(str):
    str = "[Client] %s %s %s" % (m_client_id,time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), str)
    print(str)

def make_msg(msg_type, data=None):
    """构造统一 JSON 消息"""
    msg = {
        "type": msg_type,
        "client_id": m_client_id,
        "data": data,
        "timestamp": time.time(),
    }
    return json.dumps(msg, ensure_ascii=False)

# ============ 心跳任务 ============
async def heartbeat_loop():
    while not state["stop"]:
        # 等待连接就绪
        try:
            await asyncio.wait_for(state["connected"].wait(), timeout=1.0)
        except asyncio.TimeoutError:
            continue
        if not state["connected"].is_set() or not state["registered"]:
            continue

        try:
            await state["ws"].send(make_msg("ping", "ping"))
            log("发送心跳 ping")

            await asyncio.sleep(HEARTBEAT_INTERVAL)

            # 检查 pong 是否超时
            elapsed = time.time() - state["last_pong"]
            if state["last_pong"] > 0 and elapsed > HEARTBEAT_INTERVAL + HEARTBEAT_TIMEOUT:
                log(f"心跳超时 ({elapsed:.1f}s)，主动断开触发重连")
                await state["ws"].close()
        except websockets.exceptions.ConnectionClosed:
            break
        except Exception as e:
            log(f"心跳异常: {e}")
            break


# ============ 接收任务 ============
async def receive_loop():
    async for raw in state["ws"]:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            log("非法 JSON: {raw}")
            continue

        msg_type = msg.get("type")
        data = msg.get("data")

        if msg_type == "pong":
            state["last_pong"] = time.time()
            log("pong")

        elif msg_type == "register_ack":
            state["registered"] = True
            log("注册成功")

        elif msg_type == "error":
            log("-----------错误消息-----------")
            print(data)

        elif msg_type == "command":
            # 接收服务端推送任务
            params = data.get("params")
            #command(params)
            
        else:
            log("-----------未知消息-----------")
            print(msg)

# ============ 单次连接生命周期 ============
async def run_once():
    async with websockets.connect(WS_URI, ping_interval=None,
                                  max_size=2 ** 20) as ws:
        state["ws"] = ws
        state["connected"].set()
        state["registered"] = False
        state["last_pong"] = time.time()

        log("已连接 %s，发送注册请求..." % WS_URI)

        # 1) 发送注册
        await ws.send(make_msg("register", m_client_id))

        # 2) 等 register_ack（最多 5 秒）
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            msg = json.loads(raw)
            if msg.get("type") == "register_ack":
                state["registered"] = True
                log("注册成功")
            elif msg.get("type") == "error":
                log("注册失败")
                state["stop"] = True
                return
        except asyncio.TimeoutError:
            log("注册超时")
            return

        # 3) 并发运行心跳 + 接收
        hb_task = asyncio.create_task(heartbeat_loop())
        recv_task = asyncio.create_task(receive_loop())
        try:
            await recv_task
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            state["connected"].clear()
            state["registered"] = False
            hb_task.cancel()
            recv_task.cancel()
            await asyncio.gather(hb_task, recv_task, return_exceptions=True)
            log("连接结束")


# ============ 自动重连主循环 ============
async def run_forever():
    delay, max_delay = 1.0, 30.0

    while not state["stop"]:
        try:
            await run_once()
            delay = 1.0
        except (websockets.exceptions.ConnectionClosed,
                ConnectionRefusedError, OSError) as e:
            log("----------连接异常----------")
            print(e)

        if state["stop"]:
            break

        log(f"{delay:.1f}s 后重连...")
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            break
        delay = min(delay * 2, max_delay)

    log("已退出")


        

def main():
    log("开始运行")
    try:
        asyncio.run(run_forever())
    except KeyboardInterrupt:
        log("已退出")


if __name__ == "__main__":
    main()