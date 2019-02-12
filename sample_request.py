from osv import osv, fields
import logging

_logger = logging.getLogger(__name__)

class sample_product(osv.Model):
    'make lot number field point to wholeherb_integration.product_lot'
    _name = 'sample.product'
    _inherit = 'sample.product'

    _columns = {
        # 'product_id': fields.many2one('product.product', string='Item', domain=[('categ_id','child_of','Saleable')]),
        'product_lot_requested': fields.many2one(
                'wholeherb_integration.product_lot',
                string='Requested Lot #',
                domain="[('product_id','=',product_id)]",
                ),
        'product_lot_used': fields.many2one(
                'wholeherb_integration.product_lot',
                string='Used Lot #',
                domain="[('product_id','=',product_id)]",
                ),
        }


