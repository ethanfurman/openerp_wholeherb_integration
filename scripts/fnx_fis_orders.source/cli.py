"""
Manage FIS order confirmations, open order invoices, and availability in OpenERP.
"""


# imports & config

from __future__ import print_function
from aenum import NamedTuple
from antipathy import Path
from dbf import Date
from logging import INFO, getLogger, Formatter, handlers
from re import match as re_match
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
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
        log_file=Spec('log file', OPTION, force_default='/var/log/fnx_fis_orders.log'),
        )
def main(log_file):
    global WholeHerbLogo, logger
    WholeHerbLogo = Path("/home/emile/berje_logo.png")
    if not WholeHerbLogo.exists():
        WholeHerbLogo = 'PYZAPP/berje_logo.png'

    logger = getLogger()
    logger.setLevel(INFO)
    handler = handlers.TimedRotatingFileHandler(
            log_file,
            when='midnight',
            backupCount=30,
            )
    formatter = Formatter('%(asctime)s %(funcName)-25s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info("running command %r", script_command_name)

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
            fqn.move(review)
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
        which=Spec("which test data to use [1-3]", OPTION, choices=[1, 2, 3], type=int, force_default=1),
        )
def create_order_conf(order, source, dest, which):
    """
    Create pdf version of order confirmation.
    """
    global _logger
    _logger = getLogger('create_order_conf')
    _logger.info('processing %r', order)
    if order == 'test':
        dst = 'test.pdf'
        order_conf = OrderConf(order_conf_test_data[which-1])
    else:
        src = source / order + '.dat'
        if not src.exists():
            src = source / order + '.dzz'
            if not src.exists():
                abort("unable to find file %s" % src, Exit.DataError)
        dst = dest / order + '.pdf'
        try:
            order_conf = OrderConf.from_file(src)
        except ValueError:
            abort("problem converting '%s'" % src, Exit.DataError)
    table_items = []
    for li in order_conf.line_items:
        # line1, line2 = line[1].split('\n')
        # if line2 == '-- continued --':
        #     line[1] = [Paragraph(line2, styles['continued'])]
        # else:
        names = [Paragraph(li.name, styles['Item'])]
        if li.latin_name:
            names.append(Paragraph(li.latin_name, styles['Latin']))
        if li.notes:
            names.append(Paragraph(li.notes, styles['Note']))
        table_items.append([li.code, names, li.qty, li.price, li.total])

    doc = DocTemplate(
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
            [['Item', 'Item Description', 'Quantity', 'Price per LB', 'Total']] + table_items,
            colWidths=[1.0*inch, 3.0*inch, 1.0*inch, 1.25*inch, 1.25*inch],
            rowHeights=(len(order_conf.line_items)+1) * [None],
            style=itemTableStyle,
            repeatRows=1,
            ))
    if order_conf.notes:
        flowables.append(Spacer(1, 0.5*inch))
        notes = []
        notes.append(Paragraph('Notes:', styles['Item']))
        notes.append(Spacer(1, 0.125*inch))
        for n in order_conf.notes:
            notes.append(Paragraph(n, styles['Note']))
        flowables.append(KeepTogether(notes))
    doc.build(flowables)
    _logger.info('done')


# reportlab

