import logging
import io
import base64
import json
import cv2
import numpy as np
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.pdf import PageObject
import azure.functions as func


def detect_and_correct_orientation(image_data):
    # Convert the base64-encoded image data to a NumPy array
    image_array = np.frombuffer(base64.b64decode(image_data), np.uint8)

    # Load the image using OpenCV
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply adaptive thresholding to segment text and background
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)

    # Apply morphological operations to enhance text regions
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    # Find contours of text regions
    contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Calculate the orientations and aspect ratios of each contour
    angles = []
    aspect_ratios = []
    for contour in contours:
        (x, y, w, h) = cv2.boundingRect(contour)
        moments = cv2.moments(contour)
        center_x = moments["m10"] / moments["m00"]
        center_y = moments["m01"] / moments["m00"]
        angle = np.degrees(np.arctan2(center_y - y, center_x - x))
        angles.append(angle)
        aspect_ratio = w / h if h != 0 else 0
        aspect_ratios.append(aspect_ratio)

    # Calculate the average angle and aspect ratio of contours
    avg_angle = np.mean(angles)
    avg_aspect_ratio = np.mean(aspect_ratios)

    # If the average angle is close to 0 or 180, it suggests the text is upside down
    # or the image is skewed, we need to correct it
    if abs(avg_angle) < 90 or avg_aspect_ratio > 1:
        # Calculate the rotation angle for deskewing
        skew_angle = -avg_angle if avg_angle < 0 else 180 - avg_angle

        # Rotate the image to correct skew and orientation
        rotated_image = cv2.rotate(image, cv2.ROTATE_180)
        rotated_image = cv2.rotate(rotated_image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        rotated_image = cv2.rotate(rotated_image, cv2.ROTATE_180 + skew_angle)
    else:
        rotated_image = image

    # Encode the rotated image as base64
    _, image_data = cv2.imencode('.png', rotated_image)
    base64_image = base64.b64encode(image_data).decode()

    # Return the rotated image as base64
    return base64_image


def split_pdf(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        body = req.get_body()
        pdf_stream = io.BytesIO(body)
        pdf_reader = PdfReader(pdf_stream)

        pdf_pages = []
        for page_num in range(len(pdf_reader.pages)):
            output_stream = io.BytesIO()
            pdf_writer = PdfWriter()
            page = pdf_reader.pages[page_num]

            # Get the base64-encoded page content
            page_content = base64.b64encode(page.extract_xobject_content()).decode()

            # Detect and correct the page orientation
            corrected_page_content = detect_and_correct_orientation(page_content)

            # Add the corrected page to the PDF writer
            pdf_writer.add_page(PageObject.create_blank_page())
            pdf_writer.add_page(page)

            # Set the corrected content for the page
            pdf_writer.pages[0].indirect_object.object_stream = corrected_page_content.encode()

            # Write the modified PDF to the output stream
            pdf_writer.write(output_stream)

            # Append the base64-encoded modified page to the list
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
        return func.HttpResponse(
            body=json.dumps({'error': str(e)}),
            mimetype='application/json',
            status_code=500
        )
        
