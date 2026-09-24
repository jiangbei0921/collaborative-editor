import asyncio
import json
import sys
import time
import urllib.request
import urllib.error
import websockets

HTTP_BASE = "http://127.0.0.1:8000"
WS_BASE = "ws://127.0.0.1:8000"

RECV_TIMEOUT = 5.0


def http_post(path: str):
    req = urllib.request.Request(HTTP_BASE + path, method="POST")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def http_get(path: str):
    with urllib.request.urlopen(HTTP_BASE + path) as resp:
        return json.loads(resp.read().decode())


async def recv_with_timeout(ws, timeout: float = RECV_TIMEOUT):
    try:
        return await asyncio.wait_for(ws.recv(), timeout=timeout)
    except asyncio.TimeoutError:
        return None


async def join_document(name: str, doc_id: str):
    uri = f"{WS_BASE}/ws/{doc_id}"
    ws = await websockets.connect(uri)
    await ws.send(json.dumps({"type": "join", "client_id": name}))

    raw = await recv_with_timeout(ws)
    if raw is None:
        print(f"  FAIL [{name}]: no response after join")
        await ws.close()
        return None, None

    doc = json.loads(raw)
    if doc.get("type") == "error":
        print(f"  FAIL [{name}]: server error - {doc.get('reason', doc.get('message'))}")
        await ws.close()
        return None, None

    print(f"  [{name}] joined: version={doc.get('version')} blocks={len(doc.get('blocks', []))}")
    return ws, doc


async def main():
    doc_id = f"ws-test-{int(time.time())}"

    print("=" * 60)
    print("WebSocket Collaborative Editor - Integration Test")
    print("=" * 60)

    # Step 1: Create document via HTTP
    print("\n[Step 1] Creating test document via HTTP...")
    try:
        result = http_post(f"/api/documents/{doc_id}")
        print(f"  HTTP POST -> {result['status']}")
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  Document may already exist: {body}")
    except Exception as e:
        print(f"  FAIL: HTTP error - {e}")
        sys.exit(1)

    # Step 2: Verify document state via HTTP
    print("\n[Step 2] Verifying document via HTTP...")
    state = http_get(f"/api/documents/{doc_id}")
    print(f"  id={state['id']} version={state['version']} blocks={len(state['blocks'])}")
    assert state["version"] == 0, f"Expected version 0, got {state['version']}"
    assert state["blocks"] == [], f"Expected empty blocks, got {len(state['blocks'])}"

    # Step 3: Client A joins
    print("\n[Step 3] Client A joining via WebSocket...")
    ws_a, doc_a = await join_document("client-a", doc_id)
    if ws_a is None:
        sys.exit(1)
    assert doc_a["version"] == 0
    assert doc_a["blocks"] == []

    # Step 4: Client B joins
    print("\n[Step 4] Client B joining via WebSocket...")
    ws_b, doc_b = await join_document("client-b", doc_id)
    if ws_b is None:
        await ws_a.close()
        sys.exit(1)
    assert doc_b["version"] == 0
    assert doc_b["blocks"] == []

    # Step 5: Client A sends create_block operation
    print("\n[Step 5] Client A sending create_block operation...")
    op = {
        "id": "op-test-001",
        "client_id": "client-a",
        "document_id": doc_id,
        "block_id": None,
        "type": "create_block",
        "position": None,
        "content": "paragraph",
        "length": None,
        "version": 1,
    }
    await ws_a.send(json.dumps(op))

    # Step 6: Client A receives ACK
    print("\n[Step 6] Client A waiting for ACK...")
    ack_raw = await recv_with_timeout(ws_a)
    if ack_raw is None:
        print("  FAIL: Client A did not receive ACK (timeout)")
        await ws_a.close()
        await ws_b.close()
        sys.exit(1)

    ack = json.loads(ack_raw)
    print(f"  ACK received: type={ack.get('type')} status={ack.get('status')} version={ack.get('version')}")
    assert ack["type"] == "ack", f"Expected ack, got {ack['type']}"
    assert ack["status"] == "applied", f"Expected applied, got {ack['status']}"
    assert ack["version"] == 1, f"Expected version 1, got {ack['version']}"
    assert ack["operation_id"] == "op-test-001"

    # Step 7: Client B receives broadcast
    print("\n[Step 7] Client B waiting for broadcast...")
    bcast_raw = await recv_with_timeout(ws_b)
    if bcast_raw is None:
        print("  FAIL: Client B did not receive broadcast (timeout)")
        await ws_a.close()
        await ws_b.close()
        sys.exit(1)

    bcast = json.loads(bcast_raw)
    print(f"  Broadcast received: type={bcast.get('type')} block_id={bcast.get('block_id')} version={bcast.get('version')}")
    assert bcast["type"] == "create_block", f"Expected create_block, got {bcast['type']}"
    assert bcast["version"] == 1, f"Expected version 1, got {bcast['version']}"
    assert bcast["id"] == "op-test-001"
    block_id = bcast.get("block_id") or bcast.get("id")
    assert block_id is not None, "Broadcast should have block_id or id"

    # Step 8: Client A verifies no extra broadcast (sender excluded)
    print("\n[Step 8] Verifying Client A receives nothing extra...")
    extra = await recv_with_timeout(ws_a, timeout=1.0)
    if extra is not None:
        print(f"  WARNING: Client A received unexpected message: {extra}")
    else:
        print("  OK: Client A received no extra messages")

    # Step 9: Client B also gets nothing extra
    extra_b = await recv_with_timeout(ws_b, timeout=1.0)
    if extra_b is not None:
        print(f"  WARNING: Client B received unexpected message: {extra_b}")
    else:
        print("  OK: Client B received no extra messages")

    # Step 10: Verify persisted state via HTTP
    print("\n[Step 10] Verifying persisted state via HTTP...")
    final = http_get(f"/api/documents/{doc_id}")
    print(f"  id={final['id']} version={final['version']} blocks={len(final['blocks'])}")
    assert final["version"] == 1, f"Expected version 1, got {final['version']}"
    assert len(final["blocks"]) == 1, f"Expected 1 block, got {len(final['blocks'])}"
    assert final["blocks"][0]["type"] == "paragraph"
    assert final["blocks"][0]["id"] == block_id

    # Close connections
    await ws_a.close()
    await ws_b.close()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())