from pdf2image import convert_from_path
import pytesseract
import cv2
import numpy as np
from PIL import Image
import pdfplumber


class LegalOCRExtractor:
    """
    Production-grade OCR extractor for legal documents
    """

    def __init__(self, dpi: int = 300):
        self.dpi = dpi

    # ---------------------------
    # IMAGE PREPROCESSING
    # ---------------------------

    def preprocess_image(self, image: Image.Image) -> np.ndarray:

        img = np.array(image)

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Denoise
        gray = cv2.fastNlMeansDenoising(gray, None, 30, 7, 21)

        # Thresholding (important for legal docs)
        _, thresh = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        return thresh

    # ---------------------------
    # SINGLE PAGE OCR
    # ---------------------------

    def ocr_page(self, image: Image.Image) -> str:

        processed_img = self.preprocess_image(image)

        config = r'--oem 3 --psm 6'

        text = pytesseract.image_to_string(
            processed_img,
            lang='eng',
            config=config
        )

        return text

    # ---------------------------
    # MAIN FUNCTION
    # ---------------------------


    def extract_text(self,pdf_path):
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        return text

# ---------------------------
# TEST RUN
# ---------------------------

if __name__ == "__main__":

    pdf_path = "./constitution_of_india.pdf"  

    extractor = LegalOCRExtractor(dpi=300)

    text = extractor.extract_text(pdf_path)

    # Save output
    with open("text_extracted_ocr_output.txt", "w", encoding="utf-8") as f:
        f.write(text)

    print("\nOCR extraction completed. Output saved to output.txt")