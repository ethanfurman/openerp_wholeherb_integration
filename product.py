from fnx_fs.fields import files
from .xid import xmlid
from dbf import Date
from VSS.utils import translator
from openerp.tools import SUPERUSER_ID, self_ids
from osv import osv, fields
import logging
import re

_logger = logging.getLogger(__name__)

CONFIG_ERROR = "Cannot sync products until  Settings --> Configuration --> FIS Integration --> %s  has been specified."

lose_digits = translator(delete='0123456789')
potential_lot = re.compile(r'^[ \ta-z]{,3}[ 0-9-]{3,}[a-z -]*$', re.IGNORECASE)


class product_category(xmlid, osv.Model):
    "makes external_id visible and searchable"
    _name = 'product.category'
    _inherit = 'product.category'

    _columns = {
        'xml_id': fields.char('FIS ID', size=16, readonly=True),
        'module': fields.char('FIS Module', size=16, readonly=True),
        'active': fields.boolean('Active'),
        }

    _defaults = {
        'active': True,
        }


    def fis_updates(self, cr, uid, *args):
        # this is now handled by the sync program
        return True

class product_template(osv.Model):
    _name = "product.template"
    _inherit = 'product.template'

    _columns = {
        'warranty': fields.integer("Shelf Life (days)"),
        }


