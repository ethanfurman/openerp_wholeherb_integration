# -*- coding: utf-8 -*-

# from collections import defaultdict
# from fnx_fs.fields import files
# from openerp import SUPERUSER_ID
# from openerp.exceptions import ERPError
from openerp.osv import fields, osv
from openerp.tools import self_ids
import logging

_logger = logging.getLogger(__name__)


class Blend_Categories(osv.Model):
    _name = u'wholeherb_integration.blend_category'
    _description = u'Blend Categories'
    _rec_name = 'name'
    #
    _columns = {
        'name' : fields.char(u'Category Name', size=64, help=''),
        'notes': fields.text(u'Notes', ),
        # 'formula_ids' : fields.one2many(
        #         u'wholeherb_integration.formula', u'category_id',
        #         string=u'Formulas',
        #         help='',
        #         ),
        'blend_ids' : fields.one2many(
                u'wholeherb_integration.blend', u'category_id',
                string=u'Blends',
                help='',
                oldname='blends_ids',
                ),
        }


class Formulas(osv.Model):
    _name = u'wholeherb_integration.formula'
    _description = u'Formulas'
    _rec_name = 'name'

    def _calc_yield(self, cr, uid, ids, field_name, arg, context=None):
        res = {}.fromkeys(ids)
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = rec.batch_size * rec.number_batches
        return res

    def _get_ids_from_ingredient_ids(formula_ingredient, cr, uid, changed_ids, context=None):
        ids = []
        for rec in formula_ingredient.read(cr, uid, changed_ids, ['formula_id'], context=context):
            if rec['formula_id']:
                ids.append(rec['formula_id'][0])
        return ids

    def _is_valid(self, cr, uid, ids, field_names, arg, context=None):
        res = {}
        for formula in self.browse(cr, uid, ids, context=context):
            errors = []
            if formula.amount != formula.batch_size * formula.number_batches:
                errors.append('batch size * number of batches <> amount')
            total = 0
            for ingredient in formula.ingredient_ids:
                if ingredient.product_id:
                    total += ingredient.percent_in_blend
                total = round(total, 2)
            if total != 100.0:
                errors.append('ingredient percentages <> 100%')
            res[formula.id] = {
                    'is_valid': not bool(errors),
                    'invalid_reason': '\n'.join(errors),
                    }
        return res

    _columns = {
        'code' : fields.char(u'Item Code', size=64, help=u'Blend Item Code'),
        'name' : fields.char(u'Blend Name', size=64, help=u'Blend Description'),
        'packaging' : fields.char(u'Packaging', size=85, help=u'Finished packing instructions'),
        'special_instructions' : fields.char(u'Special Instructions', size=225, help=''),
        'category_id' : fields.many2one(
                u'wholeherb_integration.blend_category',
                string=u'Category Id',
                help='',
                ondelete='restrict',
                ),
        'amount' : fields.float(u'Amount', help=u'Amount to blend'),
        'uom' : fields.char(u'UOM', size=64, help=u'Unit of measure'),
        'batch_size' : fields.float(u'Batch Size', help=''),
        'number_batches' : fields.integer(u'Number Batches', help=''),
        # 'total_yield': fields.float('Total Yield'),
        'ingredient_ids' : fields.one2many(
                u'wholeherb_integration.formula_ingredient', u'formula_id',
                string=u'Formula Ingredients',
                help='',
                ),
        # 'blend_ids' : fields.one2many(
        #         u'wholeherb_integration.blend', u'formula_id',
        #         string=u'Blends',
        #         help='',
        #         ),
        'is_valid': fields.function(
                _is_valid,
                multi='is_valid',
                type='boolean',
                string='Usable blend?',
                help='ingredient percentages must add to 100\n`batch size` * `number of batches` must equal `amount`',
                ),
        'invalid_reason': fields.function(
                _is_valid,
                multi='is_valid',
                type='text',
                string='Invalid Reason',
                store={
                    'wholeherb_integration.formula': (self_ids, ['amount','batch_size','number_batches'], 10),
                    'wholeherb_integration.formula_ingredients': (_get_ids_from_ingredient_ids, ['percent_in_blend'], 10),
                    }
                ),
        }

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


