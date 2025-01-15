from dataclasses import dataclass
from typing import Dict, List, Union

import torch
from loguru import logger
from PIL import Image
from transformers import Qwen2VLForConditionalGeneration, Qwen2VLProcessor

LABELING_MODEL_ID = "Qwen/Qwen2-VL-7B-Instruct"
SYSTEM_PROMPT = """\
You will be given a search query and two answers to it. \
The answers can be in the form of text or images. \
You must evaluate which answer is more relevant to the search query.

Provide the answer as a JSON object with a single key "answer" \
with possible values "first" or "second".
"""
USER_PROMPT_PART_QUERY = """\
Search query:
```{query}```
"""
USER_PROMPT_PART_FIRST_ANSWER_HEADER = """\
First answer:
"""
USER_PROMPT_PART_SECOND_ANSWER_HEADER = """\
Second answer:
"""
USER_PROMPT_PART_TEXT_ANSWER_BODY = """\
Text answer:
```{text}```
"""
USER_PROMPT_PART_IMAGE_ANSWER_BODY = """\
Image answer:
Image filename: {image_filename}
Image:
"""


@dataclass
class ImageData:
    image: Image.Image
    image_filename: str


def init_model():
    # load the processor
    processor = Qwen2VLProcessor.from_pretrained(LABELING_MODEL_ID)
    # load the model
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        LABELING_MODEL_ID,
        torch_dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
        device_map="auto",
    )
    return processor, model


def run_model(
    processor,
    model,
    query: str,
    doc1: Union[str, ImageData],
    doc2: Union[str, ImageData],
) -> str:
    user_messages = [
        {"type": "text", "text": USER_PROMPT_PART_QUERY.format(query=query)},
        *_get_user_messages_for_answer(doc1, is_first_answer=True),
        *_get_user_messages_for_answer(doc2, is_first_answer=False),
    ]

    messages = [
        {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
        {"role": "user", "content": user_messages},
    ]
    text_prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
    images = [doc.image for doc in (doc1, doc2) if isinstance(doc, ImageData)]
    # process images and text
    inputs = processor(
        text=[text_prompt], images=images, padding=True, return_tensors="pt"
    ).to(model.device)
    # generate output
    output = model.generate(**inputs, max_new_tokens=500)
    generated_tokens = output[0, inputs["input_ids"].size(1) :]
    # decode generated tokens to text
    generated_text = "".join(
        processor.batch_decode(
            generated_tokens,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )
    )
    logger.info(generated_text)
    left_bracket_index = generated_text.rfind("{")
    right_bracket_index = generated_text.rfind("}")
    if left_bracket_index == -1 or right_bracket_index == -1:
        left_bracket_index, right_bracket_index = 0, len(generated_text) - 1
    return generated_text[left_bracket_index : right_bracket_index + 1]


def _get_user_messages_for_answer(
    doc: Union[str, ImageData], *, is_first_answer: bool
) -> List[Dict[str, str]]:
    answer_header = (
        USER_PROMPT_PART_FIRST_ANSWER_HEADER
        if is_first_answer
        else USER_PROMPT_PART_SECOND_ANSWER_HEADER
    )
    if isinstance(doc, str):
        answer_body = USER_PROMPT_PART_TEXT_ANSWER_BODY.format(text=doc)
    elif isinstance(doc, ImageData):
        answer_body = USER_PROMPT_PART_IMAGE_ANSWER_BODY.format(
            image_filename=doc.image_filename
        )
    else:
        raise TypeError(
            f"Invalid type for doc. Expected str or ImageData, got {type(doc)}"
        )

    answer_user_messages = [{"type": "text", "text": answer_header + answer_body}]
    if isinstance(doc, ImageData):
        answer_user_messages += [{"type": "image"}]

    return answer_user_messages