class product_product(xmlid, osv.Model):
    'Adds Available column and sold_by columns'
    _name = 'product.product'
    _inherit = ['product.product', 'fnx_fs.fs']

    _fnxfs_path = 'product'
    _fnxfs_path_fields = ['xml_id', 'name']

    # XXX beginning production routines
    def _get_formula_update_ids(product_formula, cr, uid, changed_formula_ids, context=None):
        #
        # find the products effected by the change in formula name
        #
        if isinstance(changed_formula_ids, (int, long)):
            changed_formula_ids = [changed_formula_ids]
        self = product_formula.pool.get('product.product')
        formulae_names = [
                formula['name']
                for formula in product_formula.read(
                    cr, SUPERUSER_ID,
                    changed_formula_ids,
                    fields=['id','name'],
                    context=context,
                )]
        product_ids = self.search(
                cr, SUPERUSER_ID,
                [('module','=','F135'),('xml_id','in',formulae_names)],
                context=context
                )
        return product_ids

    # XXX end production routines

    def _get_fis_latin(self, cr, uid, ids, field_name=None, arg=False, context=None):
        if context is None:
            context = {}
        records = self.browse(cr, uid, ids, context=context)
        values = {}
        for rec in records:
            names = []
            if rec.xml_id:
                names.append('[%s]' % rec.xml_id)
            if rec.latin:
                names.append(rec.latin)
            values[rec.id] = ' '.join(names)
        return values

    def _product_available(self, cr, uid, ids, field_names=None, arg=False, context=None):
        records = self.browse(cr, uid, ids, context=context)
        values = {}
        for rec in records:
            qoh = rec['qty_available']
            qoo = rec['incoming_qty']
            qc = rec['outgoing_qty']
            values[rec.id] = qoh + qoo - qc
        return values

    def _get_ids_from_lots(product_lot, cr, uid, ids, context=None):
        if not isinstance(ids, (int, long)):
            [ids] = ids
        return [l.product_id.id for l in product_lot.browse(cr, uid, ids, context=context)]

    def _product_lot_available(self, cr, uid, ids, field_names=None, arg=False, context=None):
        products = self.browse(cr, uid, ids, context=context)
        values = {}
        for product in products:
            # find all lots for this product
            lots = (
                    self.pool.get('wholeherb_integration.product_lot')
                    .browse(cr, uid, [('product_id','=',product.id)], context=context)
                    )
            avail = 0
            for lot in lots:
                avail += lot.qty_on_hand + lot.qty_on_order - lot.qty_committed
            values[product.id] = avail
        return values

    _columns = {
        'xml_id': fields.char('FIS ID', size=16, readonly=True),
        'module': fields.char('FIS Module', size=16, readonly=True),
        'sold_by': fields.char('Sold by', size=50, help="unit size"),
        'latin': fields.char('Latin name', size=40),
        'fis_latin': fields.function(
                _get_fis_latin,
                type='char', size=96, string='FIS ID & Latin name',
                ),
        'avail': fields.char('Available?', size=24),
        'spcl_ship_instr': fields.text('Special Shipping Instructions'),
        'fis_location': fields.char('Location', size=6),
        'qty_available': fields.float(
            digits=(16,3), string='Quantity On Hand',
            help="Current quantity of products according to FIS. [I(6)]",
            ),
        'incoming_qty': fields.float(
            digits=(16,3), string='Quantity on Order',
            help="Quantity of products that are planned to arrive according to FIS. [I(8)]",
            ),
        'outgoing_qty': fields.float(
            digits=(16,3), string='Quantity Committed',
            help="Quantity of products that are planned to leave according to FIS. [I(7)]",
            ),
        'virtual_available': fields.function(
            _product_available, type='float', digits=(16,3), string='Forecasted Quantity',
            help="File 135 forecast quantity (computed as QoH - QC + QoO)",
            store={
                'product.product': (self_ids, ['incoming_qty', 'outgoing_qty', 'qty_available'], 10),
                },
            ),
        'virtual_available_via_lots': fields.function(
            _product_lot_available, type='float', digits=(16,3), string='Forecasted Quantity (Lots)',
            help="File 250 forecast quantity (computed as QoH - QC + QoO)",
            store={
                'wholeherb_integration.product_lot': (self_ids, ['qty_on_order', 'qty_committed', 'qty_on_hand'], 10),
                },
            ),
        'pl_100': fields.float(string='100+ price', track_visibility='initial_and_onchange'),
        'pl_1000': fields.float(string='1000+ price', track_visibility='initial_and_onchange'),
        'pl_nlt': fields.float(string='NLT', track_visibility='initial_and_onchange'),
        'pl_last_change': fields.date('Last price change'),
        'pi_metal': fields.boolean('Metal detection'),
        'pi_treatment': fields.boolean('Treatment'),
        'pi_sifting': fields.boolean('Sifting'),
        'pi_milling': fields.boolean('Milling'),
        'pi_none': fields.boolean('None'),
        'product_is_blend' : fields.boolean('Product is blend'),
        'lot_ids': fields.one2many('wholeherb_integration.product_lot', 'product_id', 'Lots'),
        'fnxfs_files': files('general', string='Available Files'),
        'c_of_a': files('c_of_a', string='Certificates of Analysis'),
        'sds': files('sds', string='Safety Data Sheets'),
        'create_date': fields.datetime('Product created on', readonly=True),
        'create_uid': fields.many2one('res.users', string='Product created by', readonly=True),
        'fis_record': fields.boolean('Record is in FIS'),
        }

    _defaults = {
            'fis_record': False,
            'pl_last_change': False,
            }

    def create(self, cr, uid, values, context=None):
        if not ('pl_last_change' in values and values['pl_last_change']):
            for f in ('pl_100','pl_1000','pl_nlt'):
                if values.get(f, 0):
                    values['pl_last_change'] = fields.date.today(self, cr, localtime=True)
                    break
        return super(product_product, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        if (
                ('pl_last_change' in values and values['pl_last_change'])
                or (
                    'pl_100' not in values
                    and 'pl_1000' not in values
                    and 'pl_nlt' not in values
                    )
            ):
            # change date specified or no price changes this time, we're done here
            return super(product_product, self).write(cr, uid, ids, values, context=context)
        #
        # separate ids into those that need to have their pl_last_change updated, and
        # those that do not
        #
        pl_changed = []
        pl_same = []
        changed_fields = [
                f
                for f in ('pl_100','pl_1000','pl_nlt')
                if f in values
                ]
        records = self.read(cr, uid, ids, fields=changed_fields, context=context)
        for rec in records:
            for f in changed_fields:
                if rec[f] != values[f]:
                    pl_changed.append(rec['id'])
                    break
            else:
                pl_same.append(rec['id'])
        res1 = res2 = True
        if pl_changed:
            values['pl_last_change'] = fields.date.today(self, cr, localtime=True)
            res1 = super(product_product, self).write(cr, uid, pl_changed, values, context=context)
            values.pop('pl_last_change')
        if pl_same:
            res2 = super(product_product, self).write(cr, uid, pl_same, values, context=context)
        return res1 and res2

    def fnxfs_folder_name(self, records):
        "return name of folder to hold related files"
        res = {}
        for record in records:
            res[record['id']] = record['xml_id'] or ("%s-%d" % (record['name'], record['id']))
        return res

    def fis_updates(self, cr, uid, *args):
        # this is now handled by the sync program
        return True


class product_lot(osv.Model):
    _name = 'wholeherb_integration.product_lot'
    _description = 'product lot'
    _rec_name = 'lot_no'
    _order = 'lot_no desc'

    def _validate_lot_no(self, cr, uid, ids, field_names, arg, context=None):
        res = {}
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        valid_lot = re.compile(user.company_id.valid_lot_regex or '!!!!!', re.IGNORECASE)
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = {
                    'lot_no_maybe': bool(potential_lot.match(rec.lot_no)),
                    'lot_no_valid': bool(valid_lot.match(rec.lot_no)),
                    }
        return res

    _columns = {
        'active': fields.boolean('Active'),
        'lot_no': fields.char('Lot #', size=10),
        'qty_recd': fields.integer('Amount received'),
        'qty_recd_uom_id': fields.many2one('product.uom', 'Received UoM'),
        'qty_remain': fields.integer('Amount remaining'),
        'date_received': fields.date('Date Received/Created'),
        'prev_lot_no_id': fields.many2one(
            'wholeherb_integration.product_lot',
            'Previous Lot #',
            ),
        'product_id': fields.many2one(
            'product.product',
            'Product',
            ),
        'supplier_id': fields.many2one(
            'res.partner',
            'Supplier',
            ),
        'cofo_ids': fields.many2many(
            'res.country',
            'lot_country_rel',
            'cid',
            'lid',
            'Country of Origin',
            ),
        'lot_no_valid': fields.function(
            _validate_lot_no,
            fnct_inv=True,
            help='lot number matches pattern "^(A|F|M|P|R)?\d{4,6}(F|HT|Q|R|S|ST|STP|U)?$"',
            type='boolean',
            string='Valid lot number?',
            multi='check-lot',
            store={
                'wholeherb_integration.product_lot': (self_ids, ['lot_no'], 10),
                },
            ),
        'lot_no_maybe': fields.function(
            _validate_lot_no,
            fnct_inv=True,
            help='lot number might be valid',
            type='boolean',
            string='Possibly valid lot number?',
            multi='check-lot',
            store={
                'wholeherb_integration.product_lot': (self_ids, ['lot_no'], 10),
                },
            ),
        'preship_lot': fields.boolean('Pre-Ship lot?'),
        'create_date': fields.datetime('Lot # created on', readonly=True, track_visibility='onchange'),
        'create_uid': fields.many2one('res.users', string='Lot # created by', readonly=True),
        'fis_record': fields.boolean('Record is in FIS'),
        'qty_on_hand': fields.float(digits=(16,3), string='Qty on Hand', help="Q(0)"),
        'qty_committed': fields.float(digits=(16,3), string='Qty Committed', help="Q(1)"),
        'qty_on_order': fields.float(digits=(16,3), string='Qty on Order', help="Q(2)"),
        'qty_produced': fields.float(digits=(16,3), string='Qty Produced', help="Q(4)"),
        'qty_on_hold': fields.float(digits=(16,3), string='Qty on Hold', help="Q(5)"),
        }

    _defaults = {
            'active': True,
            'fis_record': False,
            }

    def onchange_lot_no(self, cr, uid, ids, lot_no, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        valid_lot = re.compile(user.company_id.valid_lot_regex or '!!!!!')
        return {'value': {'lot_no_valid': bool(valid_lot.match(lot_no))}}


class product_traffic(osv.Model):
    _name = 'wholeherb_integration.product_traffic'
    _description = 'running out of product'
    _order = 'date desc'
    _inherit = ['mail.thread']
    _mirrors = {'product_id': ['description', 'categ_id']}

    def _check_already_open(self, cr, uid, ids):
        products = set()
        for rec in self.browse(cr, SUPERUSER_ID, [None]):
            if rec.state in (False, 'done'):
                continue
            if rec.product_id in products:
                return False
            products.add(rec.product_id)
        return True

    def _delete_stale_entries(self, cr, uid, arg=None, context=None):
        'zombifies entries that have been in the seen state for longer than 20 days'
        today = Date.today()
        cart = []
        for rec in self.browse(cr, uid, context=context):
            if (
                rec.purchase_comment_date and
                ((today - Date(rec.purchase_comment_date)).days > 20)
                ):
                cart.append(rec.id)
        if cart:
            self.write(cr, uid, cart, {'state': False}, context=context)
        return True

    def _find_open_entries(self, cr, uid, ids, field_names, arg, context=None):
        """
        return duplicate open entries per item
        """
        res = {}
        products = {}
        current_records = self.read(cr, uid, ids, fields=['product_id'], context=context)
        for rec in current_records:
            products[rec['product_id'][0]] = []
        for rec in self.read(
                cr, uid,
                [('product_id','in',products.keys()),('state','!=','done')],
                fields=['product_id'],
                context=context,
            ):
            products[rec['product_id'][0]].append(rec['id'])
        for rec in current_records:
            res[rec['id']] = [id for id in products[rec['product_id'][0]] if id != rec['id']]
        return res

    def _get_sales_tree_text(self, cr, uid, ids, field_names, arg, context=None):
        res = {}
        for rec in self.read(cr, uid, ids, fields=['sales_comment','sales_comment_text'], context=context):
            if rec['sales_comment'] == 'other':
                comment = rec['sales_comment_text']
            else:
                comment = rec['sales_comment']
            if len(comment) > 20:
                comment = comment[:17] + '...'
            res[rec['id']] = comment
        return res

    _columns = {
        'name': fields.related('product_id','name', string='Product name', type='text', readonly=True),
        'date': fields.date('Date Created'),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'sales_comment': fields.selection(
            (('low', 'getting low'), ('out', 'sold out'), ('other','other')),
            'Sales Comment',
            track_visibility='change_only',
            ),
        'sales_comment_text': fields.text('Other comment'),
        'sales_tree_text': fields.function(
            _get_sales_tree_text,
            string='Sales list comment',
            store=({
                'wholeherb_integration.product_traffic': (self_ids, ['sales_comment'], 10),
                }),
            type='char',
            size=20,
            ),
        'purchase_comment': fields.text('Purchase Comment', track_visibility='change_only'),
        'state': fields.selection(
            (('new','New'), ('seen', 'Seen'), ('ordered','On Order'), ('done', 'Received')),
            'Status',
            track_visibility='change_only',
            ),
        'purchase_comment_available': fields.selection(
            (('no',''), ('yes','Yes')),
            'Purchasing comment available?',
            ),
        'purchase_comment_date': fields.date('Purchasing updated'),
        'open_entry_ids': fields.function(
            _find_open_entries,
            help="currently open traffic entries",
            relation='wholeherb_integration.product_traffic',
            type='one2many',
            string='EXISTING ENTRIES',
            ), 
        }

    _defaults = {
        'date': lambda s, c, u, ctx=None: fields.date.today(s, c),
        'state': lambda *a: 'new'
        }

    _constraints = [
        ]

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        ctx['mail_track_initial'] = True
        if values.get('purchase_comment'):
            values['purchase_comment_available'] = 'yes'
            values['purchase_comment_date'] = fields.date.today(self, cr)
            values['state'] = 'seen'
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        follower_ids = [u.partner_id.id for u in user.company_id.traffic_followers_ids]
        if follower_ids:
            values['message_follower_ids'] = follower_ids
        return super(product_traffic, self).create(cr, uid, values, context=ctx)

    def mark_as(self, cr, uid, ids, state, context=None):
        return self.write(cr, uid, ids, {'state': state}, context=context)

    def name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            res.append((record.id, record.product_id.name))
        return res

    def onchange_product(self, cr, uid, ids, product_id, context=None):
        return {'value':
                {'open_entry_ids': self.search(
                        cr, uid,
                        [('product_id','=',product_id),('id','not in',ids)],
                        context=context,
                        )}
                }

    def write(self, cr, uid, ids, values, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        if ('purchase_comment' in values or 'state' in values) and ids:
            pc = values.get('purchase_comment')
            s = values.get('state')
            for rec in self.browse(cr, uid, ids, context=context):
                vals = values.copy()
                if pc is not None:
                    if pc:
                        vals['purchase_comment_available'] = 'yes'
                        vals['purchase_comment_date'] = fields.date.today(self, cr)
                        if rec.state == 'new':
                            vals['state'] = 'seen'
                    else:
                        vals['purchase_comment_available'] = 'no'
                        vals['purchase_comment_date'] = False
                        if rec.state == 'seen':
                            vals['state'] = 'new'
                if s not in (None, 'new', 'seen'):
                    vals['purchase_comment_date'] = fields.date.today(self, cr)
                if not super(product_traffic, self).write(cr, uid, rec.id, vals, context=context):
                    return False
            return True
        return super(product_traffic, self).write(cr, uid, ids, values, context=context)


class product_missed_sales(osv.Model):
    _name = 'wholeherb_integration.product_missed_sales'
    _description = 'missed sale due to insufficient product'
    _order = 'date desc'
    _inherit = ['mail.thread']

    _columns = {
        'date': fields.date('Date Created'),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'comment': fields.text('Comments'),
        }

    _defaults = {
        'date': lambda s, c, u, ctx=None: fields.date.today(s, c),
        }

