import os
import re
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet

# Load the font that supports Latvian characters
pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))

def get_invoice_number() -> int:
    today = datetime.now().strftime("%d%m%y")
    folder = "./invoice_store"
    pattern = re.compile(fr"OG_{today}_(\d+)_.*\.pdf")
    numbers = []

    if not os.path.exists(folder):
        os.makedirs(folder)

    for filename in os.listdir(folder):
        match = pattern.match(filename)
        if match:
            numbers.append(int(match.group(1)))

    return max(numbers) + 1 if numbers else 1

def generate_pdf(user_info: dict, game_info: dict, lang: str) -> str:
    # Generate a PDF invoice with tables
    today_str = datetime.now().strftime("%d%m%y")
    invoice_number = get_invoice_number()
    unit_price = float(game_info.get('price_per_person', 0.00))
    pdf_filename = f"OG_{today_str}_{invoice_number}_{user_info['first_name']}_{user_info['last_name']}.pdf"
    pdf_path = os.path.join("./invoice_store", pdf_filename)

    # Create the PDF document
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    elements = []

    # Header - Invoice and Date Information
    styles = getSampleStyleSheet()
    header_data = [ 
    ["Maksātājs"],
    [f"{user_info.get('first_name', 'First Name')} {user_info.get('last_name', 'Last Name')}"],
    ["", " ", " "],  
    ["", " ", " "], 
    ["Piegādātājs", " ", f"RĒĶINS Nr OG/{today_str}/{invoice_number}"],
    ['LTD "Company"', " ", f"no {datetime.now().strftime('%d.%m.%Y')}"],
    ["Reģ. Nr 123456789", " ", " "],
    ["Street 12-34, City, Post-Code", " ", " "],
    ['Norēķinu konta Nr ', " ", " "],
    ['AS "Banka" SWIFT (BIC) kods: 123456', " ", " "]
]

    header_table = Table(header_data, colWidths=[6 * cm, 2 * cm, 7 * cm])
    header_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'DejaVuSans', 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))

    elements.append(header_table)

    # Add some space before the table
    elements.append(Table([[" "]]))

    # Main Invoice Table
    event_date = datetime.now() + timedelta(days=14)
    total_amount = user_info.get('cust_amount', 0) * unit_price
    table_data = [
        ["Nosaukums", "Mērv.", "Daudzums", "Cena", "Summa"],
        [f"Open games {event_date.strftime('%d.%m.%y')}", "kompl.", str(user_info.get('cust_amount', 0)), f"{unit_price:.2f} EUR", f"{total_amount:.2f} EUR"]
    ]

    invoice_table = Table(table_data, colWidths=[7 * cm, 2 * cm, 2 * cm, 3 * cm, 3 * cm])
    invoice_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'DejaVuSans', 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    elements.append(invoice_table)

    # Total Amount
    total_data = [
        ["", "", "Kopā apmaksai", f"{total_amount:.2f} EUR"],
        ["", "", "", f"(Euro un centi)"]
    ]

    total_table = Table(total_data, colWidths=[7 * cm, 2 * cm, 2 * cm, 6 * cm])
    total_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'DejaVuSans', 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('SPAN', (0, 1), (2, 1)),  # Span the first three columns in the second row
    ]))
    elements.append(total_table)

    doc.build(elements)
    return pdf_path
