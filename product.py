from fnx_fs.fields import files
from .xid import xmlid
from dbf import Date
from VSS.BBxXlate.fisData import fisData
from VSS.address import NameCase
from VSS.utils import translator
from openerp.tools import SUPERUSER_ID, self_ids
from osv import osv, fields
import enum
import logging
import re

_logger = logging.getLogger(__name__)

CONFIG_ERROR = "Cannot sync products until  Settings --> Configuration --> FIS Integration --> %s  has been specified."

lose_digits = translator(delete='0123456789')
potential_lot = re.compile(r'^[ \ta-z]{,3}[ 0-9-]{3,}[a-z -]*$', re.IGNORECASE)

def warehouses(rec):
    return rec[P.warehouse] in ('0SON','0PRO','0QAH','0INP','0EXW','0GLD')

class FISenum(str, enum.Enum):
    pass

class C(FISenum):
    'Customers from CSMS'
    code =       'An$(3,6)'
    name =       'Bn$'
    addr1 =      'Cn$'
    addr2 =      'Dn$'
    addr3 =      'En$'
    postal =     'Ln$'
    phone =      'Gn$(20,10)'
    fax =        'Gn$(31,15)'
    addl_phone = 'Gn$(46,15)'
    sales_mgr =  'Jn$(10,3)'

class V(FISenum):
    'Vendors from VNMS'
    code =        'An$(3,6)'
    name =        'Bn$'
    addr1 =       'Cn$'
    addr2 =       'Dn$'
    addr3 =       'En$'
    phone =       'Gn$(1,15)'
    fax =         'Gn$(16,15)'
    telex =       'Gn$(31,15)'
    is_broker =   'In$(5,1)'
    broker_code = 'In$(6,3)'
    contact =     'Nn$'

class S(FISenum):
    'Suppliers from POSM'
    code =  'An$(3,6)'
    name =  'Bn$'
    addr1 = 'Cn$'
    addr2 = 'Dn$'
    addr3 = 'En$'
    phone = 'Gn$(1,15)'
    fax =   'Gn$(16,15)'
    telex = 'Gn$(31,15)'

class P(FISenum):
    'Products from NVTY'
    code =      'An$(3,8)'
    warehouse = 'An$(15,4)'
    available = 'Bn$(1,1)'
    category =  'Bn$(4,1)'
    sold_by =   'Bn$(9,2)'
    item_type = 'Bn$(15,1)'
    lots =      'Bn$(25,1)'
    location =  'Bn$(34,6)'
    desc =      'Cn$'
    formula =   'Dn$(1,6)'
    latin =     'Dn$(33,40)'
    supplier =  'Gn$'
    on_hand =   'I(6)'
    committed = 'I(7)'
    on_order =  'I(8)'


class ProductSource(fields.SelectionEnum):
    _order_ = ""


class CNVZc(FISenum):
    'Category codes for Products'
    code = 'An$(4,1)'
    desc = 'Bn$'

product_avail = {
    'Y' :   'yes',
    'N' :   'no',
    'D' :   'discontinued',
    'H' :   'on hold',
    }


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
        _logger.info("product.category.fis_updates starting...")
        module  = 'cnvzc'
        xml_id_map = self.get_xml_id_map(cr, uid, module=module)
        category_recs = dict((r.id, r) for r in self.browse(cr, uid, xml_id_map.values()))
        category_codes = {}
        for key, id in xml_id_map.items():
            rec = category_recs[id]
            category_codes[key] = dict(name=rec.name, id=rec.id, parent_id=rec.parent_id)
        cnvz = fisData('CNVZc', keymatch='c10%s')
        for category_rec in cnvz:
            result = {}
            result['xml_id'] = key = category_rec[CNVZc.code]
            name = category_rec[CNVZc.desc].title()
            result['name'] = name
            result['module'] = module
            if key in category_codes:
                result['parent_id'] = category_codes[key]['parent_id']['id']
                self.write(cr, uid, category_codes[key]['id'], result)
            else:
                result['parent_id'] = 2
                new_id = self.create(cr, uid, result)
                category_codes[key] = dict(name=result['name'], id=new_id, parent_id=result['parent_id'])
        _logger.info(self._name +  " done!")
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
        if context is None:
            context = {}
        nvty = fisData('NVTY', subset='10%s', filter=warehouses)
        records = self.browse(cr, uid, ids, context=context)
        values = {}
        for rec in records:
            current = values[rec.id] = {}
            try:
                fis_recs = nvty.get_subset(rec.xml_id)
                if not fis_recs:
                    raise ValueError('no matching records for %s' % rec.xml_id)
                fis_rec = fis_recs[0][1]
            except (ValueError, ):
                current['qty_available'] = qoh = 0
                current['incoming_qty'] = inc = 0
                current['outgoing_qty'] = out = 0
                current['virtual_available'] = qoh + inc - out
            else:
                current['qty_available'] = qoh = fis_rec[P.on_hand]
                current['incoming_qty'] = inc = fis_rec[P.committed]
                current['outgoing_qty'] = out = fis_rec[P.on_order]
                current['virtual_available'] = qoh + inc - out
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
        'qty_available': fields.function(_product_available, multi='qty_available',
            type='float', digits=(16,3), string='Quantity On Hand',
            help="Current quantity of products according to FIS",
            ),
        'virtual_available': fields.function(_product_available, multi='qty_available',
            type='float', digits=(16,3), string='Forecasted Quantity',
            help="Forecast quantity (computed as Quantity On Hand - Outgoing + Incoming)",
            ),
        'incoming_qty': fields.function(_product_available, multi='qty_available',
            type='float', digits=(16,3), string='Incoming',
            help="Quantity of products that are planned to arrive according to FIS.",
            ),
        'outgoing_qty': fields.function(_product_available, multi='qty_available',
            type='float', digits=(16,3), string='Outgoing',
            help="Quantity of products that are planned to leave according to FIS.",
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

    def button_fis_refresh(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        product_module = 'nvty'
        prod_cat = self.pool.get('product.category')
        nvty = fisData('NVTY', subset='10%s', filter=warehouses)
        for id in ids:
            current = self.browse(cr, uid, ids[0], context=context)
            key = current.xml_id or current.default_code
            if not key:
                if len(ids) == 1:
                    raise osv.except_osv('Warning', 'Item does not have an FIS identifier.')
                continue
            matches = nvty.get_subset(key)
            if not matches:
                if len(ids) == 1:
                    raise osv.except_osv('Warning', 'Item does not exist in the FIS system.')
                continue
            # matches is a list of (key, record) tuples
            fis_rec = matches[0][1]
            values = self._get_fis_values(fis_rec)
            cat_ids = prod_cat.search(cr, uid, [('xml_id','=',values['categ_id'])])
            if not cat_ids:
                raise ValueError("unable to locate category code %s" % values['categ_id'])
            elif len(cat_ids) > 1:
                raise ValueError("too many matches for category code %s" % values['categ_id'])
            values['categ_id'] = prod_cat.browse(cr, uid, cat_ids)[0]['id']
            values['module'] = product_module
            self.write(cr, uid, [id], values, context=context)
        return True

    def fis_updates(self, cr, uid, *args):
        """
        scans FIS product table and either updates product info or
        adds new products to table
        """
        _logger.info("product.product.fis_updates starting...")
        product_module = 'nvty'
        category_module = 'cnvzc'
        prod_cat = self.pool.get('product.category')
        prod_items = self
        # create a mapping of id -> res_id for categories
        cat_ids = prod_cat.search(cr, uid, [('module','=',category_module)])
        cat_recs = prod_cat.browse(cr, uid, cat_ids)
        cat_codes = dict([(r.xml_id, r.id) for r in cat_recs])
        # create a mapping of id -> res_id for product items
        prod_xml_id_map = self.get_xml_id_map(cr, uid, module=product_module)
        prod_recs = prod_items.browse(cr, uid, prod_xml_id_map.values())
        # xml_id is also stored in default_code, so if the xml_id association is ever lost (by uninstalling this
        # module, for example) we can reassociate once the module in reinstalled
        synced_prods = {}
        unsynced_prods = {}
        for rec in prod_recs:
            if rec.xml_id:
                synced_prods[rec.xml_id] = rec
            elif rec.default_code:
                unsynced_prods[rec.default_code] = rec
        processed = set()
        nvty = fisData('NVTY', subset='10%s', filter=warehouses)
        for inv_rec in nvty:
            values = self._get_fis_values(inv_rec)
            key = values['xml_id']
            if key in processed:
                continue
            try:
                values['categ_id'] = cat_codes[values['categ_id']]
            except KeyError:
                _logger.warning("Unable to add/update product %s because of missing category %r" % (key, values['categ_id']))
                continue
            values['module'] = product_module
            if key in synced_prods:
                prod_rec = synced_prods[key]
                if not values['latin']:
                    values['latin'] = prod_rec.latin or values['latin']
                prod_items.write(cr, uid, prod_rec.id, values)
            elif key in unsynced_prods:
                prod_rec = unsynced_prods[key]
                prod_items.write(cr, uid, prod_rec.id, values)
            else:
                values['name'] = '[%s]' % key
                id = prod_items.create(cr, uid, values)
                prod_rec = self.browse(cr, uid, [id])[0]
                synced_prods[key] = prod_rec
            if values['latin'] and values['sold_by']:
                processed.add(key)

        _logger.info(self._name + " done!")
        return True

    def _get_fis_values(self, fis_rec):
        values = {}
        values['xml_id'] = values['default_code'] = fis_rec[P.code]
        values['module'] = 'nvty'
        latin = NameCase(fis_rec[P.latin])
        if latin == 'N/A' or lose_digits(latin) == '':
            latin = ''
        values['latin'] = latin
        values['categ_id'] = fis_rec[P.category].upper()
        values['active'] = 1
        values['sale_ok'] = 1
        avail_code = fis_rec[P.available].upper()
        values['avail'] = product_avail.get(avail_code, 'Unknown code: %s' % avail_code)
        sold_by = fis_rec[P.sold_by].strip()
        values['sold_by'] = sold_by
        return values

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

    _columns = {
        'name': fields.related('product_id','name', string='Product name', type='text', readonly=True),
        'date': fields.date('Date Created'),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'sales_comment': fields.selection(
            (('low', 'getting low'), ('out', 'sold out')),
            'Sales Comment',
            track_visibility='change_only',
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

