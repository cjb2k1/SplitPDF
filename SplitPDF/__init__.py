import logging
import io
from PyPDF2 import PdfFileReader, PdfFileWriter
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        body = req.get_body()
        pdf_stream = io.BytesIO(body)
        pdf_reader = PdfFileReader(pdf_stream)

        pdf_pages = []
        for page_num in range(pdf_reader.getNumPages()):
            output_stream = io.BytesIO()
            pdf_writer = PdfFileWriter()
            pdf_writer.addPage(pdf_reader.getPage(page_num))
            pdf_writer.write(output_stream)
            pdf_pages.append(output_stream.getvalue())

        return func.HttpResponse(body=pdf_pages, mimetype='application/octet-stream')

    except Exception as e:
        logging.error(str(e))
        return func.HttpResponse('An error occurred.', status_code=500)


