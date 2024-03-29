# -*- coding: utf-8 -*-

from aenum import NamedTuple
from datetime import datetime
from io import BytesIO
# from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Flowable
from reportlab.platypus import SimpleDocTemplate, Table, Flowable, Paragraph, CellStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
TA_LEFT, TA_CENTER, TA_RIGHT

from openerp import pooler
from openerp.osv import fields
from openerp.report.interface import report_int
from openerp.report.render import render

from openerplib.dates import DEFAULT_SERVER_DATE_FORMAT as D_FORMAT


class external_pdf(render):
    #
    def __init__(self, pdf):
        render.__init__(self)
        self.pdf = pdf
        self.output_type='pdf'
    #
    def _render(self):
        return self.pdf


class report_spec_sheet(report_int):

    def create(self, cr, uid, ids, datas, context=None):
        if context is None:
            context = {}

        preship_sample = pooler.get_pool(cr.dbname).get('wholeherb_integration.preship_sample')
        preship_sample_report = pooler.get_pool(cr.dbname).get('wholeherb_integration.preship_sample.report')

        psr = preship_sample_report.browse(cr, uid, ids[0], context=context)
        domain = []
        if psr.approved:
            domain.append(('approved','=','yes'))
        if psr.rejected:
            domain.append(('approved','=','no'))
        if psr.rnd_use:
            domain.append(('rnd_use','=',True))
        if psr.start_date:
            domain.append(('date_recd','>=',psr.start_date))
        if psr.end_date:
            domain.append(('date_recd','<=',psr.end_date))
        if psr.start_prod:
            domain.append(('product_name','>=',psr.start_prod))
        if psr.end_prod:
            domain.append(('product_name','<=',psr.end_prod))
        if psr.start_supp:
            domain.append(('supplier_name','>=',psr.start_supp))
        if psr.end_supp:
            domain.append(('supplier_name','<=',psr.end_supp))
        sample_ids = preship_sample.search(cr, uid, domain, context=context)
        samples = preship_sample.browse(cr, uid, sample_ids, context=context)
        records = {}
        if psr.sort == 'date_prod':
            for s in samples:
                if s.date_recd:
                    date = datetime.strptime(s.date_recd, D_FORMAT)
                    group = date.strftime('%Y %m'), date.strftime('%B %Y')
                else:
                    group = '', '<date missing>'
                sort_key = s.date_recd, s.product_name, s.lot_no
                records.setdefault(group, []).append((sort_key, PreshipSample(s)))
        elif psr.sort == 'supp_prod':
            for s in samples:
                group = (s.supplier_name or '').lower(), s.supplier_name or ''
                sort_key = (s.product_name or '').lower(), s.lot_no
                records.setdefault(group, []).append((sort_key, PreshipSample(s)))
        elif psr.sort == 'prod_date':
            for s in samples:
                group = (s.product_name or '').lower(), s.product_name or ''
                sort_key = s.date_recd, s.lot_no
                records.setdefault(group, []).append((sort_key, PreshipSample(s)))
        else:
            raise ValueError('unknow sort option: %r' % psr.sort)

        # create document
        pdf_io = BytesIO()
        doc = SimpleDocTemplate(
                pdf_io,
                topMargin = 1.125*inch,
                rightMargin = 0.5*inch,
                bottomMargin = 0.75*inch,
                leftMargin = 0.5*inch,
                showBoundary=0,
                pagesize=(8.5*inch, 11*inch),
                author='Whole Herb Company',
                title='Pre-ship samples by %s' % psr.sort,
                subject='Pre-ship Samples',
            )
        doc.today = datetime.strptime(fields.date.today(preship_sample, cr, localtime=True), D_FORMAT)
        doc.last_entry = None
        flowables = [
                ]
        for (group, display), samples in sorted(records.items()):
            samples.sort()
            rows = []
            for k, s in samples:
                rows.append([ProductEntry(s, sort=psr.sort, doc=doc)])
            flowables.append(Table(
                    [[Paragraph(display, styles['Request'])]] + rows,
                    colWidths=7.5*inch,
                    cellStyles=[[productCellStyle]] * (len(samples)+1),
                    repeatRows=1,
                    spaceAfter=0.25*inch,
                    ))
                    
        on_page = page_headers[psr.sort]
        doc.build(flowables, onFirstPage=on_page, onLaterPages=on_page)

        self.obj = external_pdf(pdf_io.getvalue())
        self.obj.render()
        return (self.obj.pdf, 'pdf')
report_spec_sheet('report.wholeherb_integration.preship_sample')


styles = getSampleStyleSheet()
styles.add(ParagraphStyle('Request', fontName='Times-Bold', fontSize=14, leading=14, alignment=TA_LEFT))

productCellStyle = CellStyle('ProductCell')
productCellStyle.leftPadding = 0
productCellStyle.rightPadding = 0