class DocTemplate(SimpleDocTemplate):
    #
    def __fixed_elements(self, c, doc):
        c.saveState()
        c.drawImage(WholeHerbLogo, 3.0*inch, 9.5*inch, width=2.5*inch, height=1.25*inch, mask=None)
        c.setFont(FontSet['SubHdg'], 24)
        c.drawCentredString(4.25*inch, 9.125*inch, "Order Confirmation")
        c.setFont(FontSet['Ftr'], 10)  #  was 9 and below was .55 .40 .25
        c.drawCentredString(4.25*inch, 0.66 * inch, "We do not accept any returns without prior return authorization. Claims for shortages or allowances must be")
        c.drawCentredString(4.25*inch, 0.54 * inch, "made in writing within ten days from the delivery date. All raw materials are sold for further processing.")
        c.setFont(FontSet['SubHdg'], 4)
        c.drawCentredString(8.0*inch, 0.25*inch, "%s" % ctime())
        c.restoreState()
    onFirstPage = onLaterPages = __fixed_elements

    def afterInit(self):
        def _onProgress(typ, value):
            self._leaf_state[typ] = value
        self._onProgress = _onProgress
        self._leaf_state = {}

    def afterPage(self):
        _logger.info('_leaf_state: %r', self._leaf_state)
        if self._leaf_state['PROGRESS'] < self._leaf_state['SIZE_EST']:
            self.draw_continued(self.canv, self)
        else:
            self.draw_address(self.canv, self)

    def draw_address(self, c, doc):
        c.saveState()
        c.setFont(FontSet['Ftr'], 10)  #  was 9 and below was .55 .40 .25
        c.drawCentredString(4.25*inch, 1.22 * inch, "Whole Herb Company")
        c.drawCentredString(4.25*inch, 1.08 * inch, "19800 8th Street East   Sonoma, CA 95476")
        c.drawCentredString(4.25*inch, 0.94 * inch, "Phone: 707-935-1077   Fax: 707-935-3447")
        c.drawCentredString(4.25*inch, 0.80 * inch, "www.wholeherbcompany.com")
        c.restoreState()

    def draw_continued(self, c, doc):
        c.saveState()
        c.setFont(FontSet['Ftr'], 10)
        c.drawCentredString(4.25*inch, 1.08 * inch, "-- continued on next page --")
        c.restoreState()


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
styles.add(ParagraphStyle('Note', fontName='Times-Bold', fontSize=10, leading=15, alignment=TA_LEFT))
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

        count, overflow

        data_len = len(data)
        notes = []
        while data_len > startPos:
            # any notes lines at this point are global, and the end of the confirmation
            if data[startPos].startswith('Notes:'):
                notes.append(data[startPos][7:].strip())
                startPos += 1
                continue
            rec_len = 6
            # get fixed portion of data
            line = data[startPos:startPos+rec_len]
            print(repr(line), verbose=2)
            if any(line):
                item = line
                notes = []
                while startPos+rec_len < data_len and data[startPos+rec_len].startswith('Notes:'):
                    note = data[startPos+rec_len][7:].strip()
                    rec_len += 1
                    if not note:
                        break
                    notes.append(note)
                    if data_len <= startPos:
                        break
                item.append('\n'.join(notes))
                line_item = OrderItem(*item)
                keywords.add(line_item.code)
                line_items.append(line_item)

                # count += 1
                # if count == overflow:
                #     line_items.insert(count-2, ['','\n-- continued --','','',''])
                #     overflow += 14

            startPos += rec_len

        self.keywords = ["per %s:" % self.date] + list(keywords)
        self.line_items = line_items
        self.data = data
        self.notes = notes

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


class OrderItem(NamedTuple):
    #
    code = 0, "Item Code"
    name = 1, "Common Name"
    latin_name = 2, "Latin Name"
    qty = 3, "Qty in Lbs"
    price = 4, "Price per Lb"
    total = 5, "Total Cost"
    notes = 6, "Any notes"
    #
    def __new__(cls, code, name, qty, price, total, latin_name, notes):
        # Convert the FIS Description to title case and latin to lower case
        name = name.title()
        latin_name = latin_name.lower()
        if notes:
            notes = 'Note: ' + notes
        return tuple.__new__(cls, (code, name, latin_name, qty, price, total, notes.strip()))


# reportlab config

