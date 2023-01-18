#!/usr/bin/python3
"""\
Manage FIS order confirmations, open order invoices, and availability in OpenERP.
"""


# imports & config

from __future__ import print_function
from antipathy import Path
from dbf import Date
from logging import INFO, getLogger, Formatter, handlers
from re import match as re_match
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from time import ctime

import antipathy, dbf, reportlab, scription

from scription import *

# keep pyflakes happy
TA_RIGHT, antipathy, dbf, reportlab, scription

version = "2022.1.12 [source: 2.243:/opt/openerp/openerp/wholeherb_integtration/scripts/fnx_fis_orders.source]"


# API

@Script(
        )
def main():
    global WholeHerbLogo, logger
    WholeHerbLogo = Path("/home/emile/berje_logo.png")
    if not WholeHerbLogo.exists():
        WholeHerbLogo = 'berje_logo.png'

    logger = getLogger()
    logger.setLevel(INFO)
    handler = handlers.TimedRotatingFileHandler(
            '/var/log/fnx_fis_orders.log',
            when='midnight',
            backupCount=30,
            )
    formatter = Formatter('%(asctime)s %(funcName)-25s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info("running command %r", script_command_line)

@Command(
        )
def export_invoices():
    """
    copy open invoice pdfs from 2.2 to 2.243
    """
    global _logger
    _logger = getLogger('export_invoices')
    for top_dir, cust_dirs, files in Path('/usr/FIS_Invoices').walk():
        break
    for dir in cust_dirs:
        target_dir = top_dir/dir
        for path, dirs, files in target_dir.walk():
            found = []
            for fn in files:
                if match(open_invoice, fn):
                    cust, invoice, date, po_number = match.groups()
                    _logger.info('processing customer %r, invoice %r, date %r, po %r', cust, invoice, date, po_number)
                    try:
                        date = Date.strptime(date, '%Y%m%d')
                    except ValueError:
                        _logger.error('invalid date %r', date)
                        continue
                    found.append(path/fn)
            if found:
                Execute('rsync %s 192.168.2.243:/home/imports/open_invoices/' % ' '.join(found))
    Execute('ssh root@192.168.2.243 touch /home/imports/open_invoices/done')
    _logger.info('done')

@Command(
        )
def import_invoices():
    """
    add open invoices to OpenERP; remove closed invoices and matching order confirmations
    """
    global _logger
    _logger = getLogger('import_invoices')
    source = Path('/home/imports/open_invoices')
    archive = source/'archive'
    # if export_invoices finished, check for deleted invoices
    if source.exists('done'):
        _logger.info('checking for deleted invoices')
        source.unlink('done')
        for fn in archive.listdir():
            if not fn.endswith('.pdf'):
                # garbage file
                continue
            if source.exists(fn):
                # invoice is still open
                continue
            _logger.info('removing %s', fn)
            try:
                cust, invoice, date, po = match(open_invoice, fn).groups()
            except TypeError:
                _logger.error('unable to parse file name %r', fn)
                error('unable to parse file name %r' % (fn, ))
                continue
            nfn = create_invoice_filename(cust, invoice, date, po)
            rm = Execute('/usr/local/bin/fnxfs rm res.partner/xml_id=%s/open_invoices/%s' % (cust, nfn))
            if rm.returncode == Exit.IoError:
                _logger.error('unable to remove %r from OpenERP', nfn)
                _logger.error(rm.stderr)
                error('unable to remove %r from OpenERP' % (nfn, ))
            else:
                archive.unlink(fn)
    # copy invoices into OpenERP file system
    _logger.info('looking for invoices')
    for fqn in source.glob('*.pdf'):
        try:
            cust, invoice, date, po = match(open_invoice, fqn.filename).groups()
            _logger.info('processing customer %r, invoice %r, date %r, po 5r', cust, invoice, date, po)
        except TypeError:
            _logger.error('unable to parse file name %r', fqn.filename)
            error('unable to parse file name %r' % (fqn.filename, ))
            continue
        nfn = create_invoice_filename(cust, invoice, date, po)
        cp = Execute('/usr/local/bin/fnxfs cp %s res.partner/xml_id=%s/open_invoices/%s' % (fqn, cust, nfn))
        if cp.returncode:
            _logger.error('unable to copy %s into OpenERP as %s', fqn, nfn)
            _logger.error(cp.stderr)
            error('unable to copy %s into OpenERP as %s' % (fqn, nfn))
            continue
        fqn.move(archive)
        ocfn = create_confirmation_filename(invoice)
        rm = Execute('/usr/local/bin/fnxfs rm res.partner/xml_id=%s/open_invoices/%s' % (cust, ocfn))
        if rm.returncode == Exit.IoError:
            _logger.error('unable to remove %r from OpenERP', ocfn)
            _logger.error(rm.stderr)
            error('unable to remove %r from OpenERP' % (ocfn, ))
    _logger.info('done')

@Command(
        )
def import_order_confs():
    """
    add order confirmations to OpenERP
    """
    # /usr/local/bin/import_order_confs.sh
    # #!/bin/bash
    # cd /home/imports/order_confs
    # /bin/mv *.pdf archive/
    # for iii in $(find /home/imports/order_confs/archive/ -iname "*.pdf"  \
    #                         -type f -newer /home/imports/order_confs/archive/lastsweep)
    #     do
    #         CUST=$(echo $iii | cut -c35-40);
    #         ORDER=$(echo $iii | cut -c42-47);
    #         echo $iii $CUST  $ORDER >> /var/log/import_order_confs.log;
    #         cp $iii archive/$ORDER.pdf;
    #         echo VIRTUAL_ENV=/opt/openerp /usr/local/bin/fnxfs cp /home/imports/order_confs/archive/$ORDER.pdf res.partner/xml_id=$CUST/order_confirmations >> /var/log/import_order_confs.log;
    #         VIRTUAL_ENV=/opt/openerp /usr/local/bin/fnxfs cp /home/imports/order_confs/archive/$ORDER.pdf res.partner/xml_id=$CUST/order_confirmations;
    #         rm $ORDER.pdf;
    #     done
    # touch /home/imports/order_confs/archive/lastsweep
    #
    global _logger
    _logger = getLogger('import_confirmations')
    source = Path('/home/imports/order_confs')
    archive = source/'archive'
    review = source/'errors'
    for fqn in source.glob('*.pdf'):
        try:
            cust, invoice = match(order_conf, fqn.filename).groups()
            _logger.info('processing customer %r confirmation %r', cust, invoice)
        except (TypeError, AttributeError):
            _logger.error('problem with file name: %r', fqn.filename, )
            error('problem with file name: %r' % (fqn.filename, ))
            continue
        nfn = create_confirmation_filename(invoice)
        cp = Execute('/usr/local/bin/fnxfs cp %s res.partner/xml_id=%s/order_confirmations/%s' % (fqn, cust, nfn))
        if cp.returncode:
            _logger.error('unable to copy %s into OpenERP as %s', fqn, nfn)
            _logger.error(cp.stderr)
            error('unable to copy %s into OpenERP as %s' % (fqn, nfn))
	    fqn.move(review)
        else:
            fqn.move(archive)
    _logger.info('done')

@Command(
        order=Spec("order number to process", ),
        source=Spec("order file location", OPTION, force_default="/mnt/linuxworkstationmaster/confs/", type=Path),
        dest=Spec("pdf file location", OPTION, force_default="/mnt/linuxworkstationmaster/pdfs/", type=Path),
        )
def create_order_conf(order, source, dest):
    """
    Create pdf version of order confirmation.
    """
    global _logger
    _logger = getLogger('create_order_conf')
    _logger.info('processing %r', order)
    if order == 'test':
        dst = 'test.pdf'
        order_conf = OrderConf(order_conf_test_data[:55])
    else:
        src = source / order + '.dat'
        dst = dest / order + '.pdf'
        try:
            order_conf = OrderConf.from_file(src)
        except ValueError:
            return Exit.DataError
    for line in order_conf.line_items:
        line1, line2 = line[1].split('\n')
        if line2 == '-- continued --':
            line[1] = [Paragraph(line2, styles['continued'])]
        else:
            line[1] = [Paragraph(line1, styles['Item'])]
            if line2:
                line[1].append(Paragraph(line2, styles['Latin']))

    doc = SimpleDocTemplate(
            dst,
            topMargin = 2.0*inch,
            rightMargin = 0.5*inch,
            bottomMargin = 1.25*inch,
            leftMargin = 0.5*inch,
            showBoundary=0,
            pagesize=(8.5*inch, 11*inch),
            author='FIS',
            title='Whole Herb Order %s' % order,
            subject='Confirmation Request as of %s' % order_conf.date,
            keywords=order_conf.keywords,
            )
    flowables = []
    flowables.append(Paragraph(
            "<b>In our efforts to ensure that your order is processed correctly, please review the following "
            "product and shipping information.  Any changes to this order must be emailed or faxed to "
            "your sales representative prior to shipment.</b>"
            ,
            styles['Request'],
            ))
    flowables.append(Spacer(1, 0.33*inch))
    flowables.append(Table(
            list(zip(order_conf.bill_to, order_conf.ship_to)),
            colWidths=[4.0*inch, 3.5*inch],
            rowHeights=4*[0.165*inch],
            style=addressTableStyle,
            ))
    flowables.append(Spacer(1, 0.25*inch))
    flowables.append(Table(
            [['Ship Date', 'Ship Via', 'P.O.#', 'Terms', 'Reference'], order_conf.hdr_info],
            colWidths=[1.0*inch, 3.0*inch, 1.0*inch, 1.25*inch, 1.25*inch],
            style=orderTableStyle,
            ))
    flowables.append(Spacer(1, 0.125*inch))
    flowables.append(Table(
            [['Item', 'Item Description', 'Quantity', 'Price per LB', 'Total']] + order_conf.line_items,
            colWidths=[1.0*inch, 3.0*inch, 1.0*inch, 1.25*inch, 1.25*inch],
            rowHeights=(len(order_conf.line_items)+1) * [0.5*inch],
            style=itemTableStyle,
            repeatRows=1,
            ))
    doc.build(flowables, onFirstPage=page_template, onLaterPages=page_template)
    _logger.info('done')


# styles

FontSet = { 'Hdg'    : 'Times-Bold',
            'SubHdg' : 'Times-Bold',
            'Address': 'Times-Bold',
            'Ftr'    : 'Helvetica-BoldOblique',
            'Text'   : 'Times-Roman',
            'Latin'  : 'Times-Italic',
            }

styles = getSampleStyleSheet()
styles.add(ParagraphStyle('Request', fontName='Times-Bold', fontSize=14, leading=14, alignment=TA_CENTER))
styles.add(ParagraphStyle('Item', fontName='Times-Bold', fontSize=12, leading=15, alignment=TA_LEFT))
styles.add(ParagraphStyle('Latin', fontName='Times-Italic', fontSize=12, leading=15, alignment=TA_LEFT))
styles.add(ParagraphStyle('continued', fontName='Times-BoldItalic', fontSize=10, leading=10, alignment=TA_LEFT))

addressTableStyle = TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONT', (0,0), (-1,-1), FontSet['Address'], 11, 13),
        ])

