from collections import defaultdict
from fnx.xid import xmlid
from fnx.BBxXlate.fisData import fisData
from fnx import NameCase, translator, xid
from openerp.addons.product.product import sanitize_ean13
from osv import osv, fields
from urllib import urlopen
import enum
import logging
import operator as op
import time

class sample_memo(osv.Model):
    'samples sent to (prospective) customers'
    _name = 'wholeherb_integration.sample_memo'
    _rec_name = 'order_num'

    _columns = {
        'order_num': fields.char('Order #', size=10, required=True),
        'employee_id': fields.many2one('res.partner', 'Sales Rep'),
        'order_date': fields.datetime('Date of order'),
        'promise_date': fields.datetime('Promised date'),
        'customer_id': fields.many2one('res.partner', 'Customer'),
        'customer_contact_id': fields.many2one('res.partner', 'Customer contact'),
        'ship_date': fields.date('Ship date'),
        'shipping_id': fields.many2one('wholeherb_integration.shipping_method', 'Shipping Method'),
        'lot_ids': fields.many2many(
            'wholeherb_integration.product_lot',
            'memo_lot_rel',
            'mid',
            'sid',
            'Lots',
            ),
        'comments': fields.text('Comments')
        }

    _sql_constraints = [
        ('order_unique', 'unique(order_num)', 'order already exists in the system'),
        ]


class shipping_method(osv.Model):
    'shipping method'
    _name = 'wholeherb_integration.shipping_method'

    _columns = {
        'name': fields.char('Method', size=32, required=True),
        'company': fields.char('Company', size=64),
        'time': fields.integer('Days to delivery'),
        'description': fields.text('Description'),
        }

    _sql_constraints = [
        ('name_unique', 'unique(name)', 'name already exists in the system'),
        ]

