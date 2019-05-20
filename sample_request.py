from osv import osv, fields
import logging

_logger = logging.getLogger(__name__)


class sample_request(osv.Model):
    _name = 'sample.request'
    _inherit = 'sample.request'

    _columns= {
        'ship_to_parent_id': fields.related(
            'ship_to_id', 'ship_to_parent_id',
            obj='res.partner',
            type='many2one',
            ),
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
        'product_lot_id': fields.many2one(
                'wholeherb_integration.product_lot',
                string='Lot # ID',
                domain="[('product_id','=',product_id),('qty_remain','>',0)]",
                old_name='product_lot_requested_id',
                ),
        'product_lot': fields.function(
                _get_requested_lot,
                type='char',
                string='Lot Number',
                store={
                    'sample.product':
                        (lambda s, c, u, ids, ctx: ids, ['product_lot_id'], 10),
                    'product.product':
                        (_get_changed_sample_product_ids, ['default_code', 'name'], 15),
                    },
                old_name='product_lot_requested'
                ),
        'product_lot_cofo_ids': fields.related(
            'product_lot_id', 'cofo_ids',
            relation='res.country',
            rel='lot_country_rel',
            id1='cid',
            id2='lid',
            type='many2many',
            string='Origin Countries',
            ),
        }