orderTableStyle = TableStyle([
        ('ALIGN', (0,0), (1,-1), 'LEFT'),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('FONT', (0,0), (-1,0), FontSet['Text'], 10, 12),
        ('FONT', (0,1), (-1,-1), FontSet['SubHdg'], 12, 15),
        ])

itemTableStyle = TableStyle([
        ('ALIGN', (0,0), (1,-1), 'LEFT'),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('FONT', (0,0), (-1,0), FontSet['Text'], 10, 12),
        ('FONT', (0,1), (-1,-1), FontSet['SubHdg'], 12, 15),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ])

# helpers


open_invoice = r'(\d{6})_(\d+)_(\d{8})_(PO.+)\.pdf$'
order_conf = r'(\d+)-(\d+)\.pdf$'

match = Var(lambda needle, haystack: re_match(needle, haystack))

def create_confirmation_filename(invoice):
    fn = 'Conf_%s.pdf' % (invoice, )
    return fn

def create_invoice_filename(cust, invoice, date, po):
    date = '%s-%s-%s' % (date[:4], date[4:6], date[6:])
    if po.startswith('PO'):
        po = po[2:]
    po = po.lstrip('-_')
    fn = 'Inv_%s-PO_%s-Date_%s.pdf' % (invoice, po, date)
    return fn

