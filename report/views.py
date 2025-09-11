import logging
from weasyprint import HTML
from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import get_template
import io
import qrcode
from barcode import Code128
from barcode.base import Barcode
from barcode.writer import SVGWriter
import base64
from PIL import Image

from invoice.models import Invoice, InvoiceItem
from setting.models import ShopDetails, ReportConfiguration
Barcode.default_writer_options["write_text"] = False

logger = logging.getLogger(__name__)


def get_print_count(num):
    return num // 2 if num % 2 == 0 else num // 2 + 1


# general pdf creation values for all data
def generatePdf(template_name, file_name, context, request, report_type="INVOICE"):
    # Get shop details
    shop_details = ShopDetails.objects.filter(is_active=True).first()
    context["shop_details"] = shop_details
    
    # Get report configuration
    report_config = ReportConfiguration.get_default_config(report_type)
    context["report_config"] = report_config
    
    template = get_template(f"report/{template_name}")
    html = template.render(context)

    # Insert barcode image into HTML using base64-encoded data URL
    if "qrcode" in context:
        barcode_data = context["qrcode"]
        html = html.replace(
            "{{ qrcode }}", f'<img src="data:image/png;base64, {barcode_data}"/>'
        )

    pdf_file = HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(
        presentational_hints=True
    )
    response = HttpResponse(pdf_file, content_type="application/pdf")
    response["Content-Disposition"] = f'filename="{file_name}.pdf"'
    response["pdfkit-dpi"] = "800"  # Set the DPI to 300
    return response


# create invoice page
def createInvoice(request, pk):
    template = "report/invoiceA5.html"

    invoice = Invoice.objects.get(id=pk)
    values = InvoiceItem.objects.filter(invoice__id=pk)

    # Get shop details and report configuration
    shop_details = ShopDetails.objects.filter(is_active=True).first()
    report_config = ReportConfiguration.get_default_config(ReportConfiguration.ReportType.INVOICE)
    
    context = {
        "values": values, 
        "details": invoice,
        "shop_details": shop_details,
        "report_config": report_config
    }

    # Generate QR code if enabled in config
    if report_config and report_config.show_qr_code and shop_details:
        try:
            # Create UPI payment QR code
            qr_data = f"upi://pay?pa={shop_details.phone_number}&pn={shop_details.shop_name}&am={invoice.amount}&tn=Invoice {invoice.invoice_number}&cu=INR"
            qr_code = qrcode.make(qr_data)
            image_bytes = io.BytesIO()
            qr_code.save(image_bytes, format="PNG")
            context["qrcode"] = base64.b64encode(image_bytes.getvalue()).decode()
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")

    return render(request, template, context)


# # create invoice page
# def estimateInvoice(request, pk):
#     template = "report/estimate_invoice.html"

#     invoice = BillRoom.objects.get(id=pk)
#     values = StockRoom.objects.filter(roomName__id=pk)

#     upi_details = UpiDetails.objects.all().first()
#     shop_details = ShopDetails.objects.all().first()
#     context = {"values": values, "details": invoice}

#     if upi_details:
#         try:
#             qr_data = f"upi://pay?pa={upi_details.upiId}&pn={shop_details.shopName}&am={invoice.amount}&tn=for bill no {invoice.id}&cu=INR"
#             qr_code = qrcode.make(qr_data)
#             image_bytes = io.BytesIO()
#             qr_code.save(image_bytes, format="PNG")
#             context["qrcode"] = image_bytes.getvalue()

#         except BaseException as e:
#             print(e)

#     context["shop_details"] = shop_details
#     return render(request, template, context)
#     # return generatePdf(template, 'invoice', context, request)
