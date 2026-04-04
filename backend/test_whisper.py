import sys
sys.path.append('c:\\Talking BI\\talking-bi\\backend')
import asyncio
import base64
import io
import os
from core.config import settings

async def main():
    with open("dummy.webm", "wb") as f:
        f.write(b"dummy")
    try:
        from groq import AsyncGroq
        with open("dummy.webm", "rb") as f:
            audio_bytes = f.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        
        audio_bytes_decoded = base64.b64decode(audio_b64)
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        audio_file = io.BytesIO(audio_bytes_decoded)
        audio_file.name = "audio.webm"
        
        print("Calling groq transcription...", flush=True)
        response = await client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=("audio.webm", audio_bytes_decoded),
            language="en",
            prompt="Business intelligence query about sales, revenue, customers, or products.",
        )
        print("Response:", response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
