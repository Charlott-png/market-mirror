"""Small OpenAI Responses API adapter for one cleaned product image."""

import base64
import json
import os

from app.models.product import CATEGORIES


class OpenAIVisionProvider:
    def __init__(self, client=None, model="gpt-6-luna", timeout=12):
        if client is None:
            from openai import OpenAI
            client = OpenAI(
                api_key=os.environ.get("OPENAI_API_KEY"),
                timeout=timeout,
                max_retries=0,
            )
        self.client = client
        self.model = model
        self.timeout = timeout

    def analyze(self, clean_jpeg):
        data_url = "data:image/jpeg;base64," + base64.b64encode(clean_jpeg).decode("ascii")
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "title": {"type": "string", "minLength": 3, "maxLength": 80},
                "category": {"type": "string", "enum": list(CATEGORIES)},
                "title_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "category_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "abstain_reason": {"type": "string", "maxLength": 160},
            },
            "required": [
                "title", "category", "title_confidence",
                "category_confidence", "abstain_reason",
            ],
        }
        response = self.client.responses.create(
            model=self.model,
            store=False,
            tools=[],
            reasoning={"effort": "none"},
            input=[{
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Identify the main sale item. Suggest a short factual title and "
                            "exactly one allowed category. If uncertain, lower confidence and "
                            "briefly explain why. Do not infer private or personal information."
                        ),
                    },
                    {"type": "input_image", "image_url": data_url, "detail": "low"},
                ],
            }],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "market_mirror_listing_suggestion",
                    "strict": True,
                    "schema": schema,
                }
            },
            max_output_tokens=220,
        )
        return json.loads(response.output_text)
