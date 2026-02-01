from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO
from datetime import datetime

class PDFService:
    @staticmethod
    def generate_invoice_pdf(invoice_data, customer_data, items_data):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
        styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT))
        styles.add(ParagraphStyle(name='Left', alignment=TA_LEFT))
        
        elements = []
        
        elements.append(Paragraph("<b>SHIV FURNITURE</b>", styles['Title']))
        elements.append(Paragraph("Budget Accounting System", styles['Center']))
        elements.append(Spacer(1, 20))
        
        elements.append(Paragraph(f"<b>INVOICE</b>", styles['Title']))
        elements.append(Spacer(1, 10))
        
        invoice_info = [
            ['Invoice Number:', invoice_data.get('invoice_number', '')],
            ['Invoice Date:', invoice_data.get('invoice_date', '')],
            ['Due Date:', invoice_data.get('due_date', '')],
            ['Status:', invoice_data.get('payment_status', '').upper()],
        ]
        
        info_table = Table(invoice_info, colWidths=[100, 200])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        elements.append(Paragraph("<b>Bill To:</b>", styles['Normal']))
        elements.append(Paragraph(customer_data.get('name', ''), styles['Normal']))
        if customer_data.get('company_name'):
            elements.append(Paragraph(customer_data.get('company_name', ''), styles['Normal']))
        if customer_data.get('email'):
            elements.append(Paragraph(customer_data.get('email', ''), styles['Normal']))
        if customer_data.get('billing_address'):
            addr = customer_data.get('billing_address', {})
            address_str = f"{addr.get('street', '')}, {addr.get('city', '')}, {addr.get('state', '')} - {addr.get('pincode', '')}"
            elements.append(Paragraph(address_str, styles['Normal']))
        elements.append(Spacer(1, 20))
        
        table_data = [['#', 'Item', 'Qty', 'Unit Price', 'Tax', 'Amount']]
        for idx, item in enumerate(items_data, 1):
            table_data.append([
                str(idx),
                item.get('product_name', ''),
                str(item.get('quantity', 0)),
                f"₹{item.get('unit_price', 0):,.2f}",
                f"₹{item.get('tax_amount', 0):,.2f}",
                f"₹{item.get('subtotal', 0) + item.get('tax_amount', 0):,.2f}"
            ])
        
        items_table = Table(table_data, colWidths=[30, 200, 50, 80, 70, 80])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f9fafb')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 20))
        
        totals_data = [
            ['Subtotal:', f"₹{invoice_data.get('subtotal', 0):,.2f}"],
            ['Tax:', f"₹{invoice_data.get('tax_amount', 0):,.2f}"],
            ['Discount:', f"₹{invoice_data.get('discount_amount', 0):,.2f}"],
            ['Total:', f"₹{invoice_data.get('total_amount', 0):,.2f}"],
            ['Amount Paid:', f"₹{invoice_data.get('amount_paid', 0):,.2f}"],
            ['Amount Due:', f"₹{invoice_data.get('amount_due', 0):,.2f}"],
        ]
        
        totals_table = Table(totals_data, colWidths=[400, 100])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
        ]))
        elements.append(totals_table)
        elements.append(Spacer(1, 30))
        
        elements.append(Paragraph("Thank you for your business!", styles['Center']))
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Center']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    
    @staticmethod
    def generate_purchase_order_pdf(po_data, vendor_data, items_data):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
        styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT))
        
        elements = []
        
        elements.append(Paragraph("<b>SHIV FURNITURE</b>", styles['Title']))
        elements.append(Paragraph("Budget Accounting System", styles['Center']))
        elements.append(Spacer(1, 20))
        
        elements.append(Paragraph(f"<b>PURCHASE ORDER</b>", styles['Title']))
        elements.append(Spacer(1, 10))
        
        po_info = [
            ['PO Number:', po_data.get('po_number', '')],
            ['Order Date:', po_data.get('order_date', '')],
            ['Expected Date:', po_data.get('expected_date', '')],
            ['Status:', po_data.get('status', '').upper()],
        ]
        
        info_table = Table(po_info, colWidths=[100, 200])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        elements.append(Paragraph("<b>Vendor:</b>", styles['Normal']))
        elements.append(Paragraph(vendor_data.get('name', ''), styles['Normal']))
        if vendor_data.get('company_name'):
            elements.append(Paragraph(vendor_data.get('company_name', ''), styles['Normal']))
        elements.append(Spacer(1, 20))
        
        table_data = [['#', 'Item', 'Qty', 'Unit Price', 'Tax', 'Amount']]
        for idx, item in enumerate(items_data, 1):
            table_data.append([
                str(idx),
                item.get('product_name', ''),
                str(item.get('quantity', 0)),
                f"₹{item.get('unit_price', 0):,.2f}",
                f"₹{item.get('tax_amount', 0):,.2f}",
                f"₹{item.get('subtotal', 0) + item.get('tax_amount', 0):,.2f}"
            ])
        
        items_table = Table(table_data, colWidths=[30, 200, 50, 80, 70, 80])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 20))
        
        totals_data = [
            ['Subtotal:', f"₹{po_data.get('subtotal', 0):,.2f}"],
            ['Tax:', f"₹{po_data.get('tax_amount', 0):,.2f}"],
            ['Total:', f"₹{po_data.get('total_amount', 0):,.2f}"],
        ]
        
        totals_table = Table(totals_data, colWidths=[400, 100])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(totals_table)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    
    @staticmethod
    def generate_sales_order_pdf(so_data, customer_data, items_data):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
        
        elements = []
        
        elements.append(Paragraph("<b>SHIV FURNITURE</b>", styles['Title']))
        elements.append(Paragraph("Budget Accounting System", styles['Center']))
        elements.append(Spacer(1, 20))
        
        elements.append(Paragraph(f"<b>SALES ORDER</b>", styles['Title']))
        elements.append(Spacer(1, 10))
        
        so_info = [
            ['SO Number:', so_data.get('so_number', '')],
            ['Order Date:', so_data.get('order_date', '')],
            ['Delivery Date:', so_data.get('delivery_date', '')],
            ['Status:', so_data.get('status', '').upper()],
        ]
        
        info_table = Table(so_info, colWidths=[100, 200])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        elements.append(Paragraph("<b>Customer:</b>", styles['Normal']))
        elements.append(Paragraph(customer_data.get('name', ''), styles['Normal']))
        elements.append(Spacer(1, 20))
        
        table_data = [['#', 'Item', 'Qty', 'Unit Price', 'Tax', 'Amount']]
        for idx, item in enumerate(items_data, 1):
            table_data.append([
                str(idx),
                item.get('product_name', ''),
                str(item.get('quantity', 0)),
                f"₹{item.get('unit_price', 0):,.2f}",
                f"₹{item.get('tax_amount', 0):,.2f}",
                f"₹{item.get('subtotal', 0) + item.get('tax_amount', 0):,.2f}"
            ])
        
        items_table = Table(table_data, colWidths=[30, 200, 50, 80, 70, 80])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 20))
        
        totals_data = [
            ['Subtotal:', f"₹{so_data.get('subtotal', 0):,.2f}"],
            ['Tax:', f"₹{so_data.get('tax_amount', 0):,.2f}"],
            ['Discount:', f"₹{so_data.get('discount_amount', 0):,.2f}"],
            ['Total:', f"₹{so_data.get('total_amount', 0):,.2f}"],
        ]
        
        totals_table = Table(totals_data, colWidths=[400, 100])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(totals_table)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
    
    @staticmethod
    def generate_vendor_bill_pdf(bill_data, vendor_data, items_data):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
        
        elements = []
        
        elements.append(Paragraph("<b>SHIV FURNITURE</b>", styles['Title']))
        elements.append(Paragraph("Budget Accounting System", styles['Center']))
        elements.append(Spacer(1, 20))
        
        elements.append(Paragraph(f"<b>VENDOR BILL</b>", styles['Title']))
        elements.append(Spacer(1, 10))
        
        bill_info = [
            ['Bill Number:', bill_data.get('bill_number', '')],
            ['Vendor Bill #:', bill_data.get('vendor_bill_number', '')],
            ['Bill Date:', bill_data.get('bill_date', '')],
            ['Due Date:', bill_data.get('due_date', '')],
            ['Payment Status:', bill_data.get('payment_status', '').upper()],
        ]
        
        info_table = Table(bill_info, colWidths=[100, 200])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 20))
        
        elements.append(Paragraph("<b>Vendor:</b>", styles['Normal']))
        elements.append(Paragraph(vendor_data.get('name', ''), styles['Normal']))
        elements.append(Spacer(1, 20))
        
        table_data = [['#', 'Item', 'Qty', 'Unit Price', 'Tax', 'Amount']]
        for idx, item in enumerate(items_data, 1):
            table_data.append([
                str(idx),
                item.get('product_name', ''),
                str(item.get('quantity', 0)),
                f"₹{item.get('unit_price', 0):,.2f}",
                f"₹{item.get('tax_amount', 0):,.2f}",
                f"₹{item.get('subtotal', 0) + item.get('tax_amount', 0):,.2f}"
            ])
        
        items_table = Table(table_data, colWidths=[30, 200, 50, 80, 70, 80])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 20))
        
        totals_data = [
            ['Subtotal:', f"₹{bill_data.get('subtotal', 0):,.2f}"],
            ['Tax:', f"₹{bill_data.get('tax_amount', 0):,.2f}"],
            ['Total:', f"₹{bill_data.get('total_amount', 0):,.2f}"],
            ['Amount Paid:', f"₹{bill_data.get('amount_paid', 0):,.2f}"],
            ['Amount Due:', f"₹{bill_data.get('amount_due', 0):,.2f}"],
        ]
        
        totals_table = Table(totals_data, colWidths=[400, 100])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(totals_table)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
