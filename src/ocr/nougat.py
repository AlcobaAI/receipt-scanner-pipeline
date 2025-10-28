from transformers import NougatProcessor, VisionEncoderDecoderModel
import torch
from PIL import Image
import argparse

processor = NougatProcessor.from_pretrained("facebook/nougat-base")
model = VisionEncoderDecoderModel.from_pretrained("facebook/nougat-base")

device = "cuda" if torch.cuda.is_available() else "cpu"
model.to(device)

def run_ocr(filepath: str) -> str:
    """
    Performs OCR on the image at the given filepath using the Nougat model.
poet
    Args:
        filepath: The path to the image file.

    Returns:
        The extracted text as a string.
    """
    image = Image.open(filepath)
    pixel_values = processor(image, return_tensors="pt").pixel_values

    outputs = model.generate(
        pixel_values.to(device),
        min_length=1,
        max_new_tokens=30,
        bad_words_ids=[[processor.tokenizer.unk_token_id]],
    )

    sequence = processor.batch_decode(outputs, skip_special_tokens=True)[0]
    sequence = processor.post_process_generation(sequence, fix_markdown=False)

    return sequence

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run Nougat OCR on an image file.")
    parser.add_argument("--filepath", type=str, required=True, help="The path to the image file.")
    args = parser.parse_args()

    print(f"Running OCR on: {args.filepath}")
    text_result = run_ocr(args.filepath)
    print("\n--- OCR Result ---")
    print(repr(text_result))