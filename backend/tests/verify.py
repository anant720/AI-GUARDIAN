import asyncio
from app.services.message_intelligence import analyze_message

async def main():
    try:
        msg = "Your PayPal account has been suspended. Verify immediately. https://paypal-security-update.xyz/login"
        print(f"Analyzing message: {msg}")
        result = await analyze_message(msg)
        print("Analysis successful!")
        print(result)
    except Exception as e:
        print(f"Error during analysis: {e}")

if __name__ == "__main__":
    asyncio.run(main())
