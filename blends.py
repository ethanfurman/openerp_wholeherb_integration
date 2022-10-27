# -*- coding: utf-8 -*-

from collections import defaultdict
from fnx_fs.fields import files
from openerp import SUPERUSER_ID
from openerp.exceptions import ERPError
from openerp.osv import fields, osv
from openerp.tools import self_ids
import logging

_logger = logging.getLogger(__name__)


class production_ingredient(osv.Model):
    """
    ingredients have a m2m with orders because a single order can be split into
    multiple steps and each ingredient should be listed with each step
    """
    _name = 'production.ingredient' # (F329) ingredients actually used in the Production Sales Order
    _rec_name = 'item_id'

    def _get_qty_needed_desc(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        if not ids:
            return res
        elif isinstance(ids, (int, long)):
            ids = [ids]
        for record in self.read(cr, uid, ids, fields=['qty_needed', 'qty_desc'], context=context):
            res[record['id']] = '%.2f %s' % (record['qty_needed'], record['qty_desc'] or '')
        return res

    _columns = {
        'name': fields.char('Name', size=19, required=True),  # 'order:item'  (12:6)  (+6 due to order_step_total)
        # order_ids is M2M because a single order can be produced over several production lines
        'order_ids': fields.many2many(
            'production.order',
            'order2ingredients_rel', 'ingredient_id', 'order_id',
            string='Order',
            ),
        'order_state': fields.related(
            'order_ids', 'state',
            string='Order State',
            type='selection',
            selection=[
                ('draft', 'New'),
                ('complete', 'Complete'),
                ('cancelled', 'Cancelled'),
                ]),
        'item_id': fields.many2one('product.product', 'Ingredient', required=True, help='raw ingredient in product table'),
        'item_lot_ids': fields.related(
            'item_id', 'lot_ids',
            string='Item Lots',
            type='one2many',
            relation='wholeherb_integration.product_lot',
            fields_id='product_id',
            ),
        'percent_in_blend': fields.float('% in blend'),
        'lot_id': fields.many2one(
                'wholeherb_integration.product_lot', "Lot #",
                domain="[('product_id','=',item_id)]",
                ),
        'qty_avail': fields.related(
            'item_id', 'qty_available',
            string='Qty Avail.',
            type='float',
            digits=(16,2),
            ),
        'qty_needed': fields.float('Total Qty Needed (value only)'),
        'qty_needed_per_batch': fields.float('Qty/Batch (value only)'),
        'qty_desc': fields.char('Qty Unit', size=8),
        'qty_needed_desc': fields.function(
            _get_qty_needed_desc,
            string='Qty Needed',
            type='char',
            store={
                'production.ingredient': (lambda t, c, u, ids, ctx: ids, ['qty_needed', 'qty_desc'], 10),
                },
            ),
        }

    _sql_constraints = []

    def onchange_lot_id(self, cr, uid, ids, lot_id, item_id, context=None):
        res = {'value': {}, 'domain': {}}
        lot_table = self.pool.get('wholeherb_integration.product_lot')
        lot_entry = lot_table.browse(cr, uid, lot_id, context=context)
        if lot_entry.product_id and lot_entry.product_id.id != item_id:
            res['value']['item_id'] = lot_entry.product_id.id
        return res


class production_order(osv.Model):
    """
    orders have a m2m with ingredients because a single order can be split into
    multiple steps and each ingredient should be listed with each step
    """
    _name = 'production.order' # (F328)  Production Sales Order
    _description = 'production order'
    _order = 'order_no'
    _rec_name = 'order_no'

    _track = {
        'state' : {
            'production.mt_production_draft': lambda s, c, u, r, ctx: r['state'] == 'draft',
            'production.mt_production_complete': lambda s, c, u, r, ctx: r['state'] == 'complete',
            'production.mt_production_cancelled': lambda s, c, u, r, ctx: r['state'] == 'cancelled',
            }
        }

    def _get_orders_from_ingredients(self, cr, uid, ids, context=None):
        product_product = self
        product_ids = ids
        self = product_product.pool.get('production.order')
        # get order ingredient ids that match the product ids
        pd_ingredient = self.pool.get('production.ingredient')
        ingredient_ids = pd_ingredient.search(cr, SUPERUSER_ID, [('item_id','in',product_ids)])
        # get order ids that include the order ingredients
        ids = self.search(cr, SUPERUSER_ID, [('ingredient_ids','in',ingredient_ids)])
        return ids

    _columns = {
        'state': fields.selection([
            ('draft', 'New'),
            ('complete', 'Complete'),
            ('cancelled', 'Cancelled'),
            ],
            string='Status',
            sort_order='definition',
            required=True,
            ),
        'order_no': fields.char('Order #', size=12, required=True, ),
        'item_id': fields.many2one('product.product', 'Item', required=True, help='item being produced'),
        'lot_id': fields.many2one('wholeherb_integration.product_lot', "Final lot #"),
        'finish_date': fields.datetime('Production Finished', oldname='completed', ),
        'special_instructions': fields.text('Special Instructions'),
        # formula info
        'blend_id': fields.many2one('wholeherb_integration.blend', string='Blend', size=64, domain="[('is_valid','=',True)]"),
        'blend_ingredient_ids': fields.related(
            'blend_id','ingredients_ids',
            string='Blend Formula',
            type='one2many',
            relation='wholeherb_integration.blend_ingredient',
            fields_id='blend_id',
            ),
        'batches': fields.integer('Batches needed', ),
        'batch_size': fields.float('Batch size'),
        'produced_qty': fields.float('Qty produced', oldname='qty'),
        'total_yield': fields.float('Total Yield'),
        'ingredient_ids': fields.many2many(
            'production.ingredient',
            'order2ingredients_rel', 'order_id', 'ingredient_id',
            string='Ingredients',
            ),
        }

    _defaults = {
        'state': 'draft',           # also checked for in create() as script may pass False
        }

    def onchange_blend_id(self, cr, uid, ids, blend_id, context=None):
        # TODO: find a way to not have to create production.ingredient records
        #
        # when blend changes:
        # - remove any existing production.ingredient records
        # - create new ones from product_id's from blend_ingredient records
        # - clear existing lot_id
        # - update batches
        # - update qty's
        res = {'value': {}, 'domain': {}}
        value = res['value']
        value['item_id'] = False
        value['lot_id'] = False
        value['batches'] = 0
        value['batch_size'] = 0
        value['total_yield'] = 0
        value['produced_qty'] = 0
        if not blend_id:
            return res
        #
        product_table = self.pool.get('product.product')
        ingredient_table = self.pool.get('production.ingredient')
        blend_table = self.pool.get('wholeherb_integration.blend')
        blend = blend_table.browse(cr, uid, blend_id, context=context)
        product = product_table.browse(cr, uid, [('xml_id','=ilike',blend.code)], context=context)
        if not product:
            raise ERPError('invalid product', 'product %r does not exist in product.product table' % blend.code)
        product = product[0]
        value['item_id'] = product.id
        value['lot_id'] = False
        value['batches'] = batches = blend.numberbatches
        value['batch_size'] = batch_size = blend.batchsize
        value['total_yield'] = blend.amount
        ingredients = []
        for ingred in blend.ingredients_ids:
            batch_qty = batch_size * ingred.percentinblend / 100.0
            total_qty = batch_qty * batches
            ingredients.append(ingredient_table.create(cr, uid, {
                    'name':ingred.product_id.name,
                    'item_id':ingred.product_id.id,
                    'percent_in_blend':ingred.percentinblend,
                    'qty_needed_per_batch':batch_qty,
                    'qty_needed':total_qty,
                    'qty_desc':ingred.product_id.uom_id.name,
                    }))
        # value['ingredient_ids'] = [(6, 0, ingredients)]
        value['ingredient_ids'] = ingredients
        return res


    def onchange_batch(self, cr, uid, ids, batches, ingredient_ids, context=None):
        # if batch size changes, update amounts of all ingredients
        ingredient_table = self.pool.get('production.ingredient')
        new_ids = []
        for old_ingred in ingredient_table.browse(cr, uid, ingredient_ids[0][2], context=context):
            new_ingred = {
                    'name':old_ingred.name,
                    'item_id':old_ingred.item_id.id,
                    'percent_in_blend':old_ingred.percent_in_blend,
                    'qty_needed_per_batch':old_ingred.qty_needed_per_batch,
                    'qty_needed':old_ingred.qty_needed_per_batch*batches,
                    }
            new_ids.append(ingredient_table.create(cr, uid, new_ingred, context=context))
        return {'value': {'ingredient_ids':new_ids}, 'domain': {}}

class product_blend_category(osv.Model):
    _name = 'wholeherb_integration.blend_category'
    _description = 'table data for blend categories'
    _columns = {
        'name' : fields.char('Blend category name', size=62),
        'blends_ids' : fields.one2many(
            'wholeherb_integration.blend',
            'category_name',
            'Blends',
            ),
        }

class product_blend(osv.Model):
    _name = 'wholeherb_integration.blend'
    _description = 'table data for product blends'
    _columns = {
        'code' : fields.char('Code', size=8),
        'name' : fields.char('Name', size=212),
        'packaging' : fields.char('Packaging', size=112),
        'special_instructions' : fields.char('Special Instructions', size=267),
        'category_name' : fields.many2one(
            'wholeherb_integration.blend_category',
            'Category ID',
            required=True,
            ),
        'amount' : fields.float('Amount'),
        'uom' : fields.char('UOM', size=62),
        'batchsize' : fields.float('Batch Size'),
        'numberbatches' : fields.integer('Number Batches'),
        'ingredients_ids' : fields.one2many(
            'wholeherb_integration.blend_ingredient',
            'blend_id',
            'Ingredients',
            ),
        'is_valid': fields.boolean('Usable blend?', help='ingredient percentages must add to 100\n`batch size` * `number of batches` must equal `amount`'),
        'invalid_reason': fields.text('Invalid Reason'),
        }

    def create(self, cr, uid, values, context=None):
        errors = self.is_valid(cr, values, context=context)
        values['is_valid'] = not errors
        if errors:
            values['invalid_reason'] = errors
        return super(product_blend, self).create(cr, uid, values, context=context)

    def write(self, cr, uid, ids, values, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(product_blend, self).write(cr, uid, ids, values, context=context)
        if not any_in (('ingredients_ids','amount','batchsize','numberbatches'), values):
            return res
        #
        for rec in self.browse(cr, uid, ids, context=context):
            update = {}
            errors = self.is_valid(cr, rec, context=context)
            is_valid = not errors
            if rec.is_valid != is_valid:
                update['is_valid'] = is_valid
            if rec.invalid_reason != errors:
                update['invalid_reason'] = errors
            if update:
                self.write(cr, uid, rec.id, update, context=context)
        return res

    def name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            if record.code:
                name = '[%s] %s' % (record.code, record.name)
            else:
                name = record.name
            res.append((record.id, name))
        return res

    def is_valid(self, cr, record, context=None):
        """
        record is either a browse_record or a dictionary of values
        """
        errors = []
        if record['amount'] != record['batchsize'] * record['numberbatches']:
            errors.append('batch size * number of batches <> amount')
        ingredients = record['ingredients_ids']
        total = 0
        if ingredients:
            if isinstance(ingredients, (list, tuple)) and not isinstance(ingredients[0], browse_record):
                ingredients = [i[2] for i in ingredients]
            for ingred in ingredients:
                if ingred['product_id']:
                    total += ingred['percentinblend']
            total = round(total, 2)
        if total != 100.0:
            errors.append('ingredient percentages <> 100%')
        return '\n'.join(errors)

class product_blend_ingredient(osv.Model):
    _name = 'wholeherb_integration.blend_ingredient'
    _description = 'table data for product.blend_ingredient'
    _columns = {
        'blend_id' : fields.many2one(
            'wholeherb_integration.blend',
            'Blend',
            required=True,
            ),
        'product_id' : fields.many2one(
            'product.product',
            'Product',
            required=True,
            ),
        'percentinblend' : fields.float('% in Blend', required=True),
        }


