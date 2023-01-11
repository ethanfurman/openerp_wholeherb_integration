#!/usr/bin/python3
"""\
Manage FIS order confirmations, open order invoices, and availability in OpenERP.
"""


# imports & config

from __future__ import print_function
from antipathy import Path
from dbf import Date
from logging import INFO, getLogger, Formatter, handlers
import re
from scription import *

logger = getLogger()
logger.setLevel(INFO)
_handler = handlers.TimedRotatingFileHandler(
        '/var/log/fnx_fis_orders.log',
        when='midnight',
        backupCount=30,
        )
_formatter = Formatter('%(asctime)s %(funcName)-25s %(message)s')
_handler.setFormatter(_formatter)
logger.addHandler(_handler)
del _handler, _formatter


# API

@Command(
        )
def export_invoices():
    """
    copy open invoice pdfs from 2.2 to 2.243
    """
    for top_dir, cust_dirs, files in Path('/usr/FIS_Invoices').walk():
        break
    for dir in cust_dirs:
        target_dir = top_dir/dir
        for path, dirs, files in target_dir.walk():
            found = []
            for fn in files:
                if match(open_invoice, fn):
                    cust, invoice, date, po_number = match.groups()
                    try:
                        date = Date.strptime(date, '%Y%m%d')
                    except ValueError:
                        continue
                    found.append(path/fn)
            if found:
                Execute('rsync %s 192.168.2.243:/home/imports/open_invoices/' % ' '.join(found))
    Execute('ssh root@192.168.2.243 touch /home/imports/open_invoices/done')

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
        except TypeError:
            _logger.error('unable to parse file name %r', fqn.filename)
            error('unable to parse file name %r' % (fqn.filename, ))
            continue
        nfn = create_invoice_filename(cust, invoice, date, po)
        _logger.info('adding customer %s invoice %s to OpenERP', cust, nfn)
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
    _logger = getLogger('import_confirmations')
    source = Path('/home/imports/order_confs')
    archive = source/'archive'
    for fqn in source.glob('*.pdf'):
        try:
            cust, invoice = match(order_conf, fqn.filename).groups()
        except TypeError:
            _logger.error('problem with file name: %r', fqn.filename, )
            error('problem with file name: %r' % (fqn.filename, ))
            continue
        nfn = create_confirmation_filename(invoice)
        cp = Execute('/usr/local/bin/fnxfs cp %s res.partner/xml_id=%s/order_confirmations/%s' % (fqn, cust, nfn))
        if cp.returncode:
            _logger.error('unable to copy %s into OpenERP as %s', fqn, nfn)
            _logger.error(cp.stderr)
            error('unable to copy %s into OpenERP as %s' % (fqn, nfn))
        else:
            fqn.move(archive)
            _logger.info('customer %r confirmation %r processed', cust, nfn)


# helpers

open_invoice = r'(\d{6})_(\d+)_(\d{8})_(PO.+)\.pdf$'
order_conf = r'(\d+)-(\d+)\.pdf$'

match = Var(lambda needle, haystack: re.match(needle, haystack))

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


# do it

Run()
