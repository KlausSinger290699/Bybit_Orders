import asyncio, json
import websockets

# Optional: tune keepalive + close timeout
SERVE_KW = dict(ping_interval=20, ping_timeout=20, close_timeout=1)

async def handler(ws):
    peer = ws.remote_address
    print("✅ Server: client connected", peer, "\n")
    try:
        async for msg in ws:
            try:
                print(f"📥 Received (raw): {msg}")
                data = json.loads(msg)
                side = data.get("side"); tf = data.get("tf"); status = data.get("status")
                print(f"📥 Received (summary): {side.upper()} {tf}m ({status})")

                reply_wire = json.dumps({"message": f"Server received {side.upper()} {tf}m ({status})"})
                # Send might fail if client died between recv and send → guard it.
                try:
                    await ws.send(reply_wire)
                    print(f"📤 Sent back (json): {reply_wire}\n")
                except (websockets.ConnectionClosedOK, websockets.ConnectionClosedError):
                    # Client closed in between; just stop the handler cleanly
                    break
                except (ConnectionResetError, OSError) as e:
                    print("🔌 Send failed (client dropped):", e)
                    break
            except json.JSONDecodeError:
                print("⚠️ Bad message: not JSON")
    except websockets.ConnectionClosedOK as e:
        print(f"👋 Client closed cleanly: code={e.code} reason={e.reason}\n")
    except websockets.ConnectionClosedError as e:
        print(f"🔌 Client connection error: code={e.code} reason={e.reason}\n")
    except (ConnectionResetError, OSError) as e:
        print("🔌 Client network dropped:", e, "\n")
    finally:
        # Nothing else to do; handler ends and server keeps running for others
        pass

async def main():
    async with websockets.serve(handler, "127.0.0.1", 8765, **SERVE_KW):
        print("🔊 WS server listening on ws://127.0.0.1:8765")
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🟥 Server stopped by user")
