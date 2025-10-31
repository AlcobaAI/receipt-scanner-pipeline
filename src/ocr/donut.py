import re
import json
from transformers import DonutProcessor, VisionEncoderDecoderModel
import torch
from PIL import Image
import argparse

processor = DonutProcessor.from_pretrained("naver-clova-ix/donut-base-finetuned-cord-v2")
model = VisionEncoderDecoderModel.from_pretrained("naver-clova-ix/donut-base-finetuned-cord-v2")

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

def run_ocr(filepath: str) -> str:
    """
    Performs OCR on the image at the given filepath using the Donut model.

    Args:
        filepath: The path to the image file.

    Returns:
        The extracted text as a JSON string.
    """
    image = Image.open(filepath).convert("RGB")
    
    task_prompt = "<s_cord-v2>"
    decoder_input_ids = processor.tokenizer(task_prompt, add_special_tokens=False, return_tensors="pt").input_ids

    pixel_values = processor(image, return_tensors="pt").pixel_values

    outputs = model.generate(
        pixel_values.to(device),
        pad_token_id=processor.tokenizer.pad_token_id,
        eos_token_id=processor.tokenizer.eos_token_id,
        use_cache=True,
        decoder_input_ids=decoder_input_ids.to(device),
        max_length=model.decoder.config.max_position_embeddings,
        bad_words_ids=[[processor.tokenizer.unk_token_id]],
        return_dict_in_generate=True,
    )

    sequence = processor.batch_decode(outputs.sequences)[0]
    sequence = sequence.replace(processor.tokenizer.eos_token, "").replace(processor.tokenizer.pad_token, "")
    sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()
    return json.dumps(processor.token2json(sequence))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run Donut OCR on an image file.")
    parser.add_argument("--filepath", type=str, required=True, help="The path to the image file.")
    args = parser.parse_args()

    print(f"Running OCR on: {args.filepath}")
    text_result = run_ocr(args.filepath)
    print("\n--- OCR Result (JSON) ---")
    print(text_result)