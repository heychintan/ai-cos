"""Claude API integration — streaming generation."""
import anthropic

SYSTEM_PROMPT = """\
You are a professional content writer for the Chief of Staff Network (CoSN), \
a community for Chiefs of Staff and operators at tech companies. Your writing \
is professional but warm, direct, and community-focused.

Rules:
- Never fabricate events, links, dates, or statistics.
- If data is missing, note it with [MISSING: description] rather than inventing.
- Follow the provided template structure exactly.
- Do not add sections that are not in the template.
- Write in second person for calls-to-action ("join us", "register now").\
"""


def stream_generation(
    api_key: str,
    context: str,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 4096,
):
    """
    Generator that yields text chunks from the Claude streaming API.
    Usage:
        for chunk in stream_generation(api_key, context, model):
            ...
    """
    client = anthropic.Anthropic(api_key=api_key)
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": context}],
    ) as stream:
        yield from stream.text_stream


AVAILABLE_MODELS = [
    "claude-sonnet-4-6",
    "claude-opus-4-6",
    "claude-haiku-4-5-20251001",
]
