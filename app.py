from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io, os, textwrap
from forms_data import get_form

app = Flask(__name__)
CORS(app, origins="*")

# PDF is 612x792 points. y=0 is BOTTOM, so flip: pdf_y = 792 - top
def yp(top): return 792 - top

def draw(c, text, x, top, size=9, bold=False, max_w=500):
    if not str(text).strip(): return
    font = "Helvetica-Bold" if bold else "Helvetica"
    c.setFont(font, size)
    val = str(text).strip()
    while c.stringWidth(val, font, size) > max_w and len(val) > 2:
        val = val[:-1]
    c.drawString(x, yp(top), val)

def clean_terms(text):
    import re
    text = str(text).strip()
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'_{1,2}(.+?)_{1,2}', r'\1', text)
    text = re.sub(r'^(Property Address|Buyer.s.|Seller.s.|Offer Reference Date|ADDENDUM NO\.|Address|Buyer|Seller)[:\s].*$', '', text, flags=re.MULTILINE|re.IGNORECASE)
    text = re.sub(r'^[-_]{2,}\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^ADDENDUM NO\..*$', '', text, flags=re.MULTILINE|re.IGNORECASE)
    text = re.sub(r'^\d+\.\s+[A-Z ]{4,}$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^[-*•]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def draw_wrapped(c, text, x, top, width=540, size=10, line_h=13, max_top=478):
    if not str(text).strip(): return
    text = clean_terms(text)

    c.setFont("Helvetica", size)
    chars = int(width / (size * 0.52))
    cur_y = yp(top)
    min_y = yp(max_top)
    for para in text.split('\n'):
        para = para.strip()
        lines = textwrap.wrap(para, chars) if para else ['']
        for line in lines:
            if cur_y < min_y: return
            c.drawString(x, cur_y, line)
            cur_y -= line_h
        cur_y -= 3  # paragraph gap

def merge_overlay(base_bytes, overlay_bytes):
    overlay_pdf = PdfReader(overlay_bytes)
    base_pdf = PdfReader(base_bytes)
    writer = PdfWriter()
    for i, page in enumerate(base_pdf.pages):
        if i == 0:
            page.merge_page(overlay_pdf.pages[0])
        writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out

def fill_addendum(data):
    p = io.BytesIO()
    c = canvas.Canvas(p, pagesize=letter)

    # Addendum number — after "NO." in header
    draw(c, data.get('addendum_no','1'), 348, 70, size=11, bold=True)

    # Offer reference date — line below header row
    draw(c, data.get('offer_date',''), 36, 124, size=8)

    # Buyer name — "between ______ as Buyer"
    draw(c, data.get('buyer',''), 36, 138, size=9, max_w=200)

    # Seller name — "and ______ as Seller"
    draw(c, data.get('seller',''), 300, 138, size=9, max_w=228)

    # Property address — "regarding the Property located at ______"
    draw(c, data.get('property',''), 155, 149, size=7.5, max_w=160)

    # Addendum terms — large blank body area
    draw_wrapped(c, data.get('terms',''), 36, 160, width=540, size=10, line_h=13, max_top=478)

    # Responding party — X in Seller or Buyer bracket
    resp = data.get('response_party','Seller').strip().lower()
    if resp == 'seller':
        draw(c, 'X', 38, 504, size=9)   # Seller checkbox
    else:
        draw(c, 'X', 79, 504, size=9)   # Buyer checkbox

    # Response time
    draw(c, data.get('response_time','5:00'), 180, 504, size=9)
    # PM checkbox
    draw(c, 'X', 268, 504, size=9)

    # Response deadline date
    draw(c, data.get('response_date',''), 370, 504, size=9)

    c.save(); p.seek(0)
    return merge_overlay(get_form('addendum'), p)


def fill_buyer_broker(data):
    p = io.BytesIO()
    c = canvas.Canvas(p, pagesize=letter)
    draw(c, data.get('company',''),        106, 110, size=9, max_w=130)
    draw(c, data.get('agent',''),          260, 110, size=9, max_w=180)
    draw(c, data.get('buyer',''),          36,  120, size=9, max_w=420)
    draw(c, data.get('end_date',''),       36,  165, size=9, max_w=320)
    draw(c, data.get('counties',''),       36,  185, size=9, max_w=420)
    draw(c, data.get('commission_pct',''), 36,  310, size=9)
    c.save(); p.seek(0)
    return merge_overlay(get_form('buyer_broker'), p)


def fill_listing_agreement(data):
    p = io.BytesIO()
    c = canvas.Canvas(p, pagesize=letter)
    draw(c, data.get('company',''),        106, 110, size=9, max_w=130)
    draw(c, data.get('agent',''),          260, 110, size=9, max_w=180)
    draw(c, data.get('seller',''),         36,  120, size=9, max_w=420)
    draw(c, data.get('property',''),       36,  140, size=9, max_w=420)
    draw(c, data.get('listing_end',''),    36,  160, size=9, max_w=320)
    draw(c, data.get('listing_price',''),  36,  295, size=9)
    draw(c, data.get('commission_pct',''), 36,  315, size=9)
    c.save(); p.seek(0)
    return merge_overlay(get_form('listing_agreement'), p)


def fill_wire_fraud(data, form_key):
    p = io.BytesIO()
    c = canvas.Canvas(p, pagesize=letter)
    draw(c, data.get('company',''), 36, 95,  size=9, max_w=200)
    draw(c, data.get('agent',''),   36, 105, size=9, max_w=200)
    client = data.get('buyer','') if form_key == 'wire_fraud_buyer' else data.get('seller','')
    draw(c, client, 36, 115, size=9, max_w=400)
    c.save(); p.seek(0)
    return merge_overlay(get_form(form_key), p)


def fill_seller_disclosure(data):
    p = io.BytesIO()
    c = canvas.Canvas(p, pagesize=letter)
    draw(c, data.get('seller',''),  200, 65, size=9, max_w=300)
    draw(c, data.get('agent',''),   36,  78, size=9, max_w=200)
    draw(c, data.get('company',''), 250, 78, size=9, max_w=200)
    c.save(); p.seek(0)
    return merge_overlay(get_form('seller_disclosure'), p)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status':'ok','forms':['addendum','repc','buyer_broker','listing_agreement','wire_fraud_buyer','wire_fraud_seller','seller_disclosure']})

@app.route('/fill/<form_key>', methods=['POST','OPTIONS'])
def fill_form(form_key):
    if request.method == 'OPTIONS': return '',204
    try:
        data = request.get_json(force=True) or {}
        fk = form_key.lower().replace('-','_')
        if fk == 'addendum':              pdf = fill_addendum(data)
        elif fk == 'buyer_broker':        pdf = fill_buyer_broker(data)
        elif fk == 'listing_agreement':   pdf = fill_listing_agreement(data)
        elif fk in ('wire_fraud_buyer','wire_fraud_seller'): pdf = fill_wire_fraud(data, fk)
        elif fk == 'seller_disclosure':   pdf = fill_seller_disclosure(data)
        else: return jsonify({'error':f'Unknown form: {fk}'}),400

        prop = data.get('property','doc').split(',')[0].replace(' ','_').replace('/','_')
        num  = data.get('addendum_no','')
        name = f"{fk}{'_'+num if num else ''}_{prop}.pdf"
        return send_file(pdf, mimetype='application/pdf', as_attachment=False, download_name=name)
    except Exception as e:
        import traceback
        return jsonify({'error':str(e),'trace':traceback.format_exc()}),500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)))