order_conf_test_data = ([
        'ANAHUAC', '', '7522 SCOUT AVE.', 'BELL GARDENS, CA 90201', 
        'ANAHUAC', '2257 BRAVE ST.', 'BELL GARDENS, CA 90201', 'UNITED STATES',
        '07-12-22', 'RATE SHOPPER', 'EMAIL', 'NET 30', '118431',
        'FLA10001', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 'Notes: a longer and', 'Notes: more convoluted', 'Notes: note', 'Notes: ',
        'PAL13291', 'PALO AZUL', '105', '3.17', '332.85', '',  'Notes: ',
        'EPO10001', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'COR20001', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
        'FLA10002', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13292', 'PALO AZUL', '105', '3.17', '332.85', '', 
        'EPO10002', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'COR20002', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
        'FLA10003', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13293', 'PALO AZUL', '105', '3.17', '332.85', '', 
        'EPO10003', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'COR20003', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
        'FLA10004', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13294', 'PALO AZUL', '105', '3.17', '332.85', '',  'Notes: a note', 'Notes: ',
        'EPO10004', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'COR20004', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
        'FLA10005', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13295', 'PALO AZUL', '105', '3.17', '332.85', '', 
        'EPO10005', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'COR20005', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
        'FLA10006', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13296', 'PALO AZUL', '105', '3.17', '332.85', '', 
        'EPO10006', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'COR20006', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
        'FLA10007', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13297', 'PALO AZUL', '105', '3.17', '332.85', '', 
        'EPO10007', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'COR20007', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
        'FLA10008', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13298', 'PALO AZUL', '105', '3.17', '332.85', '', 
        'EPO10008', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'COR20008', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
        'FLA10009', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13299', 'PALO AZUL', '105', '3.17', '332.85', '', 
        'EPO10009', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'PAL13298', 'PALO AZUL', '105', '3.17', '332.85', '', 
        'EPO10008', 'EPASOTE DE COMER WHOLE', '45', '3.21', '144.45', '(Chenopodium ambrosioides)', 
        'COR20008', 'CORNSILK WHOLE', '48.5', '4.10', '198.85', '(Zea mays)', 
        'FLA10009', 'FLAX*SEED WHOLE', '50', '2.98', '149.00', '(Linum usitatissimum)', 
        'PAL13299', 'PALO AZUL', '105', '3.17', '332.85', '', 
        '', '', '', '', '', '', 
        '', '', '', '', '', '',
        'Notes: some final thoughts', 'Notes: about life, the universe, and everything', 'Notes: ',
        ], [
        "LION BRIDGE BREWING COMPANY", "ATTN:  QUINTON McCLAIN", "59 16TH AVENUE SW           ", "CEDAR RAPIDS, IA 52404",
        "LION BRIDGE BREWING COMPANY", "59 16TH AVENUE SW", "", "CEDAR RAPIDS, IA 52404",
        "07-14-23", "FEDEX GROUND", "LBBC71323", "PREPAID", "121579",
        "HIB14000", "HIBISCUS FLOWERS C/S", "134.25", "     4.77", "    640.37", "     (Hibiscus sabdariffa)", "Notes: ",
        "Notes: EMAILED COA & SHIP WITH ORDER",
        "Notes: CUSTOMERS FEDEX GROUND ACCOUNT# 720660415",
        "Notes: $10.00/BOX REBOXING FEE FOR GROUND SHIPPING",
        "Notes: DELIVERY CONTACT: QUINTON MCCLAIN 319-491-4471",
        ], [
        "THE EAST INDIES COMPANY", "EMAIL INVOICES ONLY", "CUSTOMERSERVICE@", "EASTINDIESCOFFEEANDTEA.COM",
        "THE EAST INDIES COMPANY", "", "7 KEYSTONE DRIVE", "LEBANON,  PA  17042",
        "07-17-23", "RATE SHOPPER", "3311", "NET 30", "121576",
        "CHA20002", "CHAMOMILE WHOLE (EGYPT)", " 127.5", "     7.61", "    970.28", "     (Matricaria chamomilla)", "Notes: REPACK W/LINERS IN BOXES", "Notes: ",
        "LAV10201", "LAVENDER*SUPER (FRANCE)", "    88", "     8.69", "    764.72", "     (Lavandula officinalis)", "Notes: ",
        "ORA23021", "ORANGE PL 1/4'' SQ CUT IMPORT", "    55", "     3.48", "    191.40", "     (Citrus sinensis)", "Notes: ",
        "PEP34001", "PEPPERMINT LEAVES*C/S (USA)", "   440", "     5.53", "  2,433.20", "     (Mentha piperita)", "Notes: ",
        "Notes: COA'S EMAILED TO CUSTOMER", "Notes: ",
        ])



# do it

Run()
