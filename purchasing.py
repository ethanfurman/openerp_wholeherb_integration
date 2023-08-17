from openerp.tools import self_ids
from osv import osv, fields

import logging

_logger = logging.getLogger(__name__)

class Approval(fields.SelectionEnum):
    _order_ = 'none yes no'
    none = '', ''
    yes = 'Accepted'
    no = 'Rejected'


class ReportType(fields.SelectionEnum):
    _order_ = 'date_prod supp_prod prod_date'
    date_prod = 'Date / Product'
    supp_prod = 'Supplier / Product'
    prod_date = 'Product / Date'

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
            digits=(16,3),
            multi='calced',
            ),
        'cost': fields.float('Cost'),
        'proj_clearance': fields.float('Proj clearance'),
        'act_fob_cost': fields.function(
            _get_calc_values,
            method=True,
            string='act FOB Cost',
            type='float',
            digits=(16,3),
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
            type='char',
            size=64,
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

class purchasing(osv.Model):
    'purchase order'
    _name = 'wholeherb_integration.purchase_order'
    _rec_name = 'purchase_order'
    _order = 'purchase_order desc'

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


class preship_sample(osv.Model):
    _name = 'wholeherb_integration.preship_sample'
    _description = 'preship sample lot from supplier'
    _order = 'lot_no desc'

    def _get_names(self, cr, uid, ids, field_name=None, arg=None, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = values = {}
            values['product_name'] = rec.product_id.name or rec.adb_product
            values['supplier_name'] = rec.supplier_id.name or rec.adb_supplier
            values['customer_name'] = rec.customer_id.name or rec.adb_customer
            values['salesrep_name'] = rec.salesrep_id.name or rec.adb_salesrep
        return res

    _columns = {
        'active': fields.boolean('Active'),
        'lot_no': fields.char('Lot #', size=12),
        'date_recd': fields.date('Date Received', oldname='received_date'),
        'product_id': fields.many2one('product.product', 'Product'),
        'rnd_use': fields.boolean('R/D Use Only'),
        'approved': fields.selection(Approval, 'Approval Status'),
        'supplier_id': fields.many2one('res.partner', 'Supplier', domain="[('supplier','=',True),('xml_id','!=',False)]"),
        'supplier_lot_no': fields.char('Supplier Lot #', size=64),
        'supplier_address': fields.text('Supplier Address'),
        'comments': fields.text('Comments'),
        'salesrep_id': fields.many2one(
                'res.users',
                'WHC Sales Rep',
                domain=[('groups_id','=',fields.ref('base.group_sale_salesman'))],
                ),
        'customer_id': fields.many2one('res.partner', 'WHC Customer', domain="[('customer','=',True),('xml_id','!=',False)]"),
        'adb_salesrep': fields.char('Sales Rep (MDB)', size=32),
        'adb_customer': fields.char('WHC Customer (MDB)', size=64),
        'adb_product': fields.char('Product (MDB)', size=64),
        'adb_supplier': fields.char('Supplier (MDB)', size=64),
        'product_name': fields.function(
                _get_names,
                type='char',
                size=128,
                string='Product name',
                multi='names',
                store={
                    'wholeherb_integration.preship_sample': (
                        self_ids, [
                            'product_id', 'adb_product',
                            'supplier_id', 'adb_supplier',
                            'customer_id', 'adb_customer',
                            'salesrep_id', 'adb_salesrep',
                            ],
                        10)}
                ),
        'supplier_name': fields.function(
                _get_names,
                type='char',
                size=128,
                string='Supplier name',
                multi='names',
                store={
                    'wholeherb_integration.preship_sample': (
                        self_ids, [
                            'product_id', 'adb_product',
                            'supplier_id', 'adb_supplier',
                            'customer_id', 'adb_customer',
                            'salesrep_id', 'adb_salesrep',
                            ],
                        10)}
                ),
        'customer_name': fields.function(
                _get_names,
                type='char',
                size=128,
                string='WHC Customer name',
                multi='names',
                store={
                    'wholeherb_integration.preship_sample': (
                        self_ids, [
                            'product_id', 'adb_product',
                            'supplier_id', 'adb_supplier',
                            'customer_id', 'adb_customer',
                            'salesrep_id', 'adb_salesrep',
                            ],
                        10)}
                ),
        'salesrep_name': fields.function(
                _get_names,
                type='char',
                size=128,
                string='WHC Sales Rep name',
                multi='names',
                store={
                    'wholeherb_integration.preship_sample': (
                        self_ids, [
                            'product_id', 'adb_product',
                            'supplier_id', 'adb_supplier',
                            'customer_id', 'adb_customer',
                            'salesrep_id', 'adb_salesrep',
                            ],
                        10)}
                ),
        }

    _defaults = {
        'active': True,
        }

    def onchange_supplier(self, cr, uid, ids, supplier_id, context=None):
        res_partner = self.pool.get('res.partner')
        supplier = res_partner.read(
                cr, uid, supplier_id,
                fields=['name','street','street2','city','state_abbr','zip','country_id'],
                context=context,
                )
        address = [supplier['name'], supplier['street'], supplier['street2']]
        city = '  '.join(supplier[f] for f in ('city','state_abbr','zip') if supplier[f])
        address.append(city)
        address.append(supplier['country_id'][1] or '')
        _logger.warning('address: %r', address)
        return {'value': {'supplier_address': '\n'.join(l for l in address if l)}}


class preship_sample_report(osv.TransientModel):
    _name = 'wholeherb_integration.preship_sample.report'
    _description = 'supplier sample report'

    _columns = {
        'sort': fields.selection(ReportType, string='Sort'),
        'approved': fields.boolean('Approved'),
        'rejected': fields.boolean('Rejected'),
        'rnd_use': fields.boolean('R/D'),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'start_prod': fields.char('Start Product', size=24),
        'end_prod': fields.char('End Product', size=24),
        'start_supp': fields.char('Start Supplier', size=24),
        'end_supp': fields.char('End Supplier', size=24),
        }

    _defaults = {
        'sort': ReportType.date_prod,
        }

    def create_pdf(self, cr, uid, ids, context=None):
        return {'type': 'ir.actions.report.xml', 'report_name': 'wholeherb_integration.preship_sample', 'datas': {}, 'nodestroy': True}