def rise(*fields):
    #fields = _fields(args)
    data = []
    empty = []
    for possible in fields:
        if possible:
            data.append(possible)
        else:
            empty.append(possible)
    results = data + empty
    return results

class OrderConf(object):
    """
    bill-to, ship-to, and items on order confirmation
    """

    def __init__(self, raw_data):
        '''
         ['ANAHUAC', '', '7522 SCOUT AVE.', 'BELL GARDENS, CA 90201', 
          'ANAHUAC', '', '7522 SCOUT AVE.', 'BELL GARDENS, CA 90201', 
          '07-12-22', 'RATE SHOPPER', 'EMAIL', 'NET 30', '118431', 
          'FLA10000', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
          'PAL13290', 'PALO AZUL', '105', '3.17', '332.85', '', 
          'EPO10000', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
          'COR20000', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
          '', '', '', '', '', '', 
          (...10x...)
          '', '', '', '', '', '']
        '''
        #Break out BillTo, ShipTo and LineItems
        data = raw_data
        self.bill_to = rise(*data[0:4])
        self.ship_to = rise(*data[4:8])
        self.hdr_info = data[8:13]
        self.date = data[8]
        keywords = set()
        line_items = []
        startPos = 13
        count = 0
        overflow = 10
        while len(data) > startPos:
            line = data[startPos:startPos+6]
            print(repr(line), verbose=2)
            if any(line):
                count += 1
                if count == overflow:
                    line_items.insert(count-2, ['','\n-- continued --','','',''])
                    overflow += 14
                keywords.add(line[0])
                # Convert the FIS Description to title case and latin to lower case
                line[1] = ('%s\n%s' % (line[1].title(), line[5].lower()))
                line_items.append(line[:5])
            startPos += 6
        self.keywords = ["per %s:" % self.date] + list(keywords)
        self.line_items = line_items
        self.data = data

    @classmethod
    def from_file(cls, path):
        # validate file name
        if not path.filename[:6].isdigit() or len(path.filename) != 10:
            _logger.error('invalid filename %r', path.filename)
            raise ValueError('invalid filename %r' % path.filename)
        raw_data = [
                line.replace('"','').strip()
                for line in open(path).readlines()
                ]
        if len(raw_data) < 13:
            _logger.error('missing data or empty file')
            raise ValueError('missing data or empty file')
        print(repr(raw_data), verbose=2)
        return cls(raw_data)

