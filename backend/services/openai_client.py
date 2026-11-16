"""Run synchronous OpenAI requests with deterministic HTTP client cleanup."""
import asyncio


def _create_completion(api_key, timeout, request_options):
    from openai import OpenAI

    with OpenAI(api_key=api_key, max_retries=0, timeout=timeout) as client:
        return client.chat.completions.create(**request_options)


async def create_chat_completion(api_key, timeout=35.0, **request_options):
    """Keep the sync HTTP client and its lifecycle on one worker thread."""
    return await asyncio.wait_for(
        asyncio.to_thread(_create_completion, api_key, timeout, request_options),
        timeout=timeout + 2,
    )
