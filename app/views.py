from django.shortcuts import render, redirect
from django.http import HttpResponse
from .forms import *
from .models import *
import pandas as pd

from .optimization.funcs import optimize_cutting

from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from datetime import datetime
from io import BytesIO

# Create your views here.

def home(request):

    if request.method == 'POST':

        form = DemandUploadForm(request.POST, request.FILES)
        if form.is_valid():

            # Reading the available stock lengths
            file = request.FILES['file']
            stock_lengths_str = form.cleaned_data['stock_lengths']

            # Processing uploaded stock lengths
            stock_lengths = [int(s.strip()) for s in stock_lengths_str.split(',') if s.strip().isdigit()]

            # Deleting existing stock lengths
            StockLength.objects.all().delete()

            # Adding new stock lengths to the database
            for length in stock_lengths:
                StockLength.objects.create(
                    length=length
                )

            # Reading the demand lengths file. Expecting - 'length, quantity, code'
            df = pd.read_excel(file)


            # Deleting old demand lengths
            DemandLength.objects.all().delete()

            # Adding new demand lengths to database
            for _, row in df.iterrows():
                DemandLength.objects.create(
                    length=row['length'],
                    qty=row['qty'],
                    code=row['code']
                )

            request.session['results'] = False
            request.session['stock_summary'] = False
            request.session['total_waste'] = False

        return redirect('home')
    
    else:

        form = DemandUploadForm()
        stock_lengths = StockLength.objects.all()
        demnad_lengths = DemandLength.objects.all()

        results = request.session.get('results', [])
        stock_summary = request.session.get('stock_summary', [])
        total_waste = request.session.get('total_waste', 0)

        context = {
            'form': form,
            'stock_lengths': stock_lengths,
            'demand_lengths': demnad_lengths,
            'results': results,
            'stock_summary': stock_summary,
            'total_waste': total_waste,
        }


        return render(request, 'app/home.html', context)
    


# Optimization Trigger function

def optimize(request):
    results, stock_summary, total_waste = optimize_cutting()
    request.session['results'] = results
    request.session['stock_summary'] = stock_summary
    request.session['total_waste'] = total_waste
    return redirect('home')



# PDF Download trigger function

def download_cutting_pdf(request):
    result_data = request.session.get('results', [])
    total_waste = request.session.get('total_waste', 0)
    total_bars = request.session.get('stock_summary', 0)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=40, rightMargin=40, topMargin=80, bottomMargin=50)

    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph("Optimized Cutting Plan", styles["Title"]))
    elements.append(Paragraph(f"Date: {datetime.now().strftime('%d-%m-%Y')}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    # Table header
    data = [["Sr. No.", "Stock Length (mm)", "Cut Pattern -> Code-Length: (Number of Cuts)", "Bar Count", "Wastage (mm)"]]

    for i, entry in enumerate(result_data):
        cuts_str = ", ".join([f"{key}: ({entry['pattern'][key]})" for key in entry["pattern"].keys()])
        data.append([
            i+1, 
            entry["stock_length"],
            Paragraph(cuts_str, styles["Normal"]),
            entry['count'],
            entry["waste"]
        ])

    # Define table style
    table = Table(data, colWidths=[50, 90, 200, 80, 80])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
        ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))

    # Summary

    summary_data = [['Sr. No.', 'Stock Length (mm)', 'Bars Required', 'Total Waste (mm)']]

    for i, entry in enumerate(total_bars):
        summary_data.append([
            i+1,
            entry['stock_length'],
            entry['used_count'],
            entry['waste']
        ])

    table2 = Table(summary_data, colWidths=[60, 145, 145, 145])
    table2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
        ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
    ]))


    elements.append(table2)
    elements.append(Spacer(1, 20))

    elements.append(Paragraph(f"<b>Total Wastage:</b> {total_waste} mm", styles["Normal"]))

    # Add page number on each page
    def add_page_number(canvas, doc):
        canvas.saveState()
        page_number_text = f"Page {doc.page}"
        canvas.setFont("Helvetica", 9)
        canvas.drawCentredString(A4[0] / 2.0, 30, page_number_text)
        canvas.restoreState()

    # Build PDF
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)

    # Return response
    buffer.seek(0)
    return HttpResponse(buffer, content_type="application/pdf", headers={
        'Content-Disposition': 'attachment; filename="cutting_plan.pdf"'
    })