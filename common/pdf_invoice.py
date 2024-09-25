import os
import re
import logging
import inflect
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

# This is needed for language other then English otherwise inflect will do
def number_to_latvian_words(num):
    units = ["", "viens", "divi", "trīs", "četri", "pieci", "seši", "septi", "astoņi", "deviņi"]
    teens = ["desmit", "vienpadsmit", "divpadsmit", "trīspadsmit", "četrpadsmit", "piecpadsmit", "sešpadsmit", "septiņpadsmit", "astoņpadsmit", "deviņpadsmit"]
    tens = ["", "desmit", "divdesmit", "trīsdesmit", "četrdesmit", "piecdesmit", "sešdesmit", "septiņdesmit", "astoņdesmit", "deviņdesmit"]
    hundreds = ["", "simts", "divi simti", "trīs simti", "četri simti", "pieci simti", "seši simti", "septiņi simti", "astoņi simti", "deviņi simti"]

    if num == 0:
        return "nulle"

    words = []
    
    # Handle hundreds
    if num >= 100:
        words.append(hundreds[num // 100])
        num %= 100
    
    # Handle tens and units
    if num >= 20:
        words.append(tens[num // 10])
        num %= 10
    
    if 10 <= num < 20:
        words.append(teens[num - 10])
    elif num < 10:
        words.append(units[num])
    
    return ' '.join(filter(bool, words)).strip()

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

def user_invoice_num() -> str:
    today_str = datetime.now().strftime("%d%m%y")
    invoice_number = get_invoice_number()
    user_invoice = f"OG_{today_str}_{invoice_number}"
    return user_invoice

def generate_pdf(user_info: dict, game_info: dict, lang: str) -> str:
    today_str = datetime.now().strftime("%d%m%y")
    invoice_number = get_invoice_number()
    game_info = user_info.get('game_details', {})
    if not game_info:
        logging.error("Game details are missing in user_info.")
    game_name = game_info.get('game_name', "GAME")
    game_date_str = game_info.get('date', "")
    try:
        unit_price = float(game_info.get('price_per_person', 0.00))
    except ValueError:
        logging.error(f"Invalid price_per_person in game_info: {game_info.get('price_per_person')}")
        unit_price = 0.00

     
    if not game_date_str:
        logging.warning("Game date is missing. Using current date as fallback.")
        game_date = datetime.now()
    else:
        try:
            game_date = datetime.strptime(game_date_str, '%Y-%m-%d')
        except ValueError:
            logging.error(f"Invalid date format for game_date_str: {game_date_str}")
            game_date = datetime.now()

    formatted_game_date = game_date.strftime('%d.%m.%y')

    cust_amount = user_info.get('cust_amount', 0)
    total_amount = cust_amount * unit_price

    total_amount_words = number_to_latvian_words(int(total_amount)) + " eiro un " + number_to_latvian_words(int((total_amount % 1) * 100)) + " centi"

    logging.info(f"Game Name: {game_name}, Game Date: {formatted_game_date}, Unit Price: {unit_price}, Total Amount: {total_amount}")

    pdf_filename = f"OG_{today_str}_{invoice_number}_{user_info['first_name']}_{user_info['last_name']}.pdf"
    user_invoice = f"OG_{today_str}_{invoice_number}"
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
    formatted_game_date = game_date.strftime('%d.%m.%y')
    total_amount = user_info.get('cust_amount', 0) * unit_price
    table_data = [
        ["Nosaukums", "Mērv.", "Daudzums", "Cena", "Summa"],
        [f"{game_name} {formatted_game_date}", "kompl.", str(user_info.get('cust_amount', 0)), f"{unit_price:.2f} EUR", f"{total_amount:.2f} EUR"]
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
        ["", "Kopā apmaksai", "", total_amount_words],
        ["", "", "", ""]
    ]

    total_table = Table(total_data, colWidths=[7 * cm, 2 * cm, 2 * cm, 6 * cm])
    total_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'DejaVuSans', 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('SPAN', (0, 1), (2, 1)), 
    ]))
    elements.append(total_table)

    doc.build(elements)
    return pdf_path
