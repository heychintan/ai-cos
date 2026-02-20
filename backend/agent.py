import os
import anthropic


def generate_newsletter(context: str) -> str:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    system_prompt = (
        "You are a professional content writer for the Chief of Staff Network (CoSN), "
        "a professional community for Chiefs of Staff at tech companies. "
        "Your writing is professional but warm, direct, and community-focused. "
        "You never fabricate events, links, or information. "
        "If data is missing, note it with [MISSING: ...] rather than inventing content. "
        "Always follow the provided template exactly."
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": context}],
    )
    return message.content[0].text
