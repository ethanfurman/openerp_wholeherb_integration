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

class purchasing_lot(osv.Model):
    'Lot information associated with a purchase'
    _inherit = 'wholeherb_integration.product_lot'
    _name = 'wholeherb_integration.product_lot'

    def _get_preship(self, cr, uid, ids, field_name, args, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        values = {}
        if context is None:
            context = {}
        if not context.get('seen'):
            context['seen'] = set()
        seen = context['seen']
        for id in ids:
            if id in seen:
                values[id] = ''
            else:
                seen.add(id)
                current = self.browse(cr, uid, id, context=context)
                preship = current.preship_id
                values[id] = preship[field_name] or ''
        return values

    def _get_calc_values(self, cr, uid, ids, field_names, args, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = {}
        calc_fields = {
            'proj_fob_cost': ('cost', 'proj_clearance'),
            'act_fob_cost': ('act_cost', 'i_f', 'cus', 'misc'),
            }
        for id in ids:
            res[id] = {}
            record = self.browse(cr, uid, id, context=context)
            for field in field_names:
                if field not in calc_fields:
                    raise osv.except_osv('Programming Error', 'Field %r unknown' % field)
                add_em_up = calc_fields[field]
                values = [record[f] for f in add_em_up]
                total = sum(values)
                res[id][field] = total
        return res

    _columns = {
        'match_preship': fields.boolean('Match preship'),
        'risk_factor': fields.char('Risk Factor', size=32),
        'pack': fields.float('Pack'),
        'proj_fob_cost': fields.function(
            _get_calc_values,
            method=True,
            string='Proj FOB Cost',
            type='float',
            multi='calced',
            ),
        'cost': fields.float('Cost'),
        'proj_clearance': fields.float('Proj clearance'),
        'act_fob_cost': fields.function(
            _get_calc_values,
            method=True,
            string='act FOB Cost',
            type='float',
            multi='calced',
            ),
        'act_cost': fields.float('Act Cost'),
        'i_f': fields.float('I/F'),
        'cus': fields.float('Cus'),
        'misc': fields.float('Misc'),
        'on_order': fields.integer('On Order'),
        'on_order_uom_id': fields.many2one('product.uom', 'On Order UoM'),
        'qty_avail': fields.selection([('all','All'), ('some','Some'), ('none','None')], 'Qty Avail'),
        'status': fields.char('Status', size=32),
        'etd_0son': fields.date('ETD 0SON'),
        'terms': fields.char('Terms', size=12),
        'c_of_a': fields.char('CofA', size=16),
        'preship_id': fields.many2one(
            'wholeherb_integration.product_lot',
            'Pre-Ship Lot #',
            ),
        'preship_status': fields.function(
            _get_preship,
            string='Preship Status',
            ),
        'expected_date': fields.date('Expected Date'),
        'usda': fields.selection([('na','N/A'), ('refused','Refused'), ('held','On hold'), ('cleared','Cleared')], 'USDA'),
        'fda': fields.selection([('na','N/A'), ('refused','Refused'), ('held','On hold'), ('cleared','Cleared')], 'FDA'),
        'customs': fields.selection([('na','N/A'), ('refused','Refused'), ('held','On hold'), ('cleared','Cleared')], 'Customs'),
        'source_lot_no': fields.char('Vendor lot #', size=32),
        's_comment': fields.text('Comments (S)'),
        'pr_comment': fields.text('Comments (P/R)'),
        }
purchasing_lot()

class purchasing(osv.Model):
    'purchase order'
    _name = 'wholeherb_integration.purchase_order'
    _rec_name = 'purchase_order'

    _columns = {
        'purchase_order': fields.integer('Purchase Order', required=True),
        'supplier_id': fields.many2one('res.partner', 'Supplier'),
        'vessel': fields.char('Vessel', size=32),
        'lot_ids': fields.many2many(
            'wholeherb_integration.product_lot',
            'po_lot_rel',
            'lid',
            'pid',
            'Items',
            ),
        }

    _sql_constraints = [
        ('po_unique', 'unique(purchase_order)', 'Purchase Order already exists in the system'),
        ]

purchasing()
