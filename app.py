from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io, os, textwrap, json

app = Flask(__name__)
CORS(app)

BLANK_ADDENDUM = os.path.join(os.path.dirname(__file__), 'addendum_blank.pdf')

# ── PDF coordinate map for Addendum to REPC (Utah DRE Form) ──────────────────
# PDF is 612x792 points. y=0 is BOTTOM in PDF coords, so we flip: pdf_y = 792 - top
def top_to_y(top): return 792 - top

ADDENDUM_FIELDS = {
    'addendum_no':    {'x': 348, 'y': top_to_y(78),  'size': 11, 'bold': True},
    'offer_date':     {'x': 36,  'y': top_to_y(132),  'size': 9},
    'buyer':          {'x': 36,  'y': top_to_y(138),  'size': 9, 'max_width': 200},
    'seller':         {'x': 300, 'y': top_to_y(138),  'size': 9, 'max_width': 230},
    'property':       {'x': 155, 'y': top_to_y(156),  'size': 8, 'max_width': 160},
    'response_party': {'x': 37,  'y': top_to_y(509),  'size': 9},
    'response_date':  {'x': 370, 'y': top_to_y(509),  'size': 9},
    'response_time':  {'x': 180, 'y': top_to_y(509),  'size': 9},
}

# Terms body area: x=36, top=162 to top=478 (large blank space)
TERMS_AREA = {'x': 36, 'y_start': top_to_y(165), 'width': 540, 'line_height': 13, 'size': 10}


def fill_addendum(data):
    """Fill the blank Addendum PDF with provided data. Returns bytes."""
    # Create overlay with filled text
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=letter)
    c.setFont("Helvetica", 10)

    # Fill named fields
    for field, cfg in ADDENDUM_FIELDS.items():
        val = str(data.get(field, '')).strip()
        if not val:
            continue
        size = cfg.get('size', 9)
        bold = cfg.get('bold', False)
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        max_width = cfg.get('max_width', 400)
        # Truncate if too long for single line
        while c.stringWidth(val, font, size) > max_width and len(val) > 3:
            val = val[:-1]
        c.drawString(cfg['x'], cfg['y'], val)

    # Fill terms (multi-line wrap)
    terms = str(data.get('terms', '')).strip()
    if terms:
        c.setFont("Helvetica", TERMS_AREA['size'])
        # Wrap text to fit width
        avg_char_width = TERMS_AREA['size'] * 0.55
        chars_per_line = int(TERMS_AREA['width'] / avg_char_width)
        lines = []
        for para in terms.split('\n'):
            if para.strip():
                wrapped = textwrap.wrap(para, width=chars_per_line)
                lines.extend(wrapped)
                lines.append('')  # paragraph break
            else:
                lines.append('')

        y = TERMS_AREA['y_start']
        min_y = top_to_y(475)  # don't go below terms area
        for line in lines:
            if y < min_y:
                break
            c.drawString(TERMS_AREA['x'], y, line)
            y -= TERMS_AREA['line_height']

    c.save()
    packet.seek(0)

    # Merge overlay onto blank PDF
    overlay = PdfReader(packet)
    base = PdfReader(BLANK_ADDENDUM)
    writer = PdfWriter()
    page = base.pages[0]
    page.merge_page(overlay.pages[0])
    writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    output.seek(0)
    return output


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'TC PDF API'})


@app.route('/fill-addendum', methods=['POST', 'OPTIONS'])
def fill_addendum_endpoint():
    if request.method == 'OPTIONS':
        return '', 204
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Required fields check
        addendum_no = data.get('addendum_no', '1')
        buyer = data.get('buyer', '')
        seller = data.get('seller', '')
        property_addr = data.get('property', '')
        terms = data.get('terms', '')
        offer_date = data.get('offer_date', '')
        response_date = data.get('response_date', '')
        response_time = data.get('response_time', '5:00 PM')
        response_party = data.get('response_party', '')

        fill_data = {
            'addendum_no': addendum_no,
            'buyer': buyer,
            'seller': seller,
            'property': property_addr,
            'terms': terms,
            'offer_date': offer_date,
            'response_date': response_date,
            'response_time': response_time,
            'response_party': response_party,
        }

        pdf_bytes = fill_addendum(fill_data)

        filename = f"Addendum_No_{addendum_no}_{property_addr.split(',')[0].replace(' ','_')}.pdf"

        return send_file(
            pdf_bytes,
            mimetype='application/pdf',
            as_attachment=False,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
