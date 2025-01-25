from flask import Flask, request
import concurrent.futures
import pdfplumber
import os
import threading

app = Flask(__name__)

OUTPUT_DIR = "output_files"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def process_page_batch(file_path, page_range, output_dir):
    with pdfplumber.open(file_path) as pdf:
        for page_num in page_range:
            if page_num >= len(pdf.pages):
                break  
            page = pdf.pages[page_num]

            text = page.extract_text()
            text_file_path = os.path.join(output_dir, f"page_{page_num + 1}.txt")
            with open(text_file_path, "w") as text_file:
                text_file.write(text or "No text on this page.")
            
            page_image = page.to_image()  
            image = page_image.original 
            image = image.convert("RGB") 
            image_path = os.path.join(output_dir, f"page_{page_num + 1}.jpg")
            image.save(image_path, format="JPEG", optimize=True, quality=50)
    return f"Processed pages {page_range[0] + 1} to {page_range[-1] + 1}."

def process_pdf_in_batches(file_path, output_dir, batch_size=30):
    with pdfplumber.open(file_path) as pdf:
        num_pages = len(pdf.pages)

    page_ranges = [range(i, min(i + batch_size, num_pages)) for i in range(0, num_pages, batch_size)]

    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = [executor.submit(process_page_batch, file_path, page_range, output_dir) for page_range in page_ranges]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    return results

def handle_file_processing(file_path, output_dir):
    """Handles the file processing in the background."""
    process_pdf_in_batches(file_path, output_dir, batch_size=20)  

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file part", 400

    uploaded_files = request.files.getlist("file")

    for file in uploaded_files:
        output_dir = os.path.join(OUTPUT_DIR, file.filename.rsplit('.', 1)[0])
        os.makedirs(output_dir, exist_ok=True)

        file_path = os.path.join(output_dir, file.filename)
        file.save(file_path)

        threading.Thread(target=handle_file_processing, args=(file_path, output_dir), daemon=True).start()
        
    return {"message": "Files uploaded and processing started in the background."}, 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
