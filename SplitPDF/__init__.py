import logging
import io
import base64
from PyPDF2 import PdfReader, PdfWriter
import azure.functions as func
import json


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        body = req.get_body()
        pdf_stream = io.BytesIO(body)
        pdf_reader = PdfReader(pdf_stream)

        pdf_pages = []
        for page_num in range(len(pdf_reader.pages)):
            output_stream = io.BytesIO()
            pdf_writer = PdfWriter()
            pdf_writer.add_Page(pdf_reader.getPage(page_num))
            pdf_writer.write(output_stream)
            pdf_pages.append(base64.b64encode(output_stream.getvalue()).decode())

        response_data = {
            'pages': pdf_pages
        }

        return func.HttpResponse(
            body=json.dumps(response_data),
            mimetype='application/json'
        )

    except Exception as e:
        logging.error(str(e))
        return func.HttpResponse('An error occurred.', status_code=500)