# reportlab config

def page_template(c, doc):
    c.saveState()
    c.drawImage(WholeHerbLogo, 3.0*inch, 9.5*inch, width=2.5*inch, height=1.25*inch, mask=None)
    c.setFont(FontSet['SubHdg'], 24)
    c.drawCentredString(4.25*inch, 9.125*inch, "Order Confirmation")
    c.setFont(FontSet['Ftr'], 10)  #  was 9 and below was .55 .40 .25
    c.drawCentredString(4.25*inch, 1.22 * inch, "Whole Herb Company")
    c.drawCentredString(4.25*inch, 1.08 * inch, "19800 8th Street East   Sonoma, CA 95476")
    c.drawCentredString(4.25*inch, 0.94 * inch, "Phone: 707-935-1077   Fax: 707-935-3447")
    c.drawCentredString(4.25*inch, 0.80 * inch, "www.wholeherbcompany.com")
    c.drawCentredString(4.25*inch, 0.66 * inch, "We do not accept any returns without prior return authorization. Claims for shortages or allowances must be")
    c.drawCentredString(4.25*inch, 0.54 * inch, "made in writing within ten days from the delivery date. All raw materials are sold for further processing.")
    c.setFont(FontSet['SubHdg'], 4)
    c.drawCentredString(8.0*inch, 0.25*inch, "%s" % ctime())
    c.restoreState()

order_conf_test_data = [
        'ANAHUAC', '', '7522 SCOUT AVE.', 'BELL GARDENS, CA 90201', 
        'ANAHUAC', '2257 BRAVE ST.', 'BELL GARDENS, CA 90201', 'UNITED STATES',
        '07-12-22', 'RATE SHOPPER', 'EMAIL', 'NET 30', '118431', 
        'FLA10000', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13290', 'PALO AZUL', '105', '3.17', '332.85', '', 
        'EPO10000', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'COR20000', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
        'FLA10000', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13290', 'PALO AZUL', '105', '3.17', '332.85', '', 
        'EPO10000', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'COR20000', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
        'FLA10000', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13290', 'PALO AZUL', '105', '3.17', '332.85', '', 
        'EPO10000', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'COR20000', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
        'FLA10000', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13290', 'PALO AZUL', '105', '3.17', '332.85', '', 
        'EPO10000', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'COR20000', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
        'FLA10000', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13290', 'PALO AZUL', '105', '3.17', '332.85', '', 
        'EPO10000', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'COR20000', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
        'FLA10000', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13290', 'PALO AZUL', '105', '3.17', '332.85', '', 
        'EPO10000', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'COR20000', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
        'FLA10000', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13290', 'PALO AZUL', '105', '3.17', '332.85', '', 
        'EPO10000', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'COR20000', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
        'FLA10000', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13290', 'PALO AZUL', '105', '3.17', '332.85', '', 
        'EPO10000', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'COR20000', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
        'FLA10000', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13290', 'PALO AZUL', '105', '3.17', '332.85', '', 
        'EPO10000', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        '', '', '', '', '', '', 
        '', '', '', '', '', '']



# do it

Run()