class Formula_Ingredients(osv.Model):
    _name = u'wholeherb_integration.formula_ingredient'
    _description = u'Formula Ingredient'
    _rec_name = 'name'

    def _calc_name(self, cr, uid, ids, field_name, args, context=None):
        # name from multiple (fk) fields
        res = {}.fromkeys(ids, False)
        if not ids:
            return res
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = '%s: %s' % (rec.formula_id.name, rec.product_id.name)
        return res

    def _convert_formula_ids(formula, cr, uid, ids, context=None):
        self = formula.pool.get('wholeherb_integration.formula_ingredient')
        ids = self.search(cr, uid, [('formula_id','in',ids)], context=context)
        return ids

    def _convert_product_product_ids(product_product, cr, uid, ids, context=None):
        self = product_product.pool.get('wholeherb_integration.formula_ingredient')
        ids = self.search(cr, uid, [('product_id','in',ids)], context=context)
        return ids

    _columns = {
        'name': fields.function(
                _calc_name,
                string='Name', type='char', size=128,
                store={
                    'wholeherb_integration.formula': (_convert_formula_ids, ['name'], 10),
                    'product.product': (_convert_product_product_ids, ['product_code'], 10),
                    },
                ),
        'formula_id' : fields.many2one(
                u'wholeherb_integration.formula',
                string=u'Blend IC',
                help=u'Blend Item Code',
                ondelete='cascade',
                ),
        'product_id' : fields.many2one(
                u'product.product',
                string=u'Product Number',
                help=u'Same number as in products table',
                ondelete='restrict',
                ),
        'percent_in_blend' : fields.float(u'% in Blend', help=u'% of blend'),
        }