class ProductEntry(Flowable):
    #
    def __init__(self, sample, sort=None, doc=None):
        Flowable.__init__(self)
        self.product = sample.product
        self.supplier = sample.supplier
        self.received = sample.date
        self.lot_no = sample.lot_no
        self.sales_rep = sample.salesrep
        self.customer = sample.customer
        self.rnd = sample.rnd_use
        self.approved = sample.approved
        self.width = 7.5*inch
        self.height = 0.6*inch
        self.sort = sort
        self.doc = doc
        if sort.startswith('prod_'):
            self.product = ''
        elif sort.startswith('supp_'):
            self.supplier = ''
    #
    def __repr__(self):
        return "ProductEntry(product=%r, lot_no=%r)" % (self.product, self.lot_no)
    #
    def draw(self):
        if self.sort.startswith('supp_'):
            # only show product name if first in series, or beginning of page
            if self.doc.last_entry == self.product:
                self.product = ''
            else:
                self.doc.last_entry = self.product
        #
        def check_box(x, y, text, is_set):
            c.rect(x, y, 0.125*inch, 0.125*inch)
            c.drawString(x+0.1875*inch, y, text)
            if is_set:
                c.line(x, y, x+0.125*inch, y+0.125*inch)
                c.line(x, y+0.125*inch, x+0.125*inch, y)
        #
        c = self.canv
        # top line
        if self.height > 0.5*inch:
            c.setFont('Times-Bold', 12)
            c.drawString(0.25*inch, 0.45*inch, self.product)
            c.setFont('Times-Roman', 10)
            c.drawString(3.75*inch, 0.45*inch, self.supplier)
        # middle line
        c.setFont('Times-Roman', 10)
        c.drawString(0.5*inch, 0.275*inch, self.received)
        c.drawString(1.5*inch, 0.275*inch, self.lot_no)
        c.drawString(4.75*inch, 0.275*inch, self.sales_rep)
        c.drawRightString(7.5*inch, 0.275*inch, self.customer)
        # bottom line
        check_box(0.5*inch, 0.05*inch, "R/D Use Only!", self.rnd)
        check_box(1.75*inch, 0.05*inch, "Approved Preship Sample", self.approved)
        # grid line
        c.line(0.5*inch, 0*inch, 7.5*inch, 0*inch)

def onPageByDate(c, doc):
    doc.last_entry = None
    c.saveState()
    c.setFont('Times-Bold', 20)
    c.line(0.5*inch, 10.5*inch, 8.0*inch, 10.5*inch)
    c.drawString(0.5*inch, 10.25*inch, "Pre-ship samples by date received")
    c.line(0.5*inch, 10.125*inch, 8.0*inch, 10.125*inch)
    c.setFont('Times-Roman', 10)
    c.drawString(0.5*inch, 9.875*inch, "Month")
    c.drawString(1.0*inch, 9.875*inch, "Recv'd")
    c.drawString(2.0*inch, 9.875*inch, "WHC Lot#")
    c.drawString(4.25*inch, 9.875*inch, "Supplier")
    c.drawString(5.25*inch, 9.875*inch, "WHC Sales Rep")
    c.drawRightString(8.0*inch, 9.875*inch, "WHC Customer")
    c.line(0.5*inch, 9.85*inch, 8.0*inch, 9.85*inch)
    c.drawString(0.5*inch, 0.5*inch, doc.today.strftime('%A, %B %d, %Y'))
    c.restoreState()

def onPageByProduct(c, doc):
    doc.last_entry = None
    c.saveState()
    c.setFont('Times-Bold', 20)
    c.line(0.5*inch, 10.5*inch, 8.0*inch, 10.5*inch)
    c.drawString(0.5*inch, 10.25*inch, "Pre-ship samples by product")
    c.line(0.5*inch, 10.125*inch, 8.0*inch, 10.125*inch)
    c.setFont('Times-Roman', 10)
    c.drawString(0.5*inch, 9.875*inch, "Product")
    c.drawString(1.0*inch, 9.875*inch, "Recv'd")
    c.drawString(2.0*inch, 9.875*inch, "WHC Lot#")
    c.drawString(4.25*inch, 9.875*inch, "Supplier")
    c.drawString(5.25*inch, 9.875*inch, "WHC Sales Rep")
    c.drawRightString(8.0*inch, 9.875*inch, "WHC Customer")
    c.line(0.5*inch, 9.85*inch, 8.0*inch, 9.85*inch)
    c.drawString(0.5*inch, 0.5*inch, doc.today.strftime('%A, %B %d, %Y'))
    c.restoreState()

def onPageBySupplier(c, doc):
    doc.last_entry = None
    c.saveState()
    c.setFont('Times-Bold', 20)
    c.line(0.5*inch, 10.5*inch, 8.0*inch, 10.5*inch)
    c.drawString(0.5*inch, 10.25*inch, "Pre-ship samples by supplier")
    c.line(0.5*inch, 10.125*inch, 8.0*inch, 10.125*inch)
    c.setFont('Times-Roman', 10)
    c.drawString(0.5*inch, 9.875*inch, "Supplier")
    c.drawString(1.0*inch, 9.875*inch, "Recv'd")
    c.drawString(2.0*inch, 9.875*inch, "WHC Lot#")
    c.drawString(5.25*inch, 9.875*inch, "WHC Sales Rep")
    c.drawRightString(8.0*inch, 9.875*inch, "WHC Customer")
    c.line(0.5*inch, 9.85*inch, 8.0*inch, 9.85*inch)
    c.drawString(0.5*inch, 0.5*inch, doc.today.strftime('%A, %B %d, %Y'))
    c.restoreState()

page_headers = {
        'date_prod': onPageByDate,
        'prod_date': onPageByProduct,
        'supp_prod': onPageBySupplier,
        }

class PreshipSample(NamedTuple):
    #
    product = 0
    lot_no = 1
    date = 2
    rnd_use = 3
    approved = 4
    supplier = 5
    salesrep = 6
    customer = 7
    #
    def __new__(cls, ps):
        product = ps.product_name or ''
        lot_no = ps.lot_no or ''
        date = ps.date_recd or ''
        rnd = ps.rnd_use
        approved = ps.approved
        supplier = ps.supplier_name or ''
        salesrep = ps.salesrep_name or ''
        customer = ps.customer_name or ''
        return tuple.__new__(cls, (product, lot_no, date, rnd, approved, supplier, salesrep, customer))

