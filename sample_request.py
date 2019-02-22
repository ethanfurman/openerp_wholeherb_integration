from osv import osv, fields
import logging

_logger = logging.getLogger(__name__)


class sample_request(osv.Model):
    _name = 'sample.request'
    _inherit = 'sample.request'

    _columns= {
        'ship_to_parent_id': fields.related('ship_to_id', 'ship_to_parent_id', type='many2one'),
        }


class sample_product(osv.Model):
    'make lot number field point to wholeherb_integration.product_lot'
    _name = 'sample.product'
    _inherit = 'sample.product'

    def _get_changed_sample_product_ids(product_product, cr, uid, changed_ids, context=None):
        self = product_product.pool.get('sample.product')
        ids = self.search(
                cr, uid,
                [('product_id','in',changed_ids)],
                context=context,
                )
        return ids

    def _get_requested_lot(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for rec in self.browse(cr, uid, ids, context=context):
            target = field_name + '_id'
            res[rec.id] = rec[target].lot_no
        return res

    _columns = {
        'product_id': fields.many2one(),
        'product_lot_requested_id': fields.many2one(
                'wholeherb_integration.product_lot',
                string='Requested Lot #',
                domain="[('product_id','=',product_id)]",
                ),
        'product_lot_requested': fields.function(
                _get_requested_lot,
                type='char',
                store={
                    'sample.product':
                        (lambda s, c, u, ids, ctx: ids, ['product_lot_requested_id'], 10),
                    'product.product':
                        (_get_changed_sample_product_ids, ['default_code', 'name'], 15),
                    },
                ),
        'product_lot_used_id': fields.many2one(
                'wholeherb_integration.product_lot',
                string='Used Lot #',
                domain="[('product_id','=',product_id)]",
                ),
        'product_lot_used': fields.function(
                _get_requested_lot,
                type='char',
                store={
                    'sample.product':
                        (lambda s, c, u, ids, ctx: ids, ['product_lot_used_id'], 10),
                    'product.product':
                        (_get_changed_sample_product_ids, ['default_code', 'name'], 15),
                    },
                ),
        }


