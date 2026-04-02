from flask import Flask, render_template, request, send_file, jsonify
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import Color
from datetime import datetime
import io
import json
import sys
import os
import textwrap

# Handle PyInstaller bundled app
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    bundle_dir = sys._MEIPASS
    template_folder = os.path.join(bundle_dir, 'templates')
    static_folder = os.path.join(bundle_dir, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    # Running as script
    app = Flask(__name__)

# Disable template caching for development
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.route('/')
def index():
    """Home page with list of available forms"""
    return render_template('index.html')

@app.route('/scheduling-dispatch')
def scheduling_dispatch():
    """Scheduling Dispatch Request Form"""
    # Pre-fill today's date
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('scheduling_dispatch.html', today=today)

@app.route('/special-order')
def special_order():
    """Special Order Request Form"""
    # Pre-fill today's date
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('special_order.html', today=today)

@app.route('/change-order')
def change_order():
    """Changes / Upgrades / Additions Form"""
    # Pre-fill today's date
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('change_order.html', today=today)

@app.route('/hvac-bid')
def hvac_bid():
    """HVAC Bid Sheet"""
    # Pre-fill today's date
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('hvac_bid.html', today=today)

@app.route('/design-walk')
def design_walk():
    """Design Plan Walk Sheet"""
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('design_walk.html', today=today)

@app.route('/quick-bid')
def quick_bid():
    """QuickBid - Smart HVAC Estimator"""
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('quick_bid.html', today=today)

@app.route('/bid-info')
def bid_info():
    """Bid Info Sheet - Manual J Request Form"""
    return render_template('bid_info.html')

@app.route('/additional-work')
def additional_work():
    """Additional Work / Change Order Form"""
    return render_template('additional_work.html')

@app.route('/linear-grille')
def linear_grille():
    """Linear Grille Order Form"""
    today = datetime.now().strftime('%Y-%m-%d')
    return render_template('linear_grille.html', today=today)

@app.route('/generate-bid-info-pdf', methods=['POST'])
def generate_bid_info_pdf():
    """Generate PDF from Bid Info Sheet"""
    form_data = request.form.to_dict()
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, height - 0.5*inch, "Load Calculation Request Form")
    c.setFont("Helvetica", 9)
    c.drawCentredString(width/2, height - 0.65*inch, "Woods Comfort Systems | TACLA16934C")
    
    y = height - 1*inch
    
    def draw_section_header(title, y_pos):
        c.setFont("Helvetica-Bold", 11)
        c.setFillColorRGB(0.08, 0.4, 0.75)  # Blue
        c.drawString(0.5*inch, y_pos, title)
        c.setFillColorRGB(0, 0, 0)
        c.line(0.5*inch, y_pos - 3, width - 0.5*inch, y_pos - 3)
        return y_pos - 0.2*inch
    
    def draw_field(label, value, x, y_pos):
        c.setFont("Helvetica-Bold", 8)
        c.drawString(x, y_pos, label)
        c.setFont("Helvetica", 8)
        label_width = c.stringWidth(label, "Helvetica-Bold", 8)
        c.drawString(x + label_width + 3, y_pos, str(value or ''))
        return y_pos - 0.15*inch
    
    # PROJECT INFORMATION
    y = draw_section_header("PROJECT INFORMATION", y)
    y = draw_field("Salesperson:", form_data.get('salesperson', ''), 0.5*inch, y)
    c.drawString(3*inch, y + 0.15*inch, f"Bid Type: {form_data.get('bid_type', '')}")
    c.drawString(5.5*inch, y + 0.15*inch, f"Due Date: {form_data.get('due_date', '')}")
    y = draw_field("Builder/Customer:", form_data.get('builder_name', ''), 0.5*inch, y)
    y = draw_field("Job Location:", form_data.get('job_location', ''), 0.5*inch, y)
    y = draw_field("Permit Required:", form_data.get('permit_required', ''), 0.5*inch, y)
    c.drawString(3*inch, y + 0.15*inch, f"Cost: ${form_data.get('permit_cost', '')}")
    y = draw_field("Special Requirements:", form_data.get('special_requirements', ''), 0.5*inch, y)
    y = draw_field("House Direction:", form_data.get('house_direction', ''), 0.5*inch, y)
    c.drawString(3*inch, y + 0.15*inch, f"Energy Star: {form_data.get('energy_star', '')}")
    y -= 0.1*inch
    
    # CONSTRUCTION SPECIFICATIONS
    y = draw_section_header("CONSTRUCTION SPECIFICATIONS", y)
    y = draw_field("Insulation - Walls:", form_data.get('insulation_walls', ''), 0.5*inch, y)
    c.drawString(3*inch, y + 0.15*inch, f"Ceiling: {form_data.get('insulation_ceiling', '')}")
    y = draw_field("Windows:", f"LowE: {'Yes' if form_data.get('windows_lowe') else 'No'}, Vinyl: {'Yes' if form_data.get('windows_vinyl') else 'No'}", 0.5*inch, y)
    c.drawString(3.5*inch, y + 0.15*inch, f"U-value: {form_data.get('windows_uvalue', '')}")
    c.drawString(5*inch, y + 0.15*inch, f"SHGC: {form_data.get('windows_shgc', '')}")
    y = draw_field("Foundation:", form_data.get('foundation', ''), 0.5*inch, y)
    y = draw_field("Roof:", form_data.get('roof_type', ''), 0.5*inch, y)
    c.drawString(2.5*inch, y + 0.15*inch, f"Truss: {form_data.get('truss_type', '')}")
    c.drawString(4*inch, y + 0.15*inch, f"Depth: {form_data.get('truss_depth', '')}")
    y -= 0.1*inch
    
    # EQUIPMENT INFORMATION
    y = draw_section_header("EQUIPMENT INFORMATION", y)
    y = draw_field("System Breakdown:", form_data.get('system_breakdown', ''), 0.5*inch, y)
    c.drawString(3.5*inch, y + 0.15*inch, f"Comments: {form_data.get('system_breakdown_comments', '')}")
    y = draw_field("System Type:", form_data.get('system_type', ''), 0.5*inch, y)
    y = draw_field("Brand:", form_data.get('brand', ''), 0.5*inch, y)
    c.drawString(2.5*inch, y + 0.15*inch, f"AFUE: {form_data.get('afue', '')}")
    c.drawString(4*inch, y + 0.15*inch, f"SEER: {form_data.get('seer', '')}")
    y = draw_field("Furnace Model:", form_data.get('furnace_model', ''), 0.5*inch, y)
    y = draw_field("Condenser Model:", form_data.get('condenser_model', ''), 0.5*inch, y)
    c.drawString(4*inch, y + 0.15*inch, f"Coil: {form_data.get('coil_model', '')}")
    y = draw_field("Thermostat:", form_data.get('thermostat_model', ''), 0.5*inch, y)
    y -= 0.1*inch
    
    # VENTILATION SPECIFICATIONS
    y = draw_section_header("VENTILATION SPECIFICATIONS", y)
    y = draw_field("Bath Fans:", form_data.get('bath_fan_model', ''), 0.5*inch, y)
    c.drawString(4*inch, y + 0.15*inch, f"Qty: {form_data.get('bath_fan_qty', '')}")
    y = draw_field("Terminations:", f"Roof: {'Yes' if form_data.get('term_roof') else 'No'}, Sidewall: {'Yes' if form_data.get('term_sidewall') else 'No'}", 0.5*inch, y)
    y = draw_field("Kitchen Venting:", form_data.get('kitchen_venting', ''), 0.5*inch, y)
    c.drawString(3.5*inch, y + 0.15*inch, f"Makeup Air: {form_data.get('makeup_air', '')}")
    y = draw_field("Fresh Air:", form_data.get('fresh_air', ''), 0.5*inch, y)
    c.drawString(2.5*inch, y + 0.15*inch, f"Model: {form_data.get('fresh_air_model', '')}")
    y -= 0.1*inch
    
    # DESIGN SPECIFICATIONS
    y = draw_section_header("DESIGN SPECIFICATIONS", y)
    y = draw_field("Furnace Location:", form_data.get('furnace_location', ''), 0.5*inch, y)
    y = draw_field("Supply Locations:", form_data.get('supply_locations', ''), 0.5*inch, y)
    returns = []
    if form_data.get('return_central'): returns.append('Central')
    if form_data.get('return_central_master'): returns.append('Central+Master')
    if form_data.get('return_jumper'): returns.append('Jumper Ducts')
    y = draw_field("Return Locations:", ', '.join(returns), 0.5*inch, y)
    y = draw_field("Ductwork:", form_data.get('ductwork_type', ''), 0.5*inch, y)
    c.drawString(4*inch, y + 0.15*inch, f"Insulation: {form_data.get('duct_insulation', '')}")
    y = draw_field("Value Engineering:", form_data.get('value_engineering', ''), 0.5*inch, y)
    y = draw_field("Condenser Set:", form_data.get('condenser_set', ''), 0.5*inch, y)
    y -= 0.1*inch
    
    # INDOOR AIR QUALITY
    y = draw_section_header("INDOOR AIR QUALITY / OPTIONS", y)
    y = draw_field("Filtration:", form_data.get('filtration', ''), 0.5*inch, y)
    c.drawString(3.5*inch, y + 0.15*inch, f"MERV: {form_data.get('merv_rating', '')}")
    y = draw_field("Humidifier:", form_data.get('humidifier', ''), 0.5*inch, y)
    c.drawString(2.5*inch, y + 0.15*inch, f"Dehumidifier: {form_data.get('iaq_dehumidifier', '')}")
    y = draw_field("ERV/HRV:", form_data.get('erv_hrv', ''), 0.5*inch, y)
    y = draw_field("UV Light:", form_data.get('uv_light', ''), 0.5*inch, y)
    y -= 0.1*inch
    
    # COMMENTS
    y = draw_section_header("COMMENTS", y)
    comments = form_data.get('comments', '')
    if comments:
        c.setFont("Helvetica", 8)
        # Simple word wrap
        words = comments.split()
        line = ''
        for word in words:
            if c.stringWidth(line + ' ' + word, "Helvetica", 8) < (width - 1*inch):
                line += ' ' + word if line else word
            else:
                c.drawString(0.5*inch, y, line)
                y -= 0.12*inch
                line = word
        if line:
            c.drawString(0.5*inch, y, line)
    
    # Footer
    c.setFont("Helvetica", 8)
    c.drawCentredString(width/2, 0.4*inch, "Woods Comfort Systems | San Marcos, Texas | TACLA16934C")
    
    c.save()
    
    pdf_data = buffer.getvalue()
    buffer.close()
    
    builder = form_data.get('builder_name', 'Unknown').replace(' ', '_')
    today = datetime.now().strftime('%Y%m%d')
    filename = f"Load_Calc_Request_{builder}_{today}.pdf"
    
    return send_file(
        io.BytesIO(pdf_data),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

def draw_checkbox(c, x, y, checked=False, label=""):
    """Draw a checkbox with optional checkmark and label"""
    # Draw checkbox square
    c.rect(x, y, 12, 12)
    
    # Draw checkmark if checked
    if checked:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(x + 2, y + 1, "X")
        c.setFont("Helvetica", 11)
    
    # Draw label
    c.drawString(x + 20, y + 2, label)

@app.route('/generate-scheduling-dispatch-pdf', methods=['POST'])
def generate_scheduling_dispatch_pdf():
    """Generate PDF from scheduling dispatch form data"""
    # Get all form data
    form_data = request.form.to_dict()
    
    # Handle checkboxes (they won't be in form data if unchecked)
    checkboxes = ['po_required', 'permit_needed', 'cornice_done', 'decked_dried', 
                  'hvac_platform', 'power_available', 'generator_needed', 'propane_gas']
    
    for checkbox in checkboxes:
        form_data[checkbox] = checkbox in request.form
    
    # Create PDF in memory
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, height - 0.75*inch, "NEW CONSTRUCTION - SCHEDULING DISPATCH REQUEST")
    
    # Draw line under title
    c.line(0.75*inch, height - 0.9*inch, width - 0.75*inch, height - 0.9*inch)
    
    # Reset font
    c.setFont("Helvetica", 11)
    
    # Current Y position
    y = height - 1.2*inch
    
    # Helper function to draw labeled field
    def draw_field(label, value, x, y_pos, width_val=2.5*inch):
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x, y_pos, label)
        c.setFont("Helvetica", 11)
        label_width = c.stringWidth(label, "Helvetica-Bold", 11)
        c.line(x + label_width + 5, y_pos - 2, x + label_width + width_val, y_pos - 2)
        if value:
            c.drawString(x + label_width + 10, y_pos, str(value))
        return y_pos - 0.3*inch
    
    # Basic Information
    y = draw_field("Today's Date:", form_data.get('today_date', ''), 0.75*inch, y, 1.5*inch)
    y += 0.3*inch
    y = draw_field("Date Needed:", form_data.get('date_needed', ''), 4.5*inch, y, 1.5*inch)
    
    y -= 0.1*inch
    y = draw_field("Salesman:", form_data.get('salesman', ''), 0.75*inch, y, 1.8*inch)
    y += 0.3*inch
    y = draw_field("WCSI Field Super:", form_data.get('field_super', ''), 4.5*inch, y, 1.8*inch)
    
    y -= 0.1*inch
    y = draw_field("Builder:", form_data.get('builder', ''), 0.75*inch, y, 5.5*inch)
    
    y -= 0.1*inch
    y = draw_field("Job Address:", form_data.get('job_address', ''), 0.75*inch, y, 5.5*inch)
    
    y -= 0.1*inch
    y = draw_field("City:", form_data.get('city', ''), 0.75*inch, y, 1.5*inch)
    y += 0.3*inch
    y = draw_field("Zip:", form_data.get('zip', ''), 4.5*inch, y, 1.5*inch)
    
    y -= 0.1*inch
    y = draw_field("Plan/Resident:", form_data.get('plan_resident', ''), 0.75*inch, y, 1.8*inch)
    y += 0.3*inch
    y = draw_field("Subdivision:", form_data.get('subdivision', ''), 4.5*inch, y, 1.8*inch)
    
    y -= 0.1*inch
    y = draw_field("Number of Systems:", form_data.get('num_systems', ''), 0.75*inch, y, 1.5*inch)
    y += 0.3*inch
    y = draw_field("Estimated Time Needed:", form_data.get('estimated_time', ''), 4.5*inch, y, 1.5*inch)
    
    y -= 0.1*inch
    y = draw_field("GC Supervisor:", form_data.get('gc_supervisor', ''), 0.75*inch, y, 1.8*inch)
    y += 0.3*inch
    y = draw_field("Lockbox/Gate Code:", form_data.get('lockbox_code', ''), 4.5*inch, y, 1.8*inch)
    
    y -= 0.1*inch
    y = draw_field("GC Supervisor Phone Number:", form_data.get('gc_phone', ''), 0.75*inch, y, 4.5*inch)
    
    y -= 0.1*inch
    y = draw_field("Builder/GC Super/Homeowner Email:", form_data.get('email', ''), 0.75*inch, y, 4.5*inch)
    
    # ROUGH IN section
    y -= 0.3*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75*inch, y, "ROUGH IN")
    c.line(0.75*inch, y - 5, 2*inch, y - 5)
    
    y -= 0.3*inch
    c.setFont("Helvetica", 11)
    
    # Checkboxes in two columns
    col1_x = 0.75*inch
    col2_x = 4.25*inch
    
    draw_checkbox(c, col1_x, y, form_data.get('po_required', False), "PO Required: Yes")
    draw_checkbox(c, col2_x, y, not form_data.get('po_required', False), "No")
    y -= 0.25*inch
    
    draw_checkbox(c, col1_x, y, form_data.get('permit_needed', False), "Permit Needed: Yes")
    draw_checkbox(c, col2_x, y, not form_data.get('permit_needed', False), "No")
    y -= 0.25*inch
    
    draw_checkbox(c, col1_x, y, form_data.get('cornice_done', False), "Cornice Done: Yes")
    draw_checkbox(c, col2_x, y, not form_data.get('cornice_done', False), "No")
    y -= 0.25*inch
    
    draw_checkbox(c, col1_x, y, form_data.get('decked_dried', False), "Decked/Dried In: Yes")
    draw_checkbox(c, col2_x, y, not form_data.get('decked_dried', False), "No")
    y -= 0.25*inch
    
    draw_checkbox(c, col1_x, y, form_data.get('hvac_platform', False), "HVAC Platform: Yes")
    draw_checkbox(c, col2_x, y, not form_data.get('hvac_platform', False), "No")
    y -= 0.25*inch
    
    draw_checkbox(c, col1_x, y, form_data.get('power_available', False), "Power Available: Yes")
    draw_checkbox(c, col2_x, y, not form_data.get('power_available', False), "No")
    y -= 0.25*inch
    
    draw_checkbox(c, col1_x, y, form_data.get('generator_needed', False), "Generator Needed: Yes")
    draw_checkbox(c, col2_x, y, not form_data.get('generator_needed', False), "No")
    y -= 0.25*inch
    
    draw_checkbox(c, col1_x, y, form_data.get('propane_gas', False), "Propane Gas Furnace/LP Conversion: Yes")
    draw_checkbox(c, col2_x, y, not form_data.get('propane_gas', False), "No")
    
    # Notes section
    y -= 0.4*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75*inch, y, "NOTES:")
    c.line(0.75*inch, y - 5, 1.5*inch, y - 5)
    
    y -= 0.2*inch
    c.setFont("Helvetica", 11)
    c.rect(0.75*inch, y - 0.8*inch, width - 1.5*inch, 0.9*inch)
    
    # Draw notes text if present
    notes = form_data.get('notes', '')
    if notes:
        # Split notes into lines to fit in box
        text_obj = c.beginText(0.85*inch, y - 0.15*inch)
        text_obj.setFont("Helvetica", 10)
        # Simple line wrapping
        words = notes.split()
        line = ""
        for word in words:
            if c.stringWidth(line + " " + word, "Helvetica", 10) < (width - 2*inch):
                line += " " + word if line else word
            else:
                text_obj.textLine(line)
                line = word
        if line:
            text_obj.textLine(line)
        c.drawText(text_obj)
    
    # Project Information section
    y -= 1.2*inch
    c.line(0.75*inch, y, width - 0.75*inch, y)
    y -= 0.25*inch
    
    y = draw_field("WCSI NC Job Number:", form_data.get('wcsi_job_number', ''), 0.75*inch, y, 2*inch)
    y += 0.3*inch
    y = draw_field("Permit Jurisdiction:", form_data.get('permit_jurisdiction', ''), 4.5*inch, y, 2*inch)
    
    y -= 0.1*inch
    y = draw_field("Application Date:", form_data.get('application_date', ''), 0.75*inch, y, 1.8*inch)
    y += 0.3*inch
    y = draw_field("Permit Number:", form_data.get('permit_number', ''), 4.5*inch, y, 1.8*inch)
    
    y -= 0.1*inch
    y = draw_field("Service Titan Project Number:", form_data.get('service_titan_number', ''), 0.75*inch, y, 4.5*inch)
    
    # Footer
    y -= 0.4*inch
    c.setFont("Helvetica", 9)
    c.drawCentredString(width/2, y, "Woods Comfort Systems | San Marcos, Texas | TACLA16934C")
    
    # Save PDF
    c.save()
    
    # Get PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    # Create filename with date and job info
    builder = form_data.get('builder', 'Unknown').replace(' ', '_')
    today = datetime.now().strftime('%Y%m%d')
    filename = f"Scheduling_Dispatch_{builder}_{today}.pdf"
    
    # Return PDF file
    return send_file(
        io.BytesIO(pdf_data),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/generate-special-order-pdf', methods=['POST'])
def generate_special_order_pdf():
    """Generate PDF from special order form data - Fixed Layout"""
    # Get all form data
    form_data = request.form.to_dict()
    
    # Handle checkboxes
    form_data['request_quote'] = 'request_quote' in request.form
    form_data['request_order'] = 'request_order' in request.form
    form_data['approved'] = 'approved' in request.form
    form_data['retracted'] = 'retracted' in request.form
    
    # Get line items
    line_items = []
    i = 0
    while f'qty_{i}' in request.form or f'description_{i}' in request.form:
        qty = request.form.get(f'qty_{i}', '')
        desc = request.form.get(f'description_{i}', '')
        line_items.append({'qty': qty, 'description': desc})
        i += 1
    
    # Create PDF in memory
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter  # 8.5 x 11 inches
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, height - 0.6*inch, "New Construction Special Order Request Form")
    
    # Top checkboxes - Request Quote / Request Order
    y = height - 0.95*inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(5*inch, y, "Request Quote")
    c.rect(5.95*inch, y - 2, 0.12*inch, 0.12*inch)
    if form_data.get('request_quote'):
        c.drawString(5.97*inch, y, "X")
    
    c.drawString(6.3*inch, y, "Request Order")
    c.rect(7.25*inch, y - 2, 0.12*inch, 0.12*inch)
    if form_data.get('request_order'):
        c.drawString(7.27*inch, y, "X")
    
    # Define fixed positions for labels and data
    left_x = 0.5*inch
    data_start_x = 1.7*inch  # Where data/lines start after labels
    line_end_x = width - 0.5*inch
    row_spacing = 0.28*inch
    
    # Basic Information Section
    y = height - 1.35*inch
    
    # Address
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x, y, "Address:")
    c.line(data_start_x, y - 2, line_end_x, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(data_start_x + 0.05*inch, y, form_data.get('address', '')[:60])
    
    # Builder (NEW FIELD)
    y -= row_spacing
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x, y, "Builder:")
    c.line(data_start_x, y - 2, line_end_x, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(data_start_x + 0.05*inch, y, form_data.get('builder', '')[:60])
    
    # Job Number
    y -= row_spacing
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x, y, "Job Number:")
    c.line(data_start_x, y - 2, line_end_x, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(data_start_x + 0.05*inch, y, form_data.get('job_number', '')[:40])
    
    # Date of Request
    y -= row_spacing
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x, y, "Date of Request:")
    c.line(data_start_x, y - 2, line_end_x, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(data_start_x + 0.05*inch, y, form_data.get('date_request', ''))
    
    # Date Needed By
    y -= row_spacing
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x, y, "Date Needed By:")
    c.line(data_start_x, y - 2, line_end_x, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(data_start_x + 0.05*inch, y, form_data.get('date_needed', ''))
    
    # Requested by
    y -= row_spacing
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x, y, "Requested by:")
    c.line(data_start_x, y - 2, line_end_x, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(data_start_x + 0.05*inch, y, form_data.get('requested_by', '')[:40])
    
    # Approved/Retracted checkboxes
    y -= 0.4*inch
    c.setFont("Helvetica-Bold", 10)
    c.rect(left_x, y - 2, 0.12*inch, 0.12*inch)
    if form_data.get('approved'):
        c.drawString(left_x + 0.02*inch, y, "X")
    c.drawString(left_x + 0.2*inch, y, "Approved")
    
    c.rect(left_x + 1.2*inch, y - 2, 0.12*inch, 0.12*inch)
    if form_data.get('retracted'):
        c.drawString(left_x + 1.22*inch, y, "X")
    c.drawString(left_x + 1.4*inch, y, "Retracted")
    
    # Two column section - Order Details
    y -= 0.45*inch
    col1_x = left_x
    col1_data_x = 1.55*inch
    col1_line_end = 3.7*inch
    
    col2_x = 4*inch
    col2_data_x = 5.4*inch
    col2_line_end = line_end_x
    
    # Left Column
    c.setFont("Helvetica-Bold", 10)
    c.drawString(col1_x, y, "Vendor:")
    c.line(col1_data_x, y - 2, col1_line_end, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(col1_data_x + 0.05*inch, y, form_data.get('vendor', '')[:25])
    
    # Right Column
    c.setFont("Helvetica-Bold", 10)
    c.drawString(col2_x, y, "Tracking number:")
    c.line(col2_data_x, y - 2, col2_line_end, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(col2_data_x + 0.05*inch, y, form_data.get('tracking_number', '')[:20])
    
    y -= row_spacing
    c.setFont("Helvetica-Bold", 10)
    c.drawString(col1_x, y, "Quote number:")
    c.line(col1_data_x, y - 2, col1_line_end, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(col1_data_x + 0.05*inch, y, form_data.get('quote_number', '')[:25])
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(col2_x, y, "Order date:")
    c.line(col2_data_x, y - 2, col2_line_end, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(col2_data_x + 0.05*inch, y, form_data.get('order_date', '')[:20])
    
    y -= row_spacing
    c.setFont("Helvetica-Bold", 10)
    c.drawString(col1_x, y, "Quoted Cost:")
    c.line(col1_data_x, y - 2, col1_line_end, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(col1_data_x + 0.05*inch, y, form_data.get('quoted_cost', '')[:25])
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(col2_x, y, "ETA:")
    c.line(col2_data_x, y - 2, col2_line_end, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(col2_data_x + 0.05*inch, y, form_data.get('eta', '')[:20])
    
    y -= row_spacing
    c.setFont("Helvetica-Bold", 10)
    c.drawString(col1_x, y, "Shipping Cost:")
    c.line(col1_data_x, y - 2, col1_line_end, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(col1_data_x + 0.05*inch, y, form_data.get('shipping_cost', '')[:25])
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(col2_x, y, "PO Number:")
    c.line(col2_data_x, y - 2, col2_line_end, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(col2_data_x + 0.05*inch, y, form_data.get('po_number', '')[:20])
    
    y -= row_spacing
    # Empty left side, Arrival Date on right
    c.setFont("Helvetica-Bold", 10)
    c.drawString(col2_x, y, "Arrival Date:")
    c.line(col2_data_x, y - 2, col2_line_end, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(col2_data_x + 0.05*inch, y, form_data.get('arrival_date', '')[:20])
    
    # Item description table header
    y -= 0.5*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width/2, y, "Item description")
    
    y -= 0.25*inch
    
    # Table header row
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x + 0.05*inch, y, "QTY")
    c.drawString(left_x + 0.7*inch, y, "Description")
    
    y -= 0.15*inch
    
    # Draw table - fixed 15 rows
    table_left = left_x
    qty_col_width = 0.6*inch
    desc_col_width = width - 1*inch - qty_col_width
    row_height = 0.25*inch
    
    c.setFont("Helvetica", 9)
    for i in range(15):
        # Draw row borders
        c.rect(table_left, y - row_height, qty_col_width, row_height)
        c.rect(table_left + qty_col_width, y - row_height, desc_col_width, row_height)
        
        # Fill in data if available
        if i < len(line_items):
            item = line_items[i]
            if item.get('qty'):
                c.drawString(table_left + 0.1*inch, y - row_height + 0.07*inch, str(item['qty'])[:8])
            if item.get('description'):
                c.drawString(table_left + qty_col_width + 0.05*inch, y - row_height + 0.07*inch, str(item['description'])[:85])
        
        y -= row_height
    
    # Footer
    c.setFont("Helvetica", 9)
    c.drawCentredString(width/2, 0.4*inch, "Woods Comfort Systems | San Marcos, Texas | TACLA16934C")
    
    # Save PDF
    c.save()
    
    # Get PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    # Create filename
    job_number = form_data.get('job_number', 'Unknown').replace(' ', '_')
    builder = form_data.get('builder', '').replace(' ', '_')
    today = datetime.now().strftime('%Y%m%d')
    filename = f"Special_Order_{builder}_{job_number}_{today}.pdf".replace('__', '_')
    
    # Return PDF file
    return send_file(
        io.BytesIO(pdf_data),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/generate-change-order-pdf', methods=['POST'])
def generate_change_order_pdf():
    """Generate PDF from change order form data"""
    # Get all form data
    form_data = request.form.to_dict()

    # Handle billable checkbox
    form_data['billable'] = 'billable' in request.form

    # Get equipment being returned
    returned_equipment = []
    for i in range(2):
        model = request.form.get(f'returned_model_{i}', '')
        serial = request.form.get(f'returned_serial_{i}', '')
        if model or serial:
            returned_equipment.append({'model': model, 'serial': serial})

    # Get new equipment sent out
    new_equipment = []
    for i in range(10):
        model = request.form.get(f'new_model_{i}', '')
        serial = request.form.get(f'new_serial_{i}', '')
        if model or serial:
            new_equipment.append({'model': model, 'serial': serial})

    # Create PDF in memory
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Pink background color
    pink_bg = Color(1.0, 0.82, 0.86)  # Soft pink

    # Draw pink background
    c.setFillColor(pink_bg)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(Color(0, 0, 0))  # Reset to black for text

    # Header - Company name
    c.setFont("Helvetica-Bold", 16)
    c.drawString(0.75*inch, height - 0.6*inch, "WOODS COMFORT SYSTEMS")
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(0.75*inch, height - 0.78*inch, "A Lifetime of Comfort")

    # Title
    c.setFont("Helvetica-Bold", 13)
    c.drawString(0.75*inch, height - 1.05*inch, "CHANGES / UPGRADES / ADDITIONS")

    # Helper function to draw labeled field with value on the line
    def draw_field(label, value, x, y_pos, field_width=3*inch):
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, y_pos, label)
        label_w = c.stringWidth(label, "Helvetica-Bold", 10)
        line_start = x + label_w + 4
        line_end = x + label_w + field_width
        c.line(line_start, y_pos - 2, line_end, y_pos - 2)
        if value:
            c.setFont("Helvetica", 10)
            c.drawString(line_start + 3, y_pos, str(value))
        return y_pos - 0.25*inch

    # Helper function to draw multi-line text field (for Work Needed)
    def draw_multiline_field(label, value, x, y_pos, field_width=6.25*inch, line_height=14):
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, y_pos, label)
        label_w = c.stringWidth(label, "Helvetica-Bold", 10)

        # Calculate max chars per line based on field width
        c.setFont("Helvetica", 10)
        avg_char_width = c.stringWidth("a", "Helvetica", 10)
        chars_per_line = int((field_width - label_w - 8) / avg_char_width)

        if value:
            # First line starts after label
            first_line_chars = int((x + label_w + field_width - (x + label_w + 4) - 6) / avg_char_width)
            full_line_chars = int((field_width + label_w - 4) / avg_char_width)

            # Wrap text
            words = value.split()
            lines = []
            current_line = ""
            max_chars = first_line_chars

            for word in words:
                test = current_line + (" " if current_line else "") + word
                if len(test) <= max_chars:
                    current_line = test
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
                    max_chars = full_line_chars
            if current_line:
                lines.append(current_line)

            # Ensure at least 3 lines
            num_lines = max(len(lines), 3)

            # Draw first line after the label
            first_line_start = x + label_w + 4
            c.line(first_line_start, y_pos - 2, x + label_w + field_width, y_pos - 2)
            if lines:
                c.setFont("Helvetica", 10)
                c.drawString(first_line_start + 3, y_pos, lines[0])

            # Draw additional lines
            for i in range(1, num_lines):
                y_pos -= line_height
                c.line(x, y_pos - 2, x + label_w + field_width, y_pos - 2)
                if i < len(lines):
                    c.setFont("Helvetica", 10)
                    c.drawString(x + 3, y_pos, lines[i])
        else:
            # No value - draw 3 blank lines
            c.line(x + label_w + 4, y_pos - 2, x + label_w + field_width, y_pos - 2)
            for i in range(2):
                y_pos -= line_height
                c.line(x, y_pos - 2, x + label_w + field_width, y_pos - 2)

        return y_pos - 0.2*inch

    # Basic Information
    y = height - 1.35*inch

    # Customer Name and Date on same line
    draw_field("Customer Name:", form_data.get('customer_name', ''), 0.75*inch, y, 3.2*inch)
    draw_field("Date:", form_data.get('date', ''), 5.25*inch, y, 1.75*inch)
    y -= 0.25*inch

    # Address (full width)
    y = draw_field("Address:", form_data.get('address', ''), 0.75*inch, y, 6.25*inch)

    # City (full width)
    y = draw_field("City:", form_data.get('city', ''), 0.75*inch, y, 6.25*inch)

    # Job # and Plan # on same line
    draw_field("Job #:", form_data.get('job_number', ''), 0.75*inch, y, 1.75*inch)
    draw_field("Plan #:", form_data.get('plan_number', ''), 4.25*inch, y, 1.75*inch)
    y -= 0.25*inch

    # Called In By / Builder and contact info
    draw_field("Called In By / Builder:", form_data.get('called_in_by', ''), 0.75*inch, y, 2.5*inch)
    draw_field("Phone / Email:", form_data.get('caller_contact', ''), 4.25*inch, y, 2.75*inch)
    y -= 0.25*inch

    # Taken by
    y = draw_field("Taken by:", form_data.get('taken_by', ''), 0.75*inch, y, 6.25*inch)

    # Work Needed - multi-line
    y = draw_multiline_field("Work Needed:", form_data.get('work_needed', ''), 0.75*inch, y)

    # Equipment Being Returned section
    y -= 0.15*inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(0.75*inch, y, "EQUIPMENT BEING RETURNED")
    c.line(0.75*inch, y - 4, 3.2*inch, y - 4)

    y -= 0.22*inch
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.75*inch, y, "Model #:")
    c.drawString(3.5*inch, y, "Serial Number:")

    y -= 0.18*inch
    c.setFont("Helvetica", 9)

    # Draw returned equipment (2 rows)
    for i in range(2):
        c.line(0.75*inch + 0.55*inch, y - 2, 3.2*inch, y - 2)
        c.line(3.5*inch + 0.95*inch, y - 2, 7*inch, y - 2)

        if i < len(returned_equipment):
            item = returned_equipment[i]
            if item['model']:
                c.drawString(0.75*inch + 0.6*inch, y, item['model'])
            if item['serial']:
                c.drawString(3.5*inch + 1.0*inch, y, item['serial'])

        y -= 0.22*inch

    # Reason for return
    y -= 0.05*inch
    y = draw_field("Reason for return:", form_data.get('reason_return', ''), 0.75*inch, y, 5.0*inch)

    # Billable section - clean formatting
    y -= 0.05*inch
    c.setFont("Helvetica-Bold", 10)

    # Draw checkbox
    c.rect(0.75*inch, y - 1, 10, 10)
    if form_data.get('billable', False):
        c.setFont("Helvetica-Bold", 10)
        c.drawString(0.75*inch + 2, y, "X")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.75*inch + 16, y, "Billable?")

    c.drawString(2.25*inch, y, "Amount to Bill:")
    c.setFont("Helvetica", 10)
    amount = form_data.get('amount_bill', '')
    c.line(3.35*inch, y - 2, 4.25*inch, y - 2)
    if amount:
        c.drawString(3.4*inch, y, f"${amount}")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(4.5*inch, y, "PO #:")
    c.setFont("Helvetica", 10)
    c.line(5*inch, y - 2, 7*inch, y - 2)
    if form_data.get('po_number', ''):
        c.drawString(5.05*inch, y, form_data.get('po_number', ''))

    # Date Requested and Date to Be Installed
    y -= 0.35*inch
    draw_field("Date Requested:", form_data.get('date_requested', ''), 0.75*inch, y, 2.0*inch)
    draw_field("Date to Be Installed:", form_data.get('date_installed', ''), 4.25*inch, y, 2.75*inch)
    y -= 0.25*inch

    # New Equipment Sent Out section
    y -= 0.15*inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(0.75*inch, y, "NEW EQUIPMENT SENT OUT")
    c.line(0.75*inch, y - 4, 3.2*inch, y - 4)

    y -= 0.22*inch
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.75*inch, y, "Model #:")
    c.drawString(3.5*inch, y, "Serial Number:")

    y -= 0.18*inch
    c.setFont("Helvetica", 9)

    # Draw new equipment (10 rows)
    for i in range(10):
        c.line(0.75*inch + 0.55*inch, y - 2, 3.2*inch, y - 2)
        c.line(3.5*inch + 0.95*inch, y - 2, 7*inch, y - 2)

        if i < len(new_equipment):
            item = new_equipment[i]
            if item['model']:
                c.drawString(0.75*inch + 0.6*inch, y, item['model'])
            if item['serial']:
                c.drawString(3.5*inch + 1.0*inch, y, item['serial'])

        y -= 0.22*inch

    # Footer
    c.setFont("Helvetica", 8)
    c.drawCentredString(width/2, 0.4*inch, "Woods Comfort Systems | San Marcos, Texas | TACLA16934C")

    # Save PDF
    c.save()

    # Get PDF data
    pdf_data = buffer.getvalue()
    buffer.close()

    # Create filename
    customer = form_data.get('customer_name', 'Unknown').replace(' ', '_')
    today = datetime.now().strftime('%Y%m%d')
    filename = f"Change_Order_{customer}_{today}.pdf"

    # Return PDF file
    return send_file(
        io.BytesIO(pdf_data),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/generate-hvac-bid-pdf', methods=['POST'])
def generate_hvac_bid_pdf():
    """Generate PDF from HVAC bid sheet with all calculations"""
    form_data = request.form.to_dict()
    
    # Get basic info
    num_systems = int(form_data.get('num_systems', 1))
    heat_type = form_data.get('heat_type', '')
    afue = float(form_data.get('afue') or 0)
    
    # Get systems data
    systems = []
    total_tonnage = 0
    equipment_cost = 0
    
    for i in range(1, 7):
        tonnage = float(form_data.get(f'sys{i}_tonnage') or 0)
        cost = float(form_data.get(f'sys{i}_cost') or 0)
        if tonnage > 0:
            # Calculate lineset size
            if tonnage < 3.5:
                lineset_size = "3/8 & 3/4"
                lineset_cost = 225
            elif tonnage < 5:
                lineset_size = "3/8 & 7/8"
                lineset_cost = 260
            else:
                lineset_size = "3/8 & 1-1/8"
                lineset_cost = 325
            
            systems.append({
                'num': i,
                'tonnage': tonnage,
                'cost': cost,
                'zone': form_data.get(f'sys{i}_zone', ''),
                'outdoor': form_data.get(f'sys{i}_outdoor', ''),
                'indoor': form_data.get(f'sys{i}_indoor', ''),
                'seer': form_data.get(f'sys{i}_seer', ''),
                'lineset_size': lineset_size,
                'lineset_cost': lineset_cost
            })
            total_tonnage += tonnage
            equipment_cost += cost
    
    # Calculate lineset total
    lineset_total = sum(s['lineset_cost'] for s in systems)
    
    # Material calculations
    two_story_adder = int(form_data.get('two_story_adder') or 0)
    supply_outlets = int(form_data.get('supply_outlets') or 0)
    returns = int(form_data.get('returns') or 0)
    jumper_returns = int(form_data.get('jumper_returns') or 0)
    panasonic_fans = int(form_data.get('panasonic_fans') or 0)
    long_range_vent = int(form_data.get('long_range_vent') or 0)
    long_dryer_vent = int(form_data.get('long_dryer_vent') or 0)
    ecobee_pro = int(form_data.get('ecobee_pro') or 0)
    fresh_air = int(form_data.get('fresh_air') or 0)
    makeup_air = int(form_data.get('makeup_air') or 0)
    misc_material = float(form_data.get('misc_material') or 0)
    
    # Auto-calculated materials
    concentric_qty = num_systems if afue == 0.9 else 0
    lp_kit_qty = num_systems if heat_type == "AC & LP Gas" else 0
    drain_line_qty = num_systems + (num_systems * 0.2 if concentric_qty >= 1 else 0)
    tape_qty = num_systems
    flue_qty = num_systems if afue == 0.8 else 0
    low_voltage_qty = num_systems
    plenums_qty = round(supply_outlets / 3 / 2 + 2 * num_systems, 0)
    media_filter_qty = num_systems
    
    # Material costs
    material_costs = {
        'concentric': concentric_qty * 72.24,
        'lp_kit': lp_kit_qty * 50,
        'drain_line': drain_line_qty * 77.76,
        'tape': tape_qty * 75.93,
        'flue': flue_qty * 101.08,
        'low_voltage': low_voltage_qty * 56,
        'plenums': plenums_qty * 37.34,
        'two_story': two_story_adder * 100,
        'supply_outlets': supply_outlets * 90,
        'returns': returns * 150,
        'jumper_returns': jumper_returns * 90,
        'panasonic_fans': panasonic_fans * 122,
        'long_range_vent': long_range_vent * 70,
        'long_dryer_vent': long_dryer_vent * 70,
        'media_filter': media_filter_qty * 90,
        'ecobee_pro': ecobee_pro * 220,
        'fresh_air': fresh_air * 425,
        'makeup_air': makeup_air * 265,
        'misc': misc_material
    }
    
    material_subtotal = sum(material_costs.values()) + lineset_total
    
    # Labor calculations
    shop_labor = 22 * (num_systems * 3)
    
    # Rough labor (complex calculation based on systems)
    rough_labor = 0
    for system in systems:
        system_rough = 700
        if two_story_adder > 0:
            system_rough += 200
        if system['tonnage'] >= 4:
            system_rough += 100
        rough_labor += system_rough
    
    final_labor_hrs = float(form_data.get('final_labor_hrs') or 0)
    final_labor = 25 * final_labor_hrs
    
    check_labor = 30 * (num_systems * 5)
    balance_labor = 30 * (num_systems * 3)
    trim_labor = 120 * num_systems
    travel_cost = float(form_data.get('travel_cost') or 0)
    misc_labor = float(form_data.get('misc_labor') or 0)
    
    labor_total = shop_labor + rough_labor + final_labor + check_labor + balance_labor + trim_labor + travel_cost + misc_labor
    
    # Job costing
    sales_tax = (equipment_cost + material_subtotal) * 0.0825
    misc_cost = float(form_data.get('misc_cost') or 0)
    job_cost = equipment_cost + material_subtotal + sales_tax + labor_total + misc_cost
    
    # Burdens & Margin
    material_burden = material_subtotal * 0.02
    labor_burden = labor_total * 0.3
    punch = job_cost * 0.02
    
    margin_percent = float(form_data.get('margin_percent') or 0.35)
    margin_dollar = (job_cost + material_burden + labor_burden + punch) / (1 - margin_percent) - (job_cost + material_burden + labor_burden + punch)
    
    price_with_burdens = job_cost + material_burden + labor_burden + punch + margin_dollar
    warranty = price_with_burdens * 0.02
    selling_price = price_with_burdens + warranty
    cost_per_ton = selling_price / total_tonnage if total_tonnage > 0 else 0
    
    # Create PDF
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, height - 0.6*inch, "HVAC BID SHEET")
    
    # Job info section
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75*inch, height - 1*inch, "JOB & PROPOSAL INFORMATION")
    
    c.setFont("Helvetica", 10)
    y = height - 1.25*inch
    c.drawString(0.75*inch, y, f"Builder: {form_data.get('builder', '')}")
    c.drawString(4*inch, y, f"Job Name: {form_data.get('job_name', '')}")
    
    y -= 0.2*inch
    c.drawString(0.75*inch, y, f"Address: {form_data.get('job_address', '')}")
    c.drawString(4*inch, y, f"Sales: {form_data.get('sales', '')}")
    
    y -= 0.2*inch
    c.drawString(0.75*inch, y, f"City: {form_data.get('city', '')}")
    c.drawString(2.5*inch, y, f"ZIP: {form_data.get('zip', '')}")
    c.drawString(4*inch, y, f"Design: {form_data.get('design', '')}")
    
    y -= 0.2*inch
    c.drawString(0.75*inch, y, f"Date: {form_data.get('date', '')}")
    
    y -= 0.3*inch
    c.drawString(0.75*inch, y, f"No. of Systems: {num_systems}")
    c.drawString(2*inch, y, f"Brand: {form_data.get('brand', '')}")
    c.drawString(3.5*inch, y, f"Heat Type: {heat_type}")
    if afue > 0:
        c.drawString(5.5*inch, y, f"AFUE: {afue}")
    
    # System Configuration
    y -= 0.4*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75*inch, y, "SYSTEM CONFIGURATION")
    
    y -= 0.25*inch
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.75*inch, y, "System")
    c.drawString(1.4*inch, y, "Tons")
    c.drawString(1.9*inch, y, "Equip Cost")
    c.drawString(2.7*inch, y, "Zone")
    c.drawString(3.8*inch, y, "Outdoor Model")
    c.drawString(4.9*inch, y, "Indoor Model")
    c.drawString(6*inch, y, "SEER")
    c.drawString(6.5*inch, y, "Lineset")
    
    y -= 0.15*inch
    c.setFont("Helvetica", 8)
    
    for system in systems:
        c.drawString(0.75*inch, y, f"System {system['num']}:")
        c.drawString(1.4*inch, y, str(system['tonnage']))
        c.drawString(1.9*inch, y, f"${system['cost']:,.0f}")
        c.drawString(2.7*inch, y, system['zone'][:12])
        c.drawString(3.8*inch, y, system['outdoor'][:10])
        c.drawString(4.9*inch, y, system['indoor'][:10])
        c.drawString(6*inch, y, str(system['seer']))
        c.drawString(6.5*inch, y, system['lineset_size'])
        y -= 0.18*inch
    
    y -= 0.1*inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.75*inch, y, "Equipment Subtotal:")
    c.drawString(1.9*inch, y, f"${equipment_cost:,.2f}")
    c.drawString(6*inch, y, "Lineset Subtotal:")
    c.drawString(6.8*inch, y, f"${lineset_total:,.2f}")
    
    # Pricing Summary
    y -= 0.4*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(0.75*inch, y, "JOB COSTING & PRICING")
    
    y -= 0.25*inch
    c.setFont("Helvetica", 10)
    c.drawString(0.75*inch, y, f"Equipment: ${equipment_cost:,.2f}")
    y -= 0.18*inch
    c.drawString(0.75*inch, y, f"Material: ${material_subtotal:,.2f}")
    y -= 0.18*inch
    c.drawString(0.75*inch, y, f"Sales Tax (8.25%): ${sales_tax:,.2f}")
    y -= 0.18*inch
    c.drawString(0.75*inch, y, f"Labor: ${labor_total:,.2f}")
    y -= 0.18*inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.75*inch, y, f"JOB COST: ${job_cost:,.2f}")
    
    y -= 0.3*inch
    c.setFont("Helvetica", 10)
    c.drawString(0.75*inch, y, f"Material Burden (2%): ${material_burden:,.2f}")
    y -= 0.18*inch
    c.drawString(0.75*inch, y, f"Labor Burden (30%): ${labor_burden:,.2f}")
    y -= 0.18*inch
    c.drawString(0.75*inch, y, f"Punch (2%): ${punch:,.2f}")
    y -= 0.18*inch
    c.drawString(0.75*inch, y, f"Margin ({margin_percent*100:.0f}%): ${margin_dollar:,.2f}")
    
    y -= 0.3*inch
    c.setFont("Helvetica-Bold", 11)
    c.drawString(0.75*inch, y, f"Price w/Burdens: ${price_with_burdens:,.2f}")
    y -= 0.2*inch
    c.drawString(0.75*inch, y, f"Warranty (2%): ${warranty:,.2f}")
    
    y -= 0.3*inch
    c.setFont("Helvetica-Bold", 14)
    c.drawString(0.75*inch, y, f"SELLING PRICE: ${selling_price:,.2f}")
    y -= 0.25*inch
    c.setFont("Helvetica", 10)
    c.drawString(0.75*inch, y, f"Cost per Ton: ${cost_per_ton:,.2f}")
    
    # Footer
    c.setFont("Helvetica", 9)
    c.drawCentredString(width/2, 0.5*inch, "Woods Comfort Systems | San Marcos, Texas | TACLA16934C")
    
    # Save PDF
    c.save()
    
    pdf_data = buffer.getvalue()
    buffer.close()
    
    # Create filename
    job_name = form_data.get('job_name', 'Bid').replace(' ', '_')
    today = datetime.now().strftime('%Y%m%d')
    filename = f"HVAC_Bid_{job_name}_{today}.pdf"
    
    return send_file(
        io.BytesIO(pdf_data),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/generate-design-walk-pdf', methods=['POST'])
def generate_design_walk_pdf():
    """Generate PDF from Design Walk Sheet - Updated with redline sections"""
    from reportlab.lib.pagesizes import legal
    from reportlab.lib.colors import HexColor, white, black

    form_data = request.form.to_dict()

    buffer = io.BytesIO()
    page_w, page_h = legal
    c = canvas.Canvas(buffer, pagesize=legal)
    margin = 36
    content_w = page_w - 2 * margin
    L = margin + 4
    R = margin + content_w
    row_h = 14
    row_gap = 3
    sec_gap = 6

    HEADER_BG = HexColor("#2C3E50")
    LABEL_COLOR = HexColor("#2C3E50")

    def sec_hdr(title, y_pos):
        h = 15
        c.setFillColor(HEADER_BG)
        c.roundRect(margin, y_pos - h, content_w, h, 3, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(margin + 6, y_pos - h + 4, title.upper())
        return y_pos - h - sec_gap

    def lbl(x, y_pos, text, bold=False, sz=8):
        c.setFillColor(LABEL_COLOR)
        c.setFont("Helvetica-Bold" if bold else "Helvetica", sz)
        c.drawString(x, y_pos, text)

    def val(x, y_pos, text, sz=8):
        c.setFillColor(black)
        c.setFont("Helvetica", sz)
        c.drawString(x, y_pos, str(text))

    def field_line(x, y_pos, w):
        c.setStrokeColor(HexColor("#BDC3C7"))
        c.setLineWidth(0.5)
        c.line(x, y_pos - 2, x + w, y_pos - 2)

    def row_field(x, y_pos, label_text, value, label_w=None, field_w=150):
        lbl(x, y_pos, label_text, bold=True, sz=7.5)
        if label_w is None:
            label_w = len(label_text) * 4.5 + 4
        val(x + label_w, y_pos, value, sz=8)
        field_line(x + label_w, y_pos, field_w)

    def yn_field(x, y_pos, label_text, value):
        lbl(x, y_pos, label_text, bold=True, sz=7.5)
        lw = len(label_text) * 4.2 + 6
        marker = "[X]" if value == "Yes" else "[ ]"
        marker_no = "[X]" if value == "No" else "[ ]"
        val(x + lw, y_pos, f"Yes {marker}  No {marker_no}", sz=7)
        return lw + 80

    # TITLE
    y = page_h - margin
    c.setFillColor(HEADER_BG)
    c.roundRect(margin, y - 24, content_w, 24, 4, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(page_w / 2, y - 17, "DESIGN PLAN WALK SHEET")
    y -= 28
    c.setFillColor(HexColor("#7F8C8D"))
    c.setFont("Helvetica", 6.5)
    c.drawCentredString(page_w / 2, y, "Woods Comfort Systems | TACLA16934C")
    y -= 10

    # JOB INFORMATION
    y = sec_hdr("Job Information", y)
    r = y - row_h
    row_field(L, r+3, "Date of Rough In:", form_data.get('rough_in_date',''), label_w=90, field_w=130)
    y = r - row_gap
    r = y - row_h
    row_field(L, r+3, "Builder:", form_data.get('builder',''), label_w=42, field_w=200)
    row_field(L+260, r+3, "Address:", form_data.get('address',''), label_w=42, field_w=R-L-306)
    y = r - row_gap
    r = y - row_h
    yn_field(L, r+3, "Permit:", form_data.get('permit',''))
    row_field(L+110, r+3, "City:", form_data.get('city',''), label_w=28, field_w=175)
    row_field(L+330, r+3, "Zip:", form_data.get('zip',''), label_w=22, field_w=80)
    y = r - sec_gap

    # FRESH AIR / FLUE VENT
    y = sec_hdr("Fresh Air / Flue Vent", y)
    r = y - row_h
    yn_field(L, r+3, "Fresh Air:", form_data.get('fresh_air',''))
    yn_field(L+150, r+3, "Marked on Plan:", form_data.get('fresh_air_marked',''))
    y = r - row_gap
    r = y - row_h
    yn_field(L, r+3, "Flue Vent:", form_data.get('flue_vent',''))
    lbl(L+120, r+3, "Type:", bold=True, sz=7.5)
    val(L+142, r+3, form_data.get('flue_type',''), sz=8)
    row_field(L+190, r+3, "FT Needed:", form_data.get('flue_ft',''), label_w=52, field_w=45)
    row_field(L+296, r+3, "90's:", form_data.get('flue_90s',''), label_w=26, field_w=30)
    row_field(L+362, r+3, "45's:", form_data.get('flue_45s',''), label_w=26, field_w=30)
    y = r - sec_gap

    # TRUSSES
    y = sec_hdr("Trusses", y)
    r = y - row_h
    lbl(L, r+3, "Truss Type:", bold=True, sz=7.5)
    val(L+58, r+3, form_data.get('truss_type',''), sz=8)
    row_field(L+130, r+3, "Size:", form_data.get('truss_size',''), label_w=28, field_w=90)
    y = r - sec_gap

    # STOVE VENTING
    y = sec_hdr("Stove Venting", y)
    r = y - row_h
    yn_field(L, r+3, "Stove Vent:", form_data.get('stove_vent',''))
    lbl(L+130, r+3, "Term:", bold=True, sz=7.5)
    val(L+156, r+3, form_data.get('stove_term',''), sz=8)
    row_field(L+230, r+3, "Size:", form_data.get('stove_size',''), label_w=28, field_w=60)
    y = r - row_gap
    r = y - row_h
    row_field(L, r+3, "Stove Vent Pipe FT:", form_data.get('stove_pipe_ft',''), label_w=96, field_w=40)
    row_field(L+150, r+3, "90's:", form_data.get('stove_90s',''), label_w=26, field_w=30)
    yn_field(L+220, r+3, "Wall Stack:", form_data.get('wall_stack',''))
    y = r - sec_gap

    # DRYER VENTING
    y = sec_hdr("Dryer Venting", y)
    r = y - row_h
    yn_field(L, r+3, "Dryer Vent:", form_data.get('dryer_vent',''))
    lbl(L+130, r+3, "Term:", bold=True, sz=7.5)
    val(L+156, r+3, form_data.get('dryer_term',''), sz=8)
    row_field(L+230, r+3, "Feet Needed:", form_data.get('dryer_ft',''), label_w=62, field_w=40)
    row_field(L+346, r+3, "90's:", form_data.get('dryer_90s',''), label_w=26, field_w=30)
    y = r - row_gap
    r = y - row_h
    yn_field(L, r+3, "Dryer Box:", form_data.get('dryer_box',''))
    lbl(L+130, r+3, "Box Size:", bold=True, sz=7.5)
    val(L+170, r+3, form_data.get('dryer_box_size',''), sz=8)
    y = r - sec_gap

    # EXHAUST FANS
    y = sec_hdr("Exhaust Fans", y)
    for i in range(1, 4):
        fan_val = form_data.get(f'fan{i}', '')
        model = form_data.get(f'fan{i}_model', '')
        qty = form_data.get(f'fan{i}_qty', '')
        vs = form_data.get(f'fan{i}_vent_size', '')
        vt = form_data.get(f'fan{i}_vent_to', '')
        r = y - row_h
        lbl(L, r+3, f"Fan {i}:", bold=True, sz=7.5)
        yn_val = "[X]" if fan_val == "Yes" else "[ ]"
        yn_n = "[X]" if fan_val == "No" else "[ ]"
        val(L+28, r+3, f"Y{yn_val} N{yn_n}", sz=6.5)
        row_field(L+80, r+3, "Model:", model, label_w=32, field_w=100)
        row_field(L+222, r+3, "#:", qty, label_w=12, field_w=20)
        row_field(L+264, r+3, "Vent Size:", vs, label_w=48, field_w=28)
        lbl(L+350, r+3, "To:", bold=True, sz=7.5)
        val(L+366, r+3, vt, sz=7.5)
        y = r - row_gap
    y -= 3

    # DRAIN LINES
    y = sec_hdr("Drain Lines", y)
    r = y - row_h
    yn_field(L, r+3, "Primary Drain Marked:", form_data.get('primary_drain',''))
    yn_field(L+230, r+3, "Secondary Drain Marked:", form_data.get('secondary_drain',''))
    y = r - sec_gap

    # THERMOSTATS
    y = sec_hdr("Thermostats", y)
    r = y - row_h
    yn_field(L, r+3, "Tstat Location Marked:", form_data.get('tstat_marked',''))
    row_field(L+230, r+3, "# Needed:", form_data.get('tstat_qty',''), label_w=48, field_w=30)
    row_field(L+320, r+3, "Model:", form_data.get('tstat_model',''), label_w=34, field_w=R-L-358)
    y = r - sec_gap

    # CHECKLIST ITEMS
    y = sec_hdr("Checklist Items", y)
    r = y - row_h
    yn_field(L, r+3, "Condenser Marked:", form_data.get('condenser_marked',''))
    yn_field(L+240, r+3, "PO / Contracts Included:", form_data.get('po_included',''))
    y = r - row_gap
    r = y - row_h
    yn_field(L, r+3, "All Returns Marked on Plan:", form_data.get('returns_marked',''))
    row_field(L+270, r+3, "IAQ Extras:", form_data.get('iaq_extras',''), label_w=54, field_w=R-L-328)
    y = r - sec_gap

    # EQUIPMENT
    y = sec_hdr("Equipment", y)
    r = y - 10
    c.setFillColor(HexColor("#7F8C8D"))
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(L, r+1, "#")
    c.drawString(L+14, r+1, "A/H or Furnace Model")
    c.drawString(L+210, r+1, "Heat Strip / Coil Model")
    c.drawString(L+400, r+1, "Condenser Model")
    y = r - 2
    for i in range(1, 4):
        ah = form_data.get(f'ah_{i}', '')
        coil = form_data.get(f'coil_{i}', '')
        cond = form_data.get(f'cond_{i}', '')
        r = y - row_h
        lbl(L, r+3, f"{i}.", bold=True, sz=7.5)
        val(L+14, r+3, ah, sz=8); field_line(L+14, r+3, 188)
        val(L+210, r+3, coil, sz=8); field_line(L+210, r+3, 182)
        val(L+400, r+3, cond, sz=8); field_line(L+400, r+3, R-L-404)
        y = r - row_gap
    y -= 3

    # MEDIA FILTERS
    y = sec_hdr("Media Filters", y)
    r = y - 10
    c.setFillColor(HexColor("#7F8C8D"))
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(L, r+1, "#")
    c.drawString(L+14, r+1, "Flex Duct")
    c.drawString(L+100, r+1, "Media Filter / Size")
    c.drawString(L+300, r+1, "Type / Notes")
    y = r - 2
    for i in range(1, 4):
        flex = form_data.get(f'filt{i}_flex', '')
        size = form_data.get(f'filt{i}_size', '')
        notes = form_data.get(f'filt{i}_notes', '')
        r = y - row_h
        lbl(L, r+3, f"{i}.", bold=True, sz=7.5)
        val(L+14, r+3, flex, sz=8)
        val(L+100, r+3, size, sz=8); field_line(L+100, r+3, 192)
        val(L+300, r+3, notes, sz=8); field_line(L+300, r+3, R-L-304)
        y = r - row_gap
    y -= 3

    # DUCTWORK / SIZING
    y = sec_hdr("Ductwork / Sizing", y)
    r = y - row_h
    row_field(L, r+3, "Trunk Line Sizes:", form_data.get('trunk_sizes',''), label_w=88, field_w=170)
    row_field(L+276, r+3, "Upflow Plenum Size:", form_data.get('plenum_size',''), label_w=96, field_w=R-L-376)
    y = r - row_gap
    r = y - row_h
    row_field(L, r+3, "Long Box Sizes:", form_data.get('long_box',''), label_w=78, field_w=R-L-82)
    y = r - row_gap
    r = y - 10
    c.setFillColor(HexColor("#E74C3C"))
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(L, r+1, 'Ducts 8" or Bigger between Floor Trusses Must be Side Tap')
    c.setFillColor(LABEL_COLOR)
    c.setFont("Helvetica", 6.5)
    c.drawString(L, r-8, 'Max Duct size for trusses:   16"-8" Duct     18"-10" Duct     24"-12" Duct')
    y = r - 18

    # NOTES / SPECIAL ORDER ITEMS
    notes_text = form_data.get('notes', '')
    y = sec_hdr("Notes / Special Order Items", y)
    if notes_text:
        c.setFont("Helvetica", 8)
        c.setFillColor(black)
        words = notes_text.split()
        line = ''
        for word in words:
            if c.stringWidth(line + ' ' + word, "Helvetica", 8) < (content_w - 20):
                line += ' ' + word if line else word
            else:
                r = y - row_h
                c.drawString(L, r+3, line)
                field_line(L, r+3, R-L-8)
                y = r - 2
                line = word
        if line:
            r = y - row_h
            c.drawString(L, r+3, line)
            field_line(L, r+3, R-L-8)
            y = r - 2
    else:
        for _ in range(4):
            r = y - row_h
            field_line(L, r+3, R-L-8)
            y = r - 2

    # Footer
    c.setFillColor(HexColor("#95A5A6"))
    c.setFont("Helvetica", 6)
    c.drawCentredString(page_w/2, margin-10, "Woods Comfort Systems | San Marcos, Texas | TACLA16934C")
    c.save()

    pdf_data = buffer.getvalue()
    buffer.close()
    builder = form_data.get('builder', 'Unknown').replace(' ', '_')
    today = datetime.now().strftime('%Y%m%d')
    filename = f"Design_Walk_{builder}_{today}.pdf"
    return send_file(io.BytesIO(pdf_data), mimetype='application/pdf', as_attachment=True, download_name=filename)

@app.route('/generate-bid-proposal-pdf', methods=['POST'])
def generate_bid_proposal_pdf():
    """Generate professional bid proposal PDF in Woods format"""
    import json
    from reportlab.lib.colors import HexColor, black, red, green
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import Paragraph
    
    # Get form data
    form_data = json.loads(request.form.get('data', '{}'))
    
    buffer = io.BytesIO()
    width, height = letter
    c = canvas.Canvas(buffer, pagesize=letter)
    
    # Colors
    woods_green = HexColor('#2E7D32')
    woods_gray = HexColor('#424242')
    
    y = height - 0.5*inch
    
    # === HEADER ===
    # Logo area (left side)
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(woods_green)
    c.drawString(0.75*inch, y, "WOODS")
    c.setFont("Helvetica", 10)
    c.drawString(0.75*inch, y - 15, "COMFORT SYSTEMS")
    c.setFont("Helvetica", 7)
    c.setFillColor(woods_gray)
    c.drawString(0.75*inch, y - 27, "A Lifetime of Experience")
    
    # Company info (right side)
    c.setFont("Helvetica", 8)
    c.setFillColor(black)
    right_x = width - 0.75*inch
    c.drawRightString(right_x, y, "1902 DUTTON DR.")
    c.drawRightString(right_x, y - 10, "SAN MARCOS, TEXAS 78667")
    c.drawRightString(right_x, y - 20, "PHONE: 512-392-6907")
    c.drawRightString(right_x, y - 30, "FAX: 512-392-6916")
    c.drawRightString(right_x, y - 40, "LICENSE: TACLA16934C")
    
    y -= 0.9*inch
    
    # Date and Builder line
    c.setFont("Helvetica-Bold", 10)
    bid_date = form_data.get('bid_date', '')
    if bid_date:
        from datetime import datetime as dt
        try:
            date_obj = dt.strptime(bid_date, '%Y-%m-%d')
            bid_date = date_obj.strftime('%B %d, %Y')
        except:
            pass
    c.drawString(0.75*inch, y, bid_date)
    
    builder = form_data.get('builder', '')
    project = form_data.get('project_name', '')
    address = form_data.get('address', '')
    
    # Builder on left, address on right
    c.drawString(0.75*inch, y - 15, builder.upper() if builder else '')
    c.drawRightString(right_x, y - 15, f"{project} ({address})" if project else address)
    
    y -= 0.6*inch
    
    # Intro paragraph
    c.setFont("Helvetica", 9)
    intro_text = "We are pleased to submit an estimate for heating & air conditioning as per our plans & specifications. System design as per construction data furnished by owner. Design temperature differences: 40 degree on heating, 25 degree on cooling."
    
    # Word wrap the intro
    words = intro_text.split()
    lines = []
    current_line = []
    for word in words:
        current_line.append(word)
        if c.stringWidth(' '.join(current_line), "Helvetica", 9) > (width - 1.5*inch):
            current_line.pop()
            lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    
    for line in lines:
        c.drawString(0.75*inch, y, line)
        y -= 12
    
    y -= 0.15*inch
    
    # Insulation note (right aligned, italic)
    c.setFont("Helvetica-Oblique", 9)
    insulation = form_data.get('insulation_type', 'Spray Foam Insulation @ Roof Deck')
    c.drawRightString(right_x, y, f"Tonnages Based on {insulation}")
    
    y -= 0.35*inch
    
    # === EQUIPMENT OPTIONS ===
    options = form_data.get('options', [])
    refrigerant = form_data.get('refrigerant', 'R454B')
    
    for i, opt in enumerate(options):
        if not opt.get('name') and not opt.get('price'):
            continue
            
        # Option header with green text for Lennox
        c.setFont("Helvetica-Bold", 10)
        opt_name = opt.get('name', f'Option {i+1}')
        
        # Check if we need a section header (MAIN HOUSE, GARAGE, etc.)
        # Draw option name
        c.setFillColor(woods_green)
        c.drawString(0.75*inch, y, f"Lennox ({refrigerant}) ")
        lennox_width = c.stringWidth(f"Lennox ({refrigerant}) ", "Helvetica-Bold", 10)
        c.setFillColor(black)
        c.drawString(0.75*inch + lennox_width, y, opt_name)
        
        # Price on right
        price = opt.get('price', 0)
        try:
            price_formatted = f"Price: ${int(price):,}"
        except:
            price_formatted = f"Price: ${price}"
        c.drawRightString(right_x, y, price_formatted)
        
        y -= 0.2*inch
        
        # Equipment models
        c.setFont("Helvetica", 9)
        condenser = opt.get('condenser', '')
        airhandler = opt.get('airhandler', '')
        
        if condenser:
            c.drawString(1*inch, y, f"Heat Pump: {condenser}")
        if airhandler:
            c.drawString(3.5*inch, y, f"Air-Handler: {airhandler}")
        
        y -= 0.18*inch
        
        # Zones
        zones = opt.get('zones', [])
        for zone in zones:
            zone_name = zone.get('name', '')
            tonnage = zone.get('tonnage', '')
            seer = zone.get('seer', '')
            if zone_name:
                c.drawString(1.25*inch, y, f"- {zone_name}")
                if tonnage:
                    c.setFillColor(woods_green)
                    c.drawString(4*inch, y, f"{tonnage} TONS")
                    if seer:
                        c.drawString(5*inch, y, f"({seer} SEER2)")
                    c.setFillColor(black)
                y -= 0.15*inch
        
        y -= 0.15*inch
        
        # Check if we need a new page
        if y < 3*inch:
            c.showPage()
            y = height - 0.75*inch
    
    y -= 0.2*inch
    
    # === BID INCLUDES ===
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.75*inch, y, "BID INCLUDES:")
    y -= 0.2*inch
    
    includes = form_data.get('includes', [])
    c.setFont("Helvetica", 9)
    
    for i, item in enumerate(includes, 1):
        # Word wrap long items
        text = f"{i}. {item}"
        if c.stringWidth(text, "Helvetica", 9) > (width - 1.5*inch):
            # Split at reasonable point
            c.drawString(0.85*inch, y, f"{i}. {item[:60]}...")
        else:
            c.drawString(0.85*inch, y, text)
        y -= 0.15*inch
        
        if y < 2.5*inch:
            c.showPage()
            y = height - 0.75*inch
    
    y -= 0.25*inch
    
    # === OPTIONS (Add-ons) ===
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.75*inch, y, "OPTIONS:")
    y -= 0.2*inch
    
    # Standard add-on options
    addon_items = [
        ('2-Zone Damper System', 1865),
        ('Ultra-Aire 98H Dehumidifier (98 Pints/Day)', 3957),
        ('Ultra-Aire 120H Dehumidifier (120 Pints/Day)', 4263),
        ('Upgrade to 150 CFM Panasonic WhisperCeiling DC', 135),
    ]
    
    c.setFont("Helvetica", 9)
    for i, (item, price) in enumerate(addon_items, 1):
        c.drawString(0.85*inch, y, f"{i}. {item}")
        c.drawRightString(right_x, y, f"add: ${price:,} ea.")
        y -= 0.15*inch
    
    y -= 0.2*inch
    
    # IECC note
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(width/2, y, "Bid Includes Necessary Labor and/or Materials to Meet the Requirements of 2024 IECC")
    y -= 0.12*inch
    c.setFillColor(red)
    c.drawCentredString(width/2, y, "Does NOT Include Cost of Independent Third-Party Inspector")
    c.setFillColor(black)
    
    y -= 0.35*inch
    
    # === WORK BY OTHERS ===
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.75*inch, y, "WORK BY OTHERS/EXTRAS:")
    y -= 0.12*inch
    
    c.setFont("Helvetica", 7)
    work_by_others = "Necessary Electrical Wiring Including Disconnect Switches, Necessary Floor Drain or Sink Connection for Air Conditioning Condensate, Bath Fan Connections (If Fans Not Provided By Woods Comfort Systems), Necessary OSHA Approved Temp Electrical Pole (Woods Comfort Systems Provided Generator Is Extra), Extra Start-Ups Due to Meters are Bill Extra, Propane Conversion Kits are Bill Extra If Not Included Above, 3rd Party Inspection Requirements That Exceed Code are Bill Extra, Sealing of Platforms & Register Boots to Sheetrock By Others, Cabinet Modification & Cutting For Range Venting, Attic Access, Lights, Catwalks, & Platforms As Required, Fire Blocking At Top Of Duct Chases, House Must Be Decked & Dried-In (With Tar Paper) Prior To Rough-In, & Carpentry Work As Required For Duct Access."
    
    # Simple word wrap for small text
    max_width = width - 1.5*inch
    words = work_by_others.split()
    current_line = []
    for word in words:
        current_line.append(word)
        if c.stringWidth(' '.join(current_line), "Helvetica", 7) > max_width:
            current_line.pop()
            c.drawString(0.75*inch, y, ' '.join(current_line))
            y -= 9
            current_line = [word]
    if current_line:
        c.drawString(0.75*inch, y, ' '.join(current_line))
        y -= 9
    
    y -= 0.15*inch
    
    # === PAYABLE ===
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.75*inch, y, "PAYABLE:")
    y -= 0.12*inch
    
    c.setFont("Helvetica", 7)
    payable = "60/40%: ROUGH-IN / TRIM-OUT: As per our billing schedule & credit terms. Payment due within 10 days of Rough-In & Trim-Out installation. The above proposal is based on current cost & is effective for thirty (30) days. Work performed after thirty (30) days shall be subject to price escalations based solely on labor & material variances."
    
    words = payable.split()
    current_line = []
    for word in words:
        current_line.append(word)
        if c.stringWidth(' '.join(current_line), "Helvetica", 7) > max_width:
            current_line.pop()
            c.drawString(0.75*inch, y, ' '.join(current_line))
            y -= 9
            current_line = [word]
    if current_line:
        c.drawString(0.75*inch, y, ' '.join(current_line))
        y -= 9
    
    y -= 0.2*inch
    
    # === ACCEPTANCE ===
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.75*inch, y, "PURCHASER'S ACCEPTANCE OF ESTIMATE")
    y -= 0.12*inch
    
    c.setFont("Helvetica", 7)
    acceptance = "The foregoing terms, specifications, & conditions are satisfactory & the same are hereby accepted & agreed upon. You are hereby authorized to execute same. Purchaser further agrees that equity in this property is security for this contract, that property will not be sold or title transferred until full payment of this contract has been made. This agreement shall become binding only upon written acceptance hereof, by the principal or authorized officer of the contractor, or upon commencing performance of the work."
    
    words = acceptance.split()
    current_line = []
    for word in words:
        current_line.append(word)
        if c.stringWidth(' '.join(current_line), "Helvetica", 7) > max_width:
            current_line.pop()
            c.drawString(0.75*inch, y, ' '.join(current_line))
            y -= 9
            current_line = [word]
    if current_line:
        c.drawString(0.75*inch, y, ' '.join(current_line))
        y -= 9
    
    y -= 0.4*inch
    
    # Signature lines
    c.setFont("Helvetica", 9)
    c.line(0.75*inch, y, 3*inch, y)
    c.drawString(0.75*inch, y - 12, "Purchaser")
    
    # Woods signature on right
    c.line(5*inch, y, 7.5*inch, y)
    c.drawString(5*inch, y - 12, "Ryan Sekula")
    c.drawRightString(right_x, y - 12, "Woods Comfort Systems")
    
    y -= 0.5*inch
    c.line(0.75*inch, y, 3*inch, y)
    c.drawString(0.75*inch, y - 12, "Date")
    
    # Save PDF
    c.save()
    
    pdf_data = buffer.getvalue()
    buffer.close()
    
    # Create filename
    builder_name = form_data.get('builder', 'Unknown').replace(' ', '_')
    project_name = form_data.get('project_name', '').replace(' ', '_')
    today = datetime.now().strftime('%Y%m%d')
    filename = f"{project_name}_{builder_name}_HVAC_{today}.pdf".replace('__', '_')
    
    return send_file(
        io.BytesIO(pdf_data),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/generate-additional-work-pdf', methods=['POST'])
def generate_additional_work_pdf():
    """Generate PDF from Additional Work / Change Order form - Triplicate Copies"""
    form_data = request.form.to_dict()

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter  # 8.5 x 11 inches

    # Triplicate copy definitions: (label, fill_color_rgb, text_color_rgb)
    copies = [
        ("WHITE COPY: CHANGE ORDER",    (0.92, 0.92, 0.95),   (0.12, 0.23, 0.37)),   # light gray fill, dark text
        ("YELLOW COPY: TAKE OFF / COSTING", (1.0, 0.95, 0.7), (0.45, 0.35, 0.0)),    # yellow fill, dark yellow-brown text
        ("PINK COPY: SUB PAY",           (1.0, 0.82, 0.86),   (0.55, 0.1, 0.2)),     # pink fill, dark pink text
    ]

    for copy_idx, (copy_label, fill_rgb, text_rgb) in enumerate(copies):
        if copy_idx > 0:
            c.showPage()

        # ===== FULL-WIDTH COLORED RIBBON HEADER =====
        # Ribbon covers entire top of page down to the header line
        ribbon_bottom = height - 1.15*inch
        c.setFillColorRGB(*fill_rgb)
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(0)
        c.rect(0, ribbon_bottom, width, height - ribbon_bottom, fill=1, stroke=0)

        # Add a thin border line at the bottom of the ribbon
        c.setStrokeColorRGB(*text_rgb)
        c.setLineWidth(1.5)
        c.line(0, ribbon_bottom, width, ribbon_bottom)

        # Copy label at top of ribbon
        c.setFillColorRGB(*text_rgb)
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(width/2, height - 0.35*inch, copy_label)

        # Title
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width/2, height - 0.65*inch, "ADDITIONAL WORK / CHANGE ORDER")

        # Subtitle
        c.setFont("Helvetica", 10)
        c.drawCentredString(width/2, height - 0.85*inch, "Woods Comfort Systems | TACLA16934C")

        # Reset colors
        c.setFillColorRGB(0, 0, 0)
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(1)
    
        # ==================== LEFT COLUMN ====================
        left_x = 0.5*inch
        right_col_x = 4.2*inch

        # JOB INFORMATION - Left Side Labels and Lines
        # Define where data starts (with spacing after labels)
        left_data_x = 1.55*inch  # Data starts here on left side
        right_data_x = 5.35*inch  # Data starts here on right side

        y = height - 1.40*inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left_x, y, "Builder Name")
        c.line(left_data_x, y - 2, 3.8*inch, y - 2)
        c.setFont("Helvetica", 10)
        c.drawString(left_data_x + 0.05*inch, y, form_data.get('builder_name', '')[:25])

        c.setFont("Helvetica-Bold", 10)
        c.drawString(right_col_x, y, "Job Number")
        c.line(right_data_x, y - 2, width - 0.5*inch, y - 2)
        c.setFont("Helvetica", 10)
        c.drawString(right_data_x + 0.05*inch, y, form_data.get('job_number', '')[:20])

        y -= 0.3*inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left_x, y, "Job Location")
        c.line(left_data_x, y - 2, 3.8*inch, y - 2)
        c.setFont("Helvetica", 10)
        c.drawString(left_data_x + 0.05*inch, y, form_data.get('job_location', '')[:25])

        c.setFont("Helvetica-Bold", 10)
        c.drawString(right_col_x, y, "Installer")
        c.line(right_data_x, y - 2, width - 0.5*inch, y - 2)
        c.setFont("Helvetica", 10)
        c.drawString(right_data_x + 0.05*inch, y, form_data.get('installer', '')[:20])

        y -= 0.3*inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left_x, y, "Date Requested")
        c.line(left_data_x, y - 2, 3.8*inch, y - 2)
        c.setFont("Helvetica", 10)
        c.drawString(left_data_x + 0.05*inch, y, form_data.get('date_requested', ''))

        c.setFont("Helvetica-Bold", 10)
        c.drawString(right_col_x, y, "Sub/Emp Pay")
        c.line(right_data_x, y - 2, width - 0.5*inch, y - 2)
        c.setFont("Helvetica", 10)
        c.drawString(right_data_x + 0.05*inch, y, form_data.get('sub_emp_pay', '')[:20])

        y -= 0.3*inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left_x, y, "Builder Rep")
        c.line(left_data_x, y - 2, 3.8*inch, y - 2)
        c.setFont("Helvetica", 10)
        c.drawString(left_data_x + 0.05*inch, y, form_data.get('builder_rep', '')[:25])

        c.setFont("Helvetica-Bold", 10)
        c.drawString(right_col_x, y, "Pay Approval")
        c.line(right_data_x, y - 2, width - 0.5*inch, y - 2)
        c.setFont("Helvetica", 10)
        c.drawString(right_data_x + 0.05*inch, y, form_data.get('pay_approval', '')[:20])

        y -= 0.3*inch
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left_x, y, "Phone #")
        c.line(left_data_x, y - 2, 3.8*inch, y - 2)
        c.setFont("Helvetica", 10)
        c.drawString(left_data_x + 0.05*inch, y, form_data.get('phone', '')[:25])

        c.setFont("Helvetica-Bold", 10)
        c.drawString(right_col_x, y, "Plan #")
        c.line(right_data_x, y - 2, width - 0.5*inch, y - 2)
        c.setFont("Helvetica", 10)
        c.drawString(right_data_x + 0.05*inch, y, form_data.get('plan_number', '')[:20])

        # ==================== MATERIAL NEEDED TABLE ====================
        y -= 0.4*inch
        mat_table_top = y
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left_x, y, "Material Needed:")

        # Column headers
        y -= 0.22*inch
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left_x + 0.05*inch, y, "Quantity")
        c.drawString(left_x + 1.1*inch, y, "")
        c.setFont("Helvetica-Bold", 8)
        c.drawString(left_x + 0.1*inch, y - 0.12*inch, "Ordered")
        c.drawString(left_x + 0.65*inch, y - 0.12*inch, "Pulled")

        # Draw table grid for materials - 12 rows
        table_left = left_x
        table_width = 3.4*inch
        row_height = 0.22*inch
        col1_width = 0.5*inch  # Ordered
        col2_width = 0.5*inch  # Pulled
        col3_width = table_width - col1_width - col2_width  # Description

        y -= 0.25*inch
        table_start_y = y

        # Draw 12 rows
        c.setFont("Helvetica", 8)
        for i in range(12):
            row_y = table_start_y - (i * row_height)
            # Draw row lines
            c.rect(table_left, row_y - row_height, col1_width, row_height)
            c.rect(table_left + col1_width, row_y - row_height, col2_width, row_height)
            c.rect(table_left + col1_width + col2_width, row_y - row_height, col3_width, row_height)

            # Fill in data
            desc = form_data.get(f'mat_need_desc_{i}', '')
            ordered = form_data.get(f'mat_need_ord_{i}', '')
            pulled = form_data.get(f'mat_need_pull_{i}', '')
            c.drawString(table_left + 0.05*inch, row_y - row_height + 0.06*inch, ordered[:6])
            c.drawString(table_left + col1_width + 0.05*inch, row_y - row_height + 0.06*inch, pulled[:6])
            c.drawString(table_left + col1_width + col2_width + 0.05*inch, row_y - row_height + 0.06*inch, desc[:30])

        # ==================== CHANGE ORDER SECTION (Right Side) ====================
        change_x = 4.2*inch
        change_y = mat_table_top

        c.setFont("Helvetica-Bold", 11)
        c.drawString(change_x, change_y, "Change Order")

        change_y -= 0.25*inch
        # Checkboxes
        c.rect(change_x, change_y - 0.12*inch, 0.12*inch, 0.12*inch)
        if form_data.get('charge'):
            c.drawString(change_x + 0.02*inch, change_y - 0.1*inch, "X")
        c.setFont("Helvetica", 9)
        c.drawString(change_x + 0.18*inch, change_y, "Charge")

        c.rect(change_x + 0.8*inch, change_y - 0.12*inch, 0.12*inch, 0.12*inch)
        if form_data.get('no_charge'):
            c.drawString(change_x + 0.82*inch, change_y - 0.1*inch, "X")
        c.drawString(change_x + 0.98*inch, change_y, "N/C")

        change_y -= 0.3*inch
        c.setFont("Helvetica-Bold", 9)
        c.drawString(change_x, change_y, "Amount to Bill")
        c.line(change_x + 0.9*inch, change_y - 2, width - 0.5*inch, change_y - 2)
        c.setFont("Helvetica", 9)
        c.drawString(change_x + 0.95*inch, change_y, form_data.get('amount_to_bill', ''))
        c.setFont("Helvetica", 7)
        c.drawString(width - 1.5*inch, change_y - 0.12*inch, "Enter N/C if No Charge")

        change_y -= 0.3*inch
        c.setFont("Helvetica-Bold", 9)
        c.drawString(change_x, change_y, "Purchase Order Number")
        c.line(change_x + 1.35*inch, change_y - 2, width - 0.5*inch, change_y - 2)
        c.setFont("Helvetica", 9)
        c.drawString(change_x + 1.4*inch, change_y, form_data.get('po_number', ''))
        c.setFont("Helvetica", 7)
        c.drawString(width - 1.5*inch, change_y - 0.12*inch, "Enter NA if no PO Required")

        # Hours/Phase/Amount table
        change_y -= 0.4*inch
        c.setFont("Helvetica-Bold", 9)
        c.drawString(change_x + 0.1*inch, change_y, "Hours")
        c.drawString(change_x + 0.7*inch, change_y, "Phase")
        c.drawString(change_x + 1.6*inch, change_y, "Amount")

        phases = [
            ('rough', 'Rough-25'),
            ('finish', 'Finish-45'),
            ('sub', 'Sub-41'),
            ('material', 'Material-21'),
            ('warres', 'War Res-00'),
            ('permit', 'Permit-00')
        ]

        change_y -= 0.18*inch
        c.setFont("Helvetica", 9)
        for key, label in phases:
            hrs = form_data.get(f'hours_{key}', '')
            amt = form_data.get(f'amount_{key}', '')
            c.line(change_x, change_y - 2, change_x + 0.5*inch, change_y - 2)
            c.drawString(change_x + 0.05*inch, change_y, hrs)
            c.drawString(change_x + 0.7*inch, change_y, label)
            c.line(change_x + 1.5*inch, change_y - 2, change_x + 2.1*inch, change_y - 2)
            c.drawString(change_x + 1.55*inch, change_y, amt)
            change_y -= 0.22*inch

        # Reason if no charge
        change_y -= 0.1*inch
        c.setFont("Helvetica-Bold", 8)
        c.drawString(change_x, change_y, "Reason if no charge to customer:")
        change_y -= 0.18*inch
        c.line(change_x, change_y - 2, width - 0.5*inch, change_y - 2)
        c.setFont("Helvetica", 8)
        c.drawString(change_x + 0.05*inch, change_y, form_data.get('reason_no_charge', '')[:40])

        # ==================== WORK NEEDED ====================
        y = table_start_y - (12 * row_height) - 0.35*inch
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left_x, y, "WORK NEEDED")
        c.line(left_x + 1.1*inch, y - 2, width - 0.5*inch, y - 2)

        # Draw 4 lines for work needed
        y -= 0.25*inch
        work_needed = form_data.get('work_needed', '')
        c.setFont("Helvetica", 9)

        # Word wrap and fill lines
        words = work_needed.split() if work_needed else []
        lines = []
        current_line = ''
        for word in words:
            if c.stringWidth(current_line + ' ' + word, "Helvetica", 9) < (width - 1.2*inch):
                current_line += ' ' + word if current_line else word
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        for i in range(4):
            c.line(left_x, y - 2, width - 0.5*inch, y - 2)
            if i < len(lines):
                c.drawString(left_x + 0.05*inch, y, lines[i])
            y -= 0.25*inch

        # ==================== WAS WORK COMPLETED ====================
        y -= 0.15*inch
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left_x, y, "Was Work Completed")
        c.line(left_x + 1.35*inch, y - 2, width - 0.5*inch, y - 2)

        # Draw 3 lines for work completed
        y -= 0.25*inch
        work_completed = form_data.get('work_completed', '')

        words = work_completed.split() if work_completed else []
        lines = []
        current_line = ''
        for word in words:
            if c.stringWidth(current_line + ' ' + word, "Helvetica", 9) < (width - 1.2*inch):
                current_line += ' ' + word if current_line else word
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)

        c.setFont("Helvetica", 9)
        for i in range(3):
            c.line(left_x, y - 2, width - 0.5*inch, y - 2)
            if i < len(lines):
                c.drawString(left_x + 0.05*inch, y, lines[i])
            y -= 0.25*inch

        # ==================== SIGNATURES ====================
        y -= 0.3*inch
        c.line(left_x, y, 2.5*inch, y)
        c.setFont("Helvetica", 9)
        c.drawString(left_x, y - 0.15*inch, "Sub Contractor or Employee Sign")
        if form_data.get('sub_sign'):
            c.drawString(left_x + 0.05*inch, y + 0.05*inch, form_data.get('sub_sign', ''))

        c.line(2.8*inch, y, 5*inch, y)
        c.drawString(2.8*inch, y - 0.15*inch, "Field Supervisor Sign")
        if form_data.get('supervisor_sign'):
            c.drawString(2.85*inch, y + 0.05*inch, form_data.get('supervisor_sign', ''))

        c.setFont("Helvetica-Bold", 9)
        c.drawString(5.3*inch, y - 0.15*inch, "Date")
        c.line(5.6*inch, y, width - 0.5*inch, y)
        c.setFont("Helvetica", 9)
        c.drawString(5.65*inch, y + 0.05*inch, form_data.get('sign_date', ''))

        # ==================== FOOTER ====================
        c.setFont("Helvetica", 8)
        c.drawCentredString(width/2, 0.6*inch, "Piece pay includes loading and unloading of material and drive to and from job.")

        # Small copy indicator at bottom
        c.setFont("Helvetica", 7)
        c.drawCentredString(width/2, 0.4*inch, copy_label)

    # End of triplicate loop
    c.save()
    
    pdf_data = buffer.getvalue()
    buffer.close()
    
    builder = form_data.get('builder_name', 'Unknown').replace(' ', '_')
    job = form_data.get('job_number', '')
    today = datetime.now().strftime('%Y%m%d')
    filename = f"Additional_Work_{builder}_{job}_{today}.pdf".replace('__', '_')
    
    return send_file(
        io.BytesIO(pdf_data),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/generate-linear-grille-pdf', methods=['POST'])
def generate_linear_grille_pdf():
    """Generate PDF from Linear Grille Order form - Fixed Layout"""
    form_data = request.form.to_dict()
    
    # Handle checkboxes
    is_bid = 'is_bid' in request.form
    is_quote = 'is_quote' in request.form
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    # Fixed positions
    left_x = 0.5*inch
    data_x = 1.7*inch
    line_end = width - 0.5*inch
    row_space = 0.26*inch
    
    # Job Information FIRST (at very top)
    y = height - 0.5*inch
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x, y, "Address:")
    c.line(data_x, y - 2, line_end, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(data_x + 0.05*inch, y, form_data.get('address', '')[:55])
    
    y -= row_space
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x, y, "Builder:")
    c.line(data_x, y - 2, line_end, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(data_x + 0.05*inch, y, form_data.get('builder', '')[:55])
    
    y -= row_space
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x, y, "Job Number:")
    c.line(data_x, y - 2, 3.8*inch, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(data_x + 0.05*inch, y, form_data.get('job_number', '')[:25])
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(4*inch, y, "Date of Request:")
    c.line(5.2*inch, y - 2, line_end, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(5.25*inch, y, form_data.get('date_request', ''))
    
    y -= row_space
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x, y, "Date Needed:")
    c.line(data_x, y - 2, 3.8*inch, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(data_x + 0.05*inch, y, form_data.get('date_needed', ''))
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(4*inch, y, "Requested by:")
    c.line(5.2*inch, y - 2, line_end, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(5.25*inch, y, form_data.get('requested_by', '')[:25])
    
    # Title - Large and Blue for Nailor (after job info)
    y -= 0.4*inch
    c.setFont("Helvetica-Bold", 18)
    c.setFillColorRGB(0.1, 0.32, 0.46)  # Dark blue
    c.drawCentredString(width/2, y, "Nailor Linear Slot & Bar Grille Order Form")
    c.setFillColorRGB(0, 0, 0)
    y -= 0.18*inch
    c.setFont("Helvetica", 9)
    c.drawCentredString(width/2, y, "Woods Comfort Systems | TACLA16934C")
    
    # Bid / Quote checkboxes
    y -= 0.25*inch
    c.setFont("Helvetica-Bold", 11)
    
    # Bid checkbox
    c.rect(0.5*inch, y - 0.02*inch, 0.15*inch, 0.15*inch)
    if is_bid:
        c.setFillColorRGB(0.15, 0.68, 0.38)  # Green
        c.drawString(0.53*inch, y, "X")
    c.setFillColorRGB(0.15, 0.68, 0.38)  # Green
    c.drawString(0.72*inch, y, "BID - Proceed with Order")
    
    # Quote checkbox
    c.rect(2.8*inch, y - 0.02*inch, 0.15*inch, 0.15*inch)
    c.setFillColorRGB(0, 0, 0)
    if is_quote:
        c.setFillColorRGB(0.9, 0.49, 0.13)  # Orange
        c.drawString(2.83*inch, y, "X")
    c.setFillColorRGB(0.9, 0.49, 0.13)  # Orange
    c.drawString(3.02*inch, y, "QUOTE ONLY - Get Pricing")
    c.setFillColorRGB(0, 0, 0)
    
    # Draw line under checkboxes
    y -= 0.15*inch
    c.setLineWidth(0.5)
    c.line(0.5*inch, y, width - 0.5*inch, y)
    
    # Supply Grille data
    supply_grilles = [
        ('5010', '1', '12" x 21/8"', '50 CFM', 'KA - MI - MM'),
        ('5010', '1', '18" x 21/8"', '75 CFM', 'KA - MI - MM'),
        ('5010', '1', '24" x 21/8"', '100 CFM', 'KA - MI - MM'),
        ('5010', '1', '36" x 21/8"', '150 CFM', 'KA - MI - MM'),
        ('5010', '1', '48" x 21/8"', '200 CFM', 'KA - MI - MM'),
    ]
    
    # MUD-IN Linear Bar Grille data (21 sizes with CFM)
    mudin_grilles = [
        ('49-240', '8" x 4"', '80 CFM'),
        ('49-240', '10" x 8"', '200 CFM'),
        ('49-240', '10" x 10"', '250 CFM'),
        ('49-240', '12" x 4"', '120 CFM'),
        ('49-240', '12" x 6"', '180 CFM'),
        ('49-240', '12" x 12"', '360 CFM'),
        ('49-240', '12" x 24"', '720 CFM'),
        ('49-240', '14" x 6"', '210 CFM'),
        ('49-240', '14" x 8"', '280 CFM'),
        ('49-240', '14" x 24"', '840 CFM'),
        ('49-240', '14" x 30"', '1,050 CFM'),
        ('49-240', '16" x 4"', '160 CFM'),
        ('49-240', '16" x 6"', '240 CFM'),
        ('49-240', '16" x 30"', '1,200 CFM'),
        ('49-240', '18" x 4"', '180 CFM'),
        ('49-240', '18" x 30"', '1,350 CFM'),
        ('49-240', '20" x 20"', '1,000 CFM'),
        ('49-240', '20" x 25"', '1,250 CFM'),
        ('49-240', '24" x 4"', '240 CFM'),
        ('49-240', '24" x 12"', '720 CFM'),
        ('49-240', '24" x 14"', '840 CFM'),
        ('49-240', '25" x 16"', '1,000 CFM'),
        ('49-240', '30" x 12"', '900 CFM'),
        ('49-240', '30" x 14"', '1,050 CFM'),
        ('49-240', '30" x 16"', '1,200 CFM'),
        ('49-240', '30" x 18"', '1,350 CFM'),
        ('49-240', '36" x 4"', '360 CFM'),
        ('49-240', '36" x 20"', '1,800 CFM'),
        ('49-240', '36" x 24"', '2,160 CFM'),
        ('49-240', '48" x 4"', '480 CFM'),
    ]
    
    # Surface Mount Grille data (same 21 sizes with CFM)
    surface_grilles = [
        ('49-240', '8" x 4"', '80 CFM'),
        ('49-240', '10" x 8"', '200 CFM'),
        ('49-240', '10" x 10"', '250 CFM'),
        ('49-240', '12" x 12"', '360 CFM'),
        ('49-240', '12" x 24"', '720 CFM'),
        ('49-240', '14" x 8"', '280 CFM'),
        ('49-240', '14" x 24"', '840 CFM'),
        ('49-240', '14" x 30"', '1,050 CFM'),
        ('49-240', '16" x 30"', '1,200 CFM'),
        ('49-240', '18" x 30"', '1,350 CFM'),
        ('49-240', '20" x 20"', '1,000 CFM'),
        ('49-240', '20" x 25"', '1,250 CFM'),
        ('49-240', '24" x 12"', '720 CFM'),
        ('49-240', '24" x 14"', '840 CFM'),
        ('49-240', '25" x 16"', '1,000 CFM'),
        ('49-240', '30" x 12"', '900 CFM'),
        ('49-240', '30" x 14"', '1,050 CFM'),
        ('49-240', '30" x 16"', '1,200 CFM'),
        ('49-240', '30" x 18"', '1,350 CFM'),
        ('49-240', '36" x 20"', '1,800 CFM'),
        ('49-240', '36" x 24"', '2,160 CFM'),
    ]
    
    # ==================== SUPPLY TABLE ====================
    y -= 0.4*inch
    c.setFont("Helvetica-Bold", 10)
    c.setFillColorRGB(0.1, 0.32, 0.46)  # Dark blue
    c.drawString(left_x, y, "MUD-IN Linear Slot Supply Grille (Model 5010)")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 7)
    c.drawString(4.2*inch, y, "Options: KA-Tape & Spackle Frame, MI-Mill/White, MM-Mitered")
    
    y -= 0.18*inch
    # Table header
    c.setFont("Helvetica-Bold", 8)
    c.drawString(left_x, y, "QTY")
    c.drawString(left_x + 0.5*inch, y, "Model")
    c.drawString(left_x + 1.1*inch, y, "Slots")
    c.drawString(left_x + 1.5*inch, y, "Rough Opening")
    c.drawString(left_x + 2.7*inch, y, "Est. CFM")
    c.drawString(left_x + 3.5*inch, y, "Options")
    
    y -= 0.12*inch
    c.setFont("Helvetica", 8)
    row_h = 0.18*inch
    
    for i, (model, slots, size, cfm, opts) in enumerate(supply_grilles):
        qty = form_data.get(f'supply_qty_{i}', '')
        c.rect(left_x, y - row_h, 0.4*inch, row_h)
        c.drawString(left_x + 0.1*inch, y - row_h + 0.05*inch, qty[:4])
        c.drawString(left_x + 0.5*inch, y - row_h + 0.05*inch, model)
        c.drawString(left_x + 1.15*inch, y - row_h + 0.05*inch, slots)
        c.drawString(left_x + 1.5*inch, y - row_h + 0.05*inch, size)
        c.drawString(left_x + 2.7*inch, y - row_h + 0.05*inch, cfm)
        c.drawString(left_x + 3.5*inch, y - row_h + 0.05*inch, opts)
        y -= row_h

    # Add 3 blank custom rows for Supply grilles
    c.setFont("Helvetica-Bold", 7)
    c.setFillColorRGB(0.1, 0.32, 0.46)
    c.drawString(left_x, y - 0.02*inch, "CUSTOM SIZES:")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 8)
    y -= 0.14*inch
    for i in range(3):
        c.rect(left_x, y - row_h, 0.4*inch, row_h)
        custom_qty = form_data.get(f'supply_custom_qty_{i}', '')
        c.drawString(left_x + 0.1*inch, y - row_h + 0.05*inch, custom_qty[:4])
        c.drawString(left_x + 0.5*inch, y - row_h + 0.05*inch, "5010")
        # Slots blank
        c.line(left_x + 1.15*inch, y - row_h + 0.02*inch, left_x + 1.4*inch, y - row_h + 0.02*inch)
        # Size blank line
        c.line(left_x + 1.5*inch, y - row_h + 0.02*inch, left_x + 2.5*inch, y - row_h + 0.02*inch)
        custom_size = form_data.get(f'supply_custom_size_{i}', '')
        if custom_size:
            c.drawString(left_x + 1.5*inch, y - row_h + 0.05*inch, custom_size)
        # CFM blank line
        c.line(left_x + 2.7*inch, y - row_h + 0.02*inch, left_x + 3.3*inch, y - row_h + 0.02*inch)
        custom_cfm = form_data.get(f'supply_custom_cfm_{i}', '')
        if custom_cfm:
            c.drawString(left_x + 2.7*inch, y - row_h + 0.05*inch, custom_cfm)
        c.drawString(left_x + 3.5*inch, y - row_h + 0.05*inch, "KA - MI - MM")
        y -= row_h

    # ==================== MUD-IN LINEAR BAR TABLE ====================
    y -= 0.25*inch
    c.setFont("Helvetica-Bold", 10)
    c.setFillColorRGB(0.1, 0.32, 0.46)
    c.drawString(left_x, y, "MUD-IN Linear Bar Grille (Model 49-240)")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 7)
    c.drawString(4*inch, y, "Options: K-Tape & Spackle, AW-Appliance White, A-Aluminum OBD, MM-Mitered")
    
    y -= 0.18*inch
    c.setFont("Helvetica-Bold", 8)
    # Two columns for MUD-IN
    col1_x = left_x
    col2_x = 4.2*inch
    c.drawString(col1_x, y, "QTY")
    c.drawString(col1_x + 0.5*inch, y, "Model")
    c.drawString(col1_x + 1.1*inch, y, "Size")
    c.drawString(col1_x + 1.85*inch, y, "CFM")
    c.drawString(col2_x, y, "QTY")
    c.drawString(col2_x + 0.5*inch, y, "Model")
    c.drawString(col2_x + 1.1*inch, y, "Size")
    c.drawString(col2_x + 1.85*inch, y, "CFM")
    
    y -= 0.12*inch
    c.setFont("Helvetica", 8)
    row_h = 0.16*inch
    
    # Split into two columns (15 left, 15 right)
    left_mudin = mudin_grilles[:15]
    right_mudin = mudin_grilles[15:]

    start_y = y
    for i, (model, size, cfm) in enumerate(left_mudin):
        qty = form_data.get(f'mudin_qty_{i}', '')
        c.rect(col1_x, y - row_h, 0.4*inch, row_h)
        c.drawString(col1_x + 0.1*inch, y - row_h + 0.04*inch, qty[:4])
        c.drawString(col1_x + 0.5*inch, y - row_h + 0.04*inch, model)
        c.drawString(col1_x + 1.1*inch, y - row_h + 0.04*inch, size)
        c.setFillColorRGB(0.15, 0.68, 0.38)  # Green for CFM
        c.drawString(col1_x + 1.85*inch, y - row_h + 0.04*inch, cfm)
        c.setFillColorRGB(0, 0, 0)
        y -= row_h

    y = start_y
    for i, (model, size, cfm) in enumerate(right_mudin):
        qty = form_data.get(f'mudin_qty_{i + 15}', '')
        c.rect(col2_x, y - row_h, 0.4*inch, row_h)
        c.drawString(col2_x + 0.1*inch, y - row_h + 0.04*inch, qty[:4])
        c.drawString(col2_x + 0.5*inch, y - row_h + 0.04*inch, model)
        c.drawString(col2_x + 1.1*inch, y - row_h + 0.04*inch, size)
        c.setFillColorRGB(0.15, 0.68, 0.38)  # Green for CFM
        c.drawString(col2_x + 1.85*inch, y - row_h + 0.04*inch, cfm)
        c.setFillColorRGB(0, 0, 0)
        y -= row_h
    
    # Add 6 blank custom size rows below right column for MUD-IN
    mudin_custom_y = start_y - (len(right_mudin) * row_h)
    c.setFont("Helvetica-Bold", 7)
    c.setFillColorRGB(0.1, 0.32, 0.46)
    c.drawString(col2_x, mudin_custom_y - 0.02*inch, "CUSTOM SIZES:")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 8)
    mudin_custom_y -= 0.14*inch
    for i in range(6):
        # QTY box
        c.rect(col2_x, mudin_custom_y - row_h, 0.4*inch, row_h)
        custom_qty = form_data.get(f'mudin_custom_qty_{i}', '')
        c.drawString(col2_x + 0.1*inch, mudin_custom_y - row_h + 0.04*inch, custom_qty[:4])
        # Model pre-filled
        c.drawString(col2_x + 0.5*inch, mudin_custom_y - row_h + 0.04*inch, "49-240")
        # Size blank line
        c.line(col2_x + 1.1*inch, mudin_custom_y - row_h + 0.02*inch, col2_x + 1.75*inch, mudin_custom_y - row_h + 0.02*inch)
        custom_size = form_data.get(f'mudin_custom_size_{i}', '')
        if custom_size:
            c.drawString(col2_x + 1.1*inch, mudin_custom_y - row_h + 0.04*inch, custom_size)
        # CFM blank line
        c.line(col2_x + 1.85*inch, mudin_custom_y - row_h + 0.02*inch, col2_x + 2.3*inch, mudin_custom_y - row_h + 0.02*inch)
        custom_cfm = form_data.get(f'mudin_custom_cfm_{i}', '')
        if custom_cfm:
            c.drawString(col2_x + 1.85*inch, mudin_custom_y - row_h + 0.04*inch, custom_cfm)
        mudin_custom_y -= row_h

    # Use whichever column extends lower: left column bottom or custom sizes bottom
    left_mudin_bottom = start_y - (len(left_mudin) * row_h)
    y = min(left_mudin_bottom, mudin_custom_y)

    # ==================== SURFACE MOUNT TABLE ====================
    y -= 0.25*inch
    c.setFont("Helvetica-Bold", 10)
    c.setFillColorRGB(0.1, 0.32, 0.46)
    c.drawString(left_x, y, "Surface Mount Linear Bar Grille (Model 49-240)")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 7)
    c.drawString(4*inch, y, "Options: A-Frame Type A, AW-Appliance White, A-Aluminum OBD, MM-Mitered")
    
    y -= 0.18*inch
    c.setFont("Helvetica-Bold", 8)
    c.drawString(col1_x, y, "QTY")
    c.drawString(col1_x + 0.5*inch, y, "Model")
    c.drawString(col1_x + 1.1*inch, y, "Size")
    c.drawString(col1_x + 1.85*inch, y, "CFM")
    c.drawString(col2_x, y, "QTY")
    c.drawString(col2_x + 0.5*inch, y, "Model")
    c.drawString(col2_x + 1.1*inch, y, "Size")
    c.drawString(col2_x + 1.85*inch, y, "CFM")
    
    y -= 0.12*inch
    c.setFont("Helvetica", 8)
    row_h = 0.16*inch
    
    # Split into two columns (11 left, 10 right)
    left_surface = surface_grilles[:11]
    right_surface = surface_grilles[11:]
    
    start_y = y
    for i, (model, size, cfm) in enumerate(left_surface):
        qty = form_data.get(f'surface_qty_{i}', '')
        c.rect(col1_x, y - row_h, 0.4*inch, row_h)
        c.drawString(col1_x + 0.1*inch, y - row_h + 0.04*inch, qty[:4])
        c.drawString(col1_x + 0.5*inch, y - row_h + 0.04*inch, model)
        c.drawString(col1_x + 1.1*inch, y - row_h + 0.04*inch, size)
        c.setFillColorRGB(0.15, 0.68, 0.38)  # Green for CFM
        c.drawString(col1_x + 1.85*inch, y - row_h + 0.04*inch, cfm)
        c.setFillColorRGB(0, 0, 0)
        y -= row_h
    
    y = start_y
    for i, (model, size, cfm) in enumerate(right_surface):
        qty = form_data.get(f'surface_qty_{i + 11}', '')
        c.rect(col2_x, y - row_h, 0.4*inch, row_h)
        c.drawString(col2_x + 0.1*inch, y - row_h + 0.04*inch, qty[:4])
        c.drawString(col2_x + 0.5*inch, y - row_h + 0.04*inch, model)
        c.drawString(col2_x + 1.1*inch, y - row_h + 0.04*inch, size)
        c.setFillColorRGB(0.15, 0.68, 0.38)  # Green for CFM
        c.drawString(col2_x + 1.85*inch, y - row_h + 0.04*inch, cfm)
        c.setFillColorRGB(0, 0, 0)
        y -= row_h
    
    # Add 6 blank custom size rows below right column for Surface Mount
    surf_custom_y = start_y - (len(right_surface) * row_h)
    c.setFont("Helvetica-Bold", 7)
    c.setFillColorRGB(0.1, 0.32, 0.46)
    c.drawString(col2_x, surf_custom_y - 0.02*inch, "CUSTOM SIZES:")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 8)
    surf_custom_y -= 0.14*inch
    for i in range(6):
        # QTY box
        c.rect(col2_x, surf_custom_y - row_h, 0.4*inch, row_h)
        custom_qty = form_data.get(f'surface_custom_qty_{i}', '')
        c.drawString(col2_x + 0.1*inch, surf_custom_y - row_h + 0.04*inch, custom_qty[:4])
        # Model pre-filled
        c.drawString(col2_x + 0.5*inch, surf_custom_y - row_h + 0.04*inch, "49-240")
        # Size blank line
        c.line(col2_x + 1.1*inch, surf_custom_y - row_h + 0.02*inch, col2_x + 1.75*inch, surf_custom_y - row_h + 0.02*inch)
        custom_size = form_data.get(f'surface_custom_size_{i}', '')
        if custom_size:
            c.drawString(col2_x + 1.1*inch, surf_custom_y - row_h + 0.04*inch, custom_size)
        # CFM blank line
        c.line(col2_x + 1.85*inch, surf_custom_y - row_h + 0.02*inch, col2_x + 2.3*inch, surf_custom_y - row_h + 0.02*inch)
        custom_cfm = form_data.get(f'surface_custom_cfm_{i}', '')
        if custom_cfm:
            c.drawString(col2_x + 1.85*inch, surf_custom_y - row_h + 0.04*inch, custom_cfm)
        surf_custom_y -= row_h

    # Calculate final y position (whichever extends lower: left column or custom sizes)
    left_surface_bottom = start_y - (len(left_surface) * row_h)
    y = min(left_surface_bottom, surf_custom_y)

    # Notes
    notes = form_data.get('notes', '')
    if notes:
        y -= 0.3*inch
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left_x, y, "Notes:")
        y -= 0.15*inch
        c.setFont("Helvetica", 8)
        # Word wrap notes
        words = notes.split()
        line = ''
        for word in words:
            if c.stringWidth(line + ' ' + word, "Helvetica", 8) < (width - 1*inch):
                line += ' ' + word if line else word
            else:
                c.drawString(left_x, y, line)
                y -= 0.12*inch
                line = word
                if y < 0.8*inch:
                    break
        if line and y >= 0.8*inch:
            c.drawString(left_x, y, line)
    
    # Reference notes at bottom
    y = 0.9*inch
    c.setFont("Helvetica", 7)
    c.drawString(left_x, y, "- MUD-IN: Rough opening = ordered grille size. Installed AFTER drywall. Countersunk screw holes for fastening.")
    y -= 0.1*inch
    c.drawString(left_x, y, "- 5010 Supply: 1\" slot width, ~50 CFM/ft  |  49-240 Return: 0-deg deflection, pencil proof, OBD damper")
    
    # Footer Page 1
    c.setFont("Helvetica", 8)
    c.drawCentredString(width/2, 0.4*inch, "Woods Comfort Systems | San Marcos, Texas | TACLA16934C")
    c.drawRightString(width - 0.5*inch, 0.4*inch, "Page 1 of 2")
    
    # ==================== PAGE 2: TEXAS BUILDMART ====================
    c.showPage()
    
    # Job Information FIRST (at very top - same as page 1)
    y = height - 0.5*inch
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x, y, "Address:")
    c.line(data_x, y - 2, line_end, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(data_x + 0.05*inch, y, form_data.get('address', '')[:55])
    
    y -= row_space
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x, y, "Builder:")
    c.line(data_x, y - 2, line_end, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(data_x + 0.05*inch, y, form_data.get('builder', '')[:55])
    
    y -= row_space
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x, y, "Job Number:")
    c.line(data_x, y - 2, 3.8*inch, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(data_x + 0.05*inch, y, form_data.get('job_number', '')[:25])
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(4*inch, y, "Date of Request:")
    c.line(5.2*inch, y - 2, line_end, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(5.25*inch, y, form_data.get('date_request', ''))
    
    y -= row_space
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left_x, y, "Date Needed:")
    c.line(data_x, y - 2, 3.8*inch, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(data_x + 0.05*inch, y, form_data.get('date_needed', ''))
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(4*inch, y, "Requested by:")
    c.line(5.2*inch, y - 2, line_end, y - 2)
    c.setFont("Helvetica", 10)
    c.drawString(5.25*inch, y, form_data.get('requested_by', '')[:25])
    
    # Page 2 Title - Large and Red for Texas Buildmart (after job info)
    y -= 0.4*inch
    c.setFont("Helvetica-Bold", 18)
    c.setFillColorRGB(0.57, 0.17, 0.13)  # Dark red
    c.drawCentredString(width/2, y, "Texas Buildmart Surface Mount Grille Order Form")
    c.setFillColorRGB(0, 0, 0)
    y -= 0.18*inch
    c.setFont("Helvetica", 9)
    c.drawCentredString(width/2, y, "Woods Comfort Systems | TACLA16934C")
    
    # Bid / Quote checkboxes
    y -= 0.25*inch
    c.setFont("Helvetica-Bold", 11)
    
    c.rect(0.5*inch, y - 0.02*inch, 0.15*inch, 0.15*inch)
    if is_bid:
        c.setFillColorRGB(0.15, 0.68, 0.38)
        c.drawString(0.53*inch, y, "X")
    c.setFillColorRGB(0.15, 0.68, 0.38)
    c.drawString(0.72*inch, y, "BID - Proceed with Order")
    
    c.rect(2.8*inch, y - 0.02*inch, 0.15*inch, 0.15*inch)
    c.setFillColorRGB(0, 0, 0)
    if is_quote:
        c.setFillColorRGB(0.9, 0.49, 0.13)
        c.drawString(2.83*inch, y, "X")
    c.setFillColorRGB(0.9, 0.49, 0.13)
    c.drawString(3.02*inch, y, "QUOTE ONLY - Get Pricing")
    c.setFillColorRGB(0, 0, 0)
    
    # Draw line under checkboxes
    y -= 0.15*inch
    c.setLineWidth(0.5)
    c.line(0.5*inch, y, width - 0.5*inch, y)
    
    # Texas Buildmart 2-Slot Linear Diffusers
    tbm_slot_grilles = [
        ('12"', '145 CFM', '11 7/8" x 3 1/8"', '13 1/4" x 4 5/8"'),
        ('18"', '174 CFM', '17 3/4" x 3 1/8"', '19 1/8" x 4 5/8"'),
        ('24"', '199 CFM', '23 5/8" x 3 1/8"', '25 1/16" x 4 5/8"'),
        ('36"', '302 CFM', '35 3/8" x 3 1/8"', '36 3/4" x 4 1/2"'),
        ('48"', '401 CFM', '47 1/4" x 3 1/8"', '48 3/4" x 4 1/2"'),
    ]
    
    # Texas Buildmart Vent Covers - organized by size
    tbm_vent_grilles = [
        ('6" x 6"', '148 CFM'),
        ('8" x 4"', '138 CFM'),
        ('8" x 8"', '218 CFM'),
        ('10" x 8"', '228 CFM'),
        ('10" x 10"', '243 CFM'),
        ('12" x 6"', '233 CFM'),
        ('12" x 12"', '293 CFM'),
        ('14" x 6"', '254 CFM'),
        ('14" x 8"', '255 CFM'),
        ('14" x 14"', '328 CFM'),
        ('24" x 12"', '366 CFM'),
        ('24" x 14"', '445 CFM'),
        ('24" x 16"', '508 CFM'),
        ('24" x 20"', '636 CFM'),
        ('24" x 24"', '763 CFM'),
        ('30" x 12"', '411 CFM'),
        ('30" x 16"', '593 CFM'),
        ('30" x 18"', '678 CFM'),
        ('30" x 20"', '753 CFM'),
        ('30" x 24"', '908 CFM'),
        ('36" x 10"', '449 CFM'),
    ]
    
    # ==================== TBM 2-SLOT TABLE ====================
    y -= 0.35*inch
    c.setFont("Helvetica-Bold", 10)
    c.setFillColorRGB(0.57, 0.17, 0.13)  # Dark red
    c.drawString(left_x, y, "2-Slot Linear Slot Diffuser - Surface Mount (White)")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 7)
    c.drawString(4.5*inch, y, "Double Slot - 3/4\" Slot Width")
    
    y -= 0.18*inch
    c.setFont("Helvetica-Bold", 8)
    c.drawString(left_x, y, "QTY")
    c.drawString(left_x + 0.5*inch, y, "Size")
    c.drawString(left_x + 1.1*inch, y, "CFM")
    c.drawString(left_x + 1.8*inch, y, "Neck Size")
    c.drawString(left_x + 3.3*inch, y, "Face Size")
    
    y -= 0.12*inch
    c.setFont("Helvetica", 8)
    row_h = 0.18*inch
    
    for i, (size, cfm, neck, face) in enumerate(tbm_slot_grilles):
        qty = form_data.get(f'tbm_slot_qty_{i}', '')
        c.rect(left_x, y - row_h, 0.4*inch, row_h)
        c.drawString(left_x + 0.1*inch, y - row_h + 0.05*inch, qty[:4])
        c.drawString(left_x + 0.5*inch, y - row_h + 0.05*inch, size)
        c.setFillColorRGB(0.15, 0.68, 0.38)  # Green for CFM
        c.drawString(left_x + 1.1*inch, y - row_h + 0.05*inch, cfm)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(left_x + 1.8*inch, y - row_h + 0.05*inch, neck)
        c.drawString(left_x + 3.3*inch, y - row_h + 0.05*inch, face)
        y -= row_h
    
    # ==================== TBM VENT COVERS TABLE ====================
    y -= 0.3*inch
    c.setFont("Helvetica-Bold", 10)
    c.setFillColorRGB(0.57, 0.17, 0.13)  # Dark red
    c.drawString(left_x, y, "Modern AC Vent Cover - Surface Mount (White)")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 7)
    c.drawString(4.2*inch, y, "Decorative Air Vent - All Standard Sizes")
    
    y -= 0.18*inch
    c.setFont("Helvetica-Bold", 8)
    # Two columns
    col1_x = left_x
    col2_x = 4.2*inch
    c.drawString(col1_x, y, "QTY")
    c.drawString(col1_x + 0.5*inch, y, "Size")
    c.drawString(col1_x + 1.3*inch, y, "CFM")
    c.drawString(col2_x, y, "QTY")
    c.drawString(col2_x + 0.5*inch, y, "Size")
    c.drawString(col2_x + 1.3*inch, y, "CFM")
    
    y -= 0.12*inch
    c.setFont("Helvetica", 8)
    row_h = 0.17*inch
    
    # Split into two columns (11 left, 10 right)
    left_vents = tbm_vent_grilles[:11]
    right_vents = tbm_vent_grilles[11:]
    
    start_y = y
    for i, (size, cfm) in enumerate(left_vents):
        qty = form_data.get(f'tbm_vent_qty_{i}', '')
        c.rect(col1_x, y - row_h, 0.4*inch, row_h)
        c.drawString(col1_x + 0.1*inch, y - row_h + 0.04*inch, qty[:4])
        c.drawString(col1_x + 0.5*inch, y - row_h + 0.04*inch, size)
        c.setFillColorRGB(0.15, 0.68, 0.38)  # Green for CFM
        c.drawString(col1_x + 1.3*inch, y - row_h + 0.04*inch, cfm)
        c.setFillColorRGB(0, 0, 0)
        y -= row_h
    
    y = start_y
    for i, (size, cfm) in enumerate(right_vents):
        qty = form_data.get(f'tbm_vent_qty_{i + 11}', '')
        c.rect(col2_x, y - row_h, 0.4*inch, row_h)
        c.drawString(col2_x + 0.1*inch, y - row_h + 0.04*inch, qty[:4])
        c.drawString(col2_x + 0.5*inch, y - row_h + 0.04*inch, size)
        c.setFillColorRGB(0.15, 0.68, 0.38)  # Green for CFM
        c.drawString(col2_x + 1.3*inch, y - row_h + 0.04*inch, cfm)
        c.setFillColorRGB(0, 0, 0)
        y -= row_h
    
    # Reset y to bottom of longest column
    y = start_y - (len(left_vents) * row_h)
    
    # Notes section (if any notes were entered, show on page 2 as well)
    notes = form_data.get('notes', '')
    if notes:
        y -= 0.35*inch
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left_x, y, "Notes:")
        y -= 0.15*inch
        c.setFont("Helvetica", 8)
        words = notes.split()
        line = ''
        for word in words:
            if c.stringWidth(line + ' ' + word, "Helvetica", 8) < (width - 1*inch):
                line += ' ' + word if line else word
            else:
                c.drawString(left_x, y, line)
                y -= 0.12*inch
                line = word
                if y < 1.2*inch:
                    break
        if line and y >= 1.2*inch:
            c.drawString(left_x, y, line)
    
    # Reference notes at bottom of page 2
    y = 0.9*inch
    c.setFont("Helvetica", 7)
    c.drawString(left_x, y, "- Texas Buildmart grilles are surface mount only. Neck size = rough opening required.")
    y -= 0.1*inch
    c.drawString(left_x, y, "- All grilles white finish. Face size is visible grille dimension after installation.")
    
    # Footer Page 2
    c.setFont("Helvetica", 8)
    c.drawCentredString(width/2, 0.4*inch, "Woods Comfort Systems | San Marcos, Texas | TACLA16934C")
    c.drawRightString(width - 0.5*inch, 0.4*inch, "Page 2 of 2")
    
    c.save()
    
    pdf_data = buffer.getvalue()
    buffer.close()
    
    builder = form_data.get('builder', 'Unknown').replace(' ', '_')
    job = form_data.get('job_number', '').replace(' ', '_')
    today = datetime.now().strftime('%Y%m%d')
    filename = f"Linear_Grille_Order_{builder}_{job}_{today}.pdf".replace('__', '_')
    
    return send_file(
        io.BytesIO(pdf_data),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

if __name__ == '__main__':
    import webbrowser
    from threading import Timer
    
    def open_browser():
        webbrowser.open('http://localhost:5001')
    
    print("\n" + "="*60)
    print("Woods Comfort Systems - Forms Application")
    print("="*60)
    print("\nStarting server...")
    print("\nThe app will open in your web browser automatically.")
    print("If it doesn't, go to: http://localhost:5001")
    print("\nLeave this window open while using the app.")
    print("Close this window to stop the server.")
    print("="*60 + "\n")
    
    # Open browser after short delay (only from reloader process to avoid double-open)
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        Timer(1.5, open_browser).start()

    # Run with debug mode for development (auto-reloads templates)
    app.run(debug=True, host='localhost', port=5001)