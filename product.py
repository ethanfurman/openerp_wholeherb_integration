from collections import defaultdict
from fnx import xid, check_company_settings
from fnx.BBxXlate.fisData import fisData
from fnx import NameCase, translator
from openerp.addons.product.product import sanitize_ean13
from osv import osv, fields
from urllib import urlopen
import enum
import logging
import time

_logger = logging.getLogger(__name__)

CONFIG_ERROR = "Cannot sync products until  Settings --> Configuration --> FIS Integration --> %s  has been specified." 

lose_digits = translator(delete='0123456789')

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

class product_category(osv.Model):
    "makes external_id visible and searchable"
    _name = 'product.category'
    _inherit = 'product.category'

    _columns = {
        'name': fields.char('Sales Category', size=64, required=True, translate=True, select=True),
        'xml_id': fields.function(
            xid.get_xml_ids,
            arg=('product_category_integration','FIS Product Category', CONFIG_ERROR),
            fnct_inv=xid.update_xml_id,
            string="FIS ID",
            type='char',
            method=False,
            fnct_search=xid.search_xml_id,
            multi='external',
            ),
        'module': fields.function(
            xid.get_xml_ids,
            arg=('product_category_integration','FIS Product Category', CONFIG_ERROR),
            fnct_inv=xid.update_xml_id,
            string="FIS Module",
            type='char',
            method=False,
            fnct_search=xid.search_xml_id,
            multi='external',
            ),
        }


    def fis_updates(self, cr, uid, *args):
        _logger.info("product.category.fis_updates starting...")
        settings = check_company_settings(self, cr, uid, ('product_category_integration', 'Product Module', CONFIG_ERROR))
        module  = settings['product_category_integration']
        category_ids = self.search(cr, uid, [('module','=',module)])
        category_recs = self.browse(cr, uid, category_ids)
        category_codes = dict([(r.xml_id, dict(name=r.name, id=r.id, parent_id=r.parent_id)) for r in category_recs])
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
product_category()


class product_template(osv.Model):
    _name = "product.template"
    _inherit = 'product.template'

    _columns = {
        'warranty': fields.integer("Shelf Life (days)"),
        }
product_template()


class product_product(osv.Model):
    'Adds Available column and sold_by columns'
    _name = 'product.product'
    _inherit = 'product.product'

    def _product_available(self, cr, uid, ids, field_names=None, arg=False, context=None):
        settings = check_company_settings(self, cr, uid, ('product_integration', 'Product Module', CONFIG_ERROR))
        if context is None:
            context = {}
        model = self._name
        module = settings['product_integration']
        imd = self.pool.get('ir.model.data')
        nvty = fisData('NVTY', subset='10%s', filter=warehouses)
        records = self.browse(cr, uid, ids, context=context)
        values = {}
        for rec in records:
            current = values[rec.id] = {}
            try:
                imd_rec = imd.get_object_from_model_resid(cr, uid, model, rec.id, context=context)
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
        'xml_id': fields.function(
            xid.get_xml_ids,
            arg=('product_integration','Product Module',CONFIG_ERROR),
            fnct_inv=xid.update_xml_id,
            string="FIS ID",
            type='char',
            method=False,
            fnct_search=xid.search_xml_id,
            multi='external',
            ),
        'module': fields.function(
            xid.get_xml_ids,
            arg=('product_integration','Product Module',CONFIG_ERROR),
            fnct_inv=xid.update_xml_id,
            string="FIS Module",
            type='char',
            method=False,
            fnct_search=xid.search_xml_id,
            multi='external',
            ),

        'sold_by': fields.char('Sold by', size=50),
        'latin': fields.char('Latin name', size=40),
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
        'product_is_blend' : fields.boolean('Product is blend'),
        }

    def button_fis_refresh(self, cr, uid, ids, context=None):
        settings = check_company_settings(self, cr, uid, 
            ('product_integration', 'Product Module', CONFIG_ERROR),
            ('product_category_integration', 'Product Category', CONFIG_ERROR),
            )
        product_module = settings['product_integration']
        category_module = settings['product_category_integration']
        prod_cat = self.pool.get('product.category')
        prod_template = self.pool.get('product.template')

        nvty = fisData('NVTY', subset='10%s', filter=warehouses)
        records = self.browse(cr, uid, ids, context=context)
        for rec in records:
            fis_rec_list = nvty.get_subset(rec['xml_id'])
            if not fis_rec_list:
                continue
            fis_rec = fis_rec_list[0]   # use first record in subset
            values = self._get_fis_values(fis_rec)
            cat_ids = prod_cat.search(cr, uid, [('xml_id','=',values['categ_id'])])
            if not cat_ids:
                raise ValueError("unable to locate category code %s" % values['categ_id'])
            elif len(cat_ids) > 1:
                raise ValueError("too many matches for category code %s" % values['categ_id'])
            values['categ_id'] = prod_cat.browse(cr, uid, cat_ids)[0]['id']
            values['module'] = product_module
            self.write(cr, uid, rec['id'], values, context=context)
        return True

    def fis_updates(self, cr, uid, *args):
        """
        scans FIS product table and either updates product info or
        adds new products to table
        """
        _logger.info("product.product.fis_updates starting...")
        settings = check_company_settings(self, cr, uid, 
            ('product_integration', 'Product Module', CONFIG_ERROR),
            ('product_category_integration', 'Product Category', CONFIG_ERROR),
            )
        product_module = settings['product_integration']
        category_module = settings['product_category_integration']
        prod_cat = self.pool.get('product.category')
        prod_items = self
        # create a mapping of id -> res_id for categories
        cat_ids = prod_cat.search(cr, uid, [('module','=',category_module)])
        cat_recs = prod_cat.browse(cr, uid, cat_ids)
        cat_codes = dict([(r.xml_id, r.id) for r in cat_recs])
        # create a mapping of id -> res_id for product items
        prod_ids = prod_items.search(cr, uid, [('module','=',product_module)])
        prod_recs = prod_items.browse(cr, uid, prod_ids)
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
        latin = NameCase(fis_rec[P.latin])
        if latin == 'N/A' or lose_digits(latin) == '':
            latin = ''
        values['latin'] = latin
        values['categ_id'] = fis_rec[P.category].upper()
        #values['ean13'] = sanitize_ean13(fis_rec[P.ean13])
        values['active'] = 1
        values['sale_ok'] = 1
        avail_code = fis_rec[P.available].upper()
        values['avail'] = product_avail.get(avail_code, 'Unknown code: %s' % avail_code)
        sold_by = fis_rec[P.sold_by].strip()
        values['sold_by'] = sold_by
        return values
product_product()

class product_blend_category(osv.Model):
    _name = 'fis_wholeherb.blend_category'
    _description = 'table data for blend categories'
    _columns = {
        'name' : fields.char('Blend category name', size=62),
        'blends_ids' : fields.one2many(
            'fis_wholeherb.blend',
            'category_name',
            'Blends',
            ),
        }
product_blend_category()

class product_blend(osv.Model):
    _name = 'fis_wholeherb.blend'
    _description = 'table data for product blends'
    _columns = {
        'code' : fields.char('Code', size=8),
        'name' : fields.char('Name', size=212),
        'packaging' : fields.char('Packaging', size=112),
        'special_instructions' : fields.char('Special Instructions', size=267),
        'category_name' : fields.many2one(
            'fis_wholeherb.blend_category',
            'Category ID',
            ),
        'amount' : fields.float('Amount'),
        'uom' : fields.char('UOM', size=62),
        'batchsize' : fields.float('Batch Size'),
        'numberbatches' : fields.integer('Number Batches'),
        'ingredients_ids' : fields.one2many(
            'fis_wholeherb.blend_ingredient',
            'blend_id',
            'Ingredients',
            ),
        }
product_blend()

class product_blend_ingredient(osv.Model):
    _name = 'fis_wholeherb.blend_ingredient'
    _description = 'table data for product.blend_ingredient'
    _columns = {
        'blend_id' : fields.many2one(
            'fis_wholeherb.blend',
            'Blend',
            ),
        'product_id' : fields.many2one(
            'product.product',
            'Product',
            ),
        'percentinblend' : fields.float('% in Blend'),
        }
product_blend_ingredient()