class Blends(osv.Model):
    _name = u'wholeherb_integration.blend'
    _description = u'Blends'
    _rec_name = 'name'

    def _calc_amount(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for blend in self.browse(cr, uid, ids, context=context):
            res[blend.id] = blend.batch_size * blend.number_batches
        return res

    def _calc_totals(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for blend in self.browse(cr, uid, ids, context=context):
            percent = sum([ingred.percent_in_blend for ingred in blend.ingredient_ids], 0.0)
            batch_total = percent * blend.batch_size / 100.0
            blend_total = batch_total * blend.number_batches
            res[blend.id] = {
                    'total_percent': percent,
                    'total_batch': batch_total,
                    'total_amount': blend_total,
                    }
        return res

    def _get_ids_from_ingredient_ids(blend_ingredient, cr, uid, changed_ids, context=None):
        ids = []
        for rec in blend_ingredient.read(cr, uid, changed_ids, ['blend_id'], context=context):
            if rec['blend_id']:
                ids.append(rec['blend_id'][0])
        return ids

    def _is_valid(self, cr, uid, ids, field_names, arg, context=None):
        res = {}
        for blend in self.browse(cr, uid, ids, context=context):
            errors = []
            if blend.amount != blend.batch_size * blend.number_batches:
                errors.append('batch size * number of batches <> amount')
            total = 0
            for ingredient in blend.ingredient_ids:
                if ingredient.product_id:
                    total += ingredient.percent_in_blend
                total = round(total, 2)
            if total != 100.0:
                errors.append('ingredient percentages <> 100%')
            res[blend.id] = {
                    'is_valid': not bool(errors),
                    'invalid_reason': '\n'.join(errors),
                    }
        return res

    _columns = {
        'code' : fields.char(u'Item Code', size=64, help=u'Blend Item Code'),
        'name' : fields.char(u'Blend Name', size=64, help=u'Blend Description'),
        'packaging' : fields.char(u'Packaging', size=85, help=u'Finished packing instructions'),
        'special_instructions' : fields.char(u'Special Instructions', size=225, help=''),
        'category_id' : fields.many2one(
                u'wholeherb_integration.blend_category',
                string=u'Category ID',
                help='',
                ondelete='restrict',
                oldname='category_name',
                ),
        'amount' : fields.function(
                _calc_amount,
                string='Amount',
                type='float',
                digits=(16, 2),
                help='Total amount produced.',
                store={
                        'wholeherb_integration.blend': (self_ids, ['batch_size','number_batches'], 10),
                        },
                ),
        'uom' : fields.char(u'UOM', size=64, help=u'Unit of measure'),
        'batch_size' : fields.float(u'Batch Size', help='', digits=(16, 2), oldname='batchsize'),
        'number_batches' : fields.integer(u'Number Batches', help='', oldname='numberbatches'),
        # 'total_yield': fields.float('Total Yield'),
        'lot_number' : fields.char(u'Lot Number', size=64, help=''),
        'formula_id' : fields.many2one(
                u'wholeherb_integration.formula',
                string=u'Formula Template',
                ),
        'ingredient_ids' : fields.one2many(
                u'wholeherb_integration.blend_ingredient', u'blend_id',
                string=u'Ingredients',
                help='',
                oldname='ingredients_ids',
                ),
        'is_valid': fields.function(
                _is_valid,
                multi='is_valid',
                type='boolean',
                string='Usable blend?',
                help='ingredient percentages must add to 100\n`batch size` * `number of batches` must equal `amount`',
                ),
        'invalid_reason': fields.function(
                _is_valid,
                multi='is_valid',
                type='text',
                string='Invalid Reason',
                store={
                    'wholeherb_integration.blend': (self_ids, ['amount','batch_size','number_batches'], 10),
                    'wholeherb_integration.blend_ingredient': (_get_ids_from_ingredient_ids, ['percent_in_blend'], 10),
                    }
                ),
        'finish_date': fields.date('Finished'),
        'start_date': fields.date('Started'),
        'total_amount': fields.function(
                _calc_totals,
                string='Total in blend',
                type='float',
                digits=(16,2),
                store=False,
                multi='totals',
                ),
        'total_batch': fields.function(
                _calc_totals,
                string='Total in batch',
                type='float',
                digits=(16,2),
                store=False,
                multi='totals',
                ),
        'total_percent': fields.function(
                _calc_totals,
                string='Total percent',
                type='float',
                digits=(16,2),
                store=False,
                multi='totals',
                ),
        }

    def onchange_batch(self, cr, uid, ids, number_batches, batch_size, ingredients, context=None):
        return {'value': {'amount': number_batches * batch_size}}

    def onchange_blend_id(self, cr, uid, ids, formula_id, context=None):
        blend_formula = self.pool.get('wholeherb_integration.formula')
        blend = blend_formula.read(cr, uid, formula_id, context=context)
        formula_ingredient = self.pool.get('wholeherb_integration.formula_ingredient')
        ingredients = formula_ingredient.read(cr, uid, blend.pop('ingredient_ids'), context=context)
        blend['category_id'] = blend.pop('category_id')[0]
        blend['formula_id'] = blend.pop('id')
        blend['ingredient_ids'] = new_ingredients = []
        for ingred in ingredients:
            new_ingred = {'product_id':ingred['product_id'][0], 'percent_in_blend':ingred['percent_in_blend']}
            new_ingredients.append((0, 0, new_ingred))
        return {'value': blend}


class Ingredients(osv.Model):
    _name = u'wholeherb_integration.blend_ingredient'
    _description = u'Ingredients'
    _rec_name = 'name'

    def _calc_qty(self, cr, uid, ids, field_name, args, context=None):
        res = {}.fromkeys(ids, False)
        if not ids:
            return res
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = {
                    'batch_qty': rec.blend_id.batch_size * rec.percent_in_blend / 100.0,
                    'blend_qty': rec.blend_id.batch_size * rec.percent_in_blend * rec.blend_id.number_batches / 100.0,
                    }
        return res

    def _calc_name(self, cr, uid, ids, field_name, args, context=None):
        # name from multiple (fk) fields
        res = {}.fromkeys(ids, False)
        if not ids:
            return res
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = '%s %s' % (rec.product_id.xml_id, rec.product_id.name)
        return res

    def _convert_blend_ids(blend, cr, uid, ids, context=None):
        self = blend.pool.get('wholeherb_integration.blend_ingredient')
        ids = self.search(cr, uid, [('blend_id','in',ids)], context=context)
        return ids

    def _convert_product_product_ids(product_product, cr, uid, ids, context=None):
        self = product_product.pool.get('wholeherb_integration.blend_ingredient')
        ids = self.search(cr, uid, [('product_id','in',ids)], context=context)
        return ids

    _columns = {
        'name': fields.function(
                _calc_name,
                string='Name', type='char', size=128,
                store={
                    'product.product': (_convert_product_product_ids, ['xml_id','name'], 10),
                    },
                ),
        'blend_id' : fields.many2one(
                u'wholeherb_integration.blend',
                string=u'Blend IC',
                help=u'Blend Item Code',
                ondelete='cascade',
                ),
        'product_id' : fields.many2one(
                u'product.product',
                string=u'Product Number',
                help=u'Same number as in products table',
                ondelete='restrict',
                ),
        'percent_in_blend' : fields.float(u'% in Blend', help=u'% of blend', digits=(16, 2), oldname='percentinblend'),
        'batch_qty': fields.function(
                _calc_qty,
                string='Qty/batch',
                type='float',
                digits=(16, 2),
                multi='qtys',
                ),
        'blend_qty': fields.function(
                _calc_qty,
                string='Total Qty',
                type='float',
                digits=(16, 2),
                multi='qtys',
                ),
        'lot_number' : fields.char(u'Lot Number', size=64, help=''),
        }



