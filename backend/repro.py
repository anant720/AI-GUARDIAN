
import asyncio
import time
from typing import Dict, Any

# Mocking the pipeline parts
async def mock_url_builder(url: str):
    print("URL builder started")
    await asyncio.sleep(0.1)
    return {"risk_score": 10, "signals": {}}

async def mock_threat_builder(url: str):
    print("Threat builder started")
    # This simulates my aggregate_threat_intelligence
    tasks = [asyncio.sleep(0.05) for _ in range(5)]
    await asyncio.wait_for(asyncio.gather(*tasks), timeout=2.0)
    return {"threat_score": 20}

async def mock_msg_builder(text: str):
    print("Msg builder started")
    return await asyncio.to_thread(lambda: {"message_analysis": {"score_details": {"message_risk_score": 5}}})

async def repro():
    url = "https://example.com"
    msg = "hello"
    
    url_task = mock_url_builder(url)
    threat_task = mock_threat_builder(url)
    msg_task = mock_msg_builder(msg)
    
    results = await asyncio.gather(url_task, threat_task, msg_task)
    print("Results gathered:", results)
    
    url_report, threat_report, msg_report = results
    
    # Simulate signal extraction
    def extract(rep):
        return rep.get("risk_score", 0)
        
    print("Extracted:", extract(url_report))

if __name__ == "__main__":
    asyncio.run(repro())
