"""
Summary
=======
Log work on products tracked by lot numbers.

---

Tables
======

In-House
--------

--> **Product In** [[*inhouse.product_in*]] -- original product
--| - **Name** [[*name*]] -- name of process (defaults to process number)
--| - **Process Number** [[*process_number*]] -- assigned number for tracking this product through ***Job Time*** and ***Finished Product***
--| - **Date In**
--| - **Process** [[*process_id*]] - which process will be performed (e.g. *Blend*, *Clean*, or *Mill*)
--| - **Equip to Use** [[*equip_to_use_id*]] -- which equipment will be used (e.g. *V-Blender*, *Box Sifter*, or *Fitz Mill*)
--| - **Product Description** [[*product_id*]] -- product being used
--| - **Raw Lot#** [[*raw_lot_ids*]] -- lot numbers of starting product
--| - **Finished Lot#** [[*finished_lot_ids]] -- lot numbers of final product
--| - **Net Weight In**
--| - **Reason** -- reason for process
--| - **Customer** [[*partner_id*]] -- who finished product is committed to
--| - **Description**
--| - **Screen Size**
--| - **Designated Pack**
--| - **Alcohol Wash**
--| - **Comment**
--| - **Treatment** -- type of bacteria reduction treatment
--| - **Voided Job** [[*voided*]]
--| - **Job Time** [[*job_time_ids]] -- associated jobs
--| - **Finished Product** [[*product_out_ids]] -- associated final products

--> **Job Time** [[inhouse.job_time]] -- jobs performed for a process
--| - **Name** -- name of job (defaults to process number and finished product id)
--| - **Process Number** [[*process_number_id*]]
--| - **Finished Product** [[*product_id*]]
--| - **Lot # Raw** [[*lot_in_ids*]] -- same as *"Product In"."Raw Lot #"*
--| - **Lot # Finished** [[*lot_out_ids*]] -- same as *"Product In"."Finished Lot #"*
--| - **Equipment Prep Time**
--| - **Stage Product Time**
--| - **Packaging Time**
--| - **Wt Check Time**
--| - **QC Check Time**
--| - **Equip Disassembly Time**
--| - **Equip Clean Time**
--| - **Area Clean Time**
--| - **Other Time**
--| - **Machine Run Time**
--| - **Total Man Hours** [[*total_hours*]] -- calculated from *"Equipment Prep Time"* through *"Machine Run Time"*
--| - **Voided Job** [[*voided*]] -- same as *"Product In"."Voided Job"*

--> **Finished Product** [[*inhouse.product_out*]] -- finished product info
--| - **Name** -- (defaults to process number and finished product id)
--| - **Process Number** [[*process_number_id*]]
--| - **Date In**
--| - **Date Finished**
--| - **Released for Sale**
--| - **Finished Product** [[*product_id*]]
--| - **Finished Lot#** [[*finished_lot_ids*]] -- same as *"Product In"."Finished Lot #"*
--| - **Finished Lbs** -- pounds of primary finished product
--| - **Finished Pack** -- pack size and type of primary finished product
--| - **Overs** -- item code and description of overs
--| - **Lot# Overs** [[*over_lot_ids*]]
--| - **Overs Lbs** -- pounds of overs produced
--| - **Overs Pack** -- pack size and type of overs
--| - **Unders** -- item code and description of unders
--| - **Lot# Unders** [[*under_lot_ids*]]
--| - **Unders Lbs** -- pounds of unders produced
--| - **Unders Pack** -- pack size and type of unders
--| - **Magnetic Lbs**
--| - **Waste Lbs**
--| - **Treatment** -- post-process treatment required
--| - **Comments**
--| - **Total Liners Used**
--| - **Voided Job** [[*voided*]] -- same as *"Product In"."Voided Job"*

--> **Lots** [[*wholeherb_integration.product_lot*]] -- track lot # origins/qty
--| - **Lot#** [[*lot_no*]]
--| - **Amount Received** [[*qty_recd*]]
--| - **Received UoM** (Unit of Measure) [[*qty_recd_uom_id]]
--| - **Amount Remaining** [[*qty_remain*]]
--| - **Previous Lot#** [[*prev_lot_no_id*]]
--| - **Product** [[*product_id*]]
--| - **Supplier** [[*supplier_id*]]
--| - **Country of Origin** [[*cofo_ids]]
--| - **Valid Lot Number** [[*lot_no_valid**]]
--| - **Possibly Valid Lot Number** [[*lot_no_maybe*]] -- omit obviously invalid product lot numbers (zone/type/platform/etc.)
--| - **Pre-Ship Lot?**

--> **Processes** [[*inhouse.selection.process*]] -- available processes for In-House jobs
--| - **Name**
--| - **Active** -- available for selection

--> **Equipment** [[inhouse.selection.equip_to_use*]] -- available equipment for In-House jobs
--| - **Name**
--| - **Active** -- available for selection

Outside
-------

--> **aoeu**
--|
--|
"""

from collections import defaultdict
from osv import osv, fields
from openerp.tools import self_ids
import logging

_logger = logging.getLogger(__name__)


class product_in_process_selection(osv.Model):
    _name = 'inhouse.selection.process'
    _columns = {
            'name' : fields.char(string='Process', size=64, required=True),
            'active' : fields.boolean(string='Available', help='Only available items are selectable.')
            }
    _sql_constraints = [
            ('name_unique', 'unique(name)', 'Name already exists.'),
            ]


class product_in_equip_to_use_selection(osv.Model):
    _name = 'inhouse.selection.equip_to_use'
    _columns = {
            'name' : fields.char(string='Equip To Use', size=64, required=True),
            'active' : fields.boolean(string='Available', help='Only available items are selectable.')
            }
    _sql_constraints = [
            ('name_unique', 'unique(name)', 'Name already exists.'),
            ]


class Product_In_Info(osv.Model):
    _name = 'inhouse.product_in'
    _description = 'Product In Info'
    _rec_name = 'name'
    _order = 'process_number desc'
    #
    def _calc_name(self, cr, uid, ids, field_name, args, context=None):
        # name from own non-string field
        res = {}.fromkeys(ids, False)
        if not ids:
            return res
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = '%s' % (rec.process_number, )
        return res
    #
    def _select_process(self, cr, uid, context=None):
        obj = self.pool.get('inhouse.selection.process')
        ids = obj.search(cr, uid, [])
        res = obj.read(cr, uid, ids, ['name', 'id'], context)
        res = [(r['id'], r['name']) for r in res]
        return res
    #
    def _select_equip_to_use(self, cr, uid, context=None):
        obj = self.pool.get('inhouse.selection.equip_to_use')
        ids = obj.search(cr, uid, [])
        res = obj.read(cr, uid, ids, ['name', 'id'], context)
        res = [(r['id'], r['name']) for r in res]
        return res
    #
    _columns = {
        'name': fields.function(
                _calc_name,
                string='Name', type='char', size=128,
                store={
                    'inhouse.product_in': (self_ids, ['process_number'], 10),
                    },
                ),
        'process_number' : fields.integer('Process Number', help=''),
        'date_in' : fields.datetime('Date In', help=''),
        'process_id' : fields.many2one('inhouse.selection.process', string='Process', oldname='process', help='Process to be done'),
        'equip_to_use_id' : fields.many2one('inhouse.selection.equip_to_use', string='Equip To Use', oldname='equip_to_use', help='Machine to use for job'),
        'product_id' : fields.many2one(
                'product.product',
                string='Product Description',
                required=True,
                help='Item Code & Description of product going into process',
                ),
        'raw_lot_ids' : fields.many2many(
                'wholeherb_integration.product_lot',
                'inhouse_product_in_rel', 'product_in_id', 'lot_id',
                string='Raw Lot#',
                domain=[('lot_no_valid','=',True)],
                help='Preprocess lot#',
                ),
        'finished_lot_ids' : fields.many2many(
                'wholeherb_integration.product_lot',
                'inhouse_product_out_rel', 'product_out_id', 'lot_id',
                string='Finished Lot#',
                domain=[('lot_no_valid','=',True)],
                help='Lot# of finished product',
                ),
        'net_weight_in' : fields.char('Net Weight In', size=64, help='Net weight and pack of product going into process'),
        'reason' : fields.char('Reason', size=128, help='Reason for process'),
        'partner_id': fields.many2one(
                'res.partner',
                string='Customer',
                domain=[('customer','=',1),('is_company','=',1)],
                help='Customer(s) that finished product is commited to',
                ),
        'description' : fields.char('Description', size=128),
        'screen_size' : fields.char('Screen Size', size=64, help='Mesh size to use on sifter'),
        'designated_pack' : fields.char('Designated Pack', size=64, help='Designated pack size & type of finished product'),
        'alcohol_wash' : fields.boolean('Alcohol Wash', help='Alcohol wash equipment before process?'),
        'comment' : fields.text('Comment', help=''),
        'treatment' : fields.char('Treatment', size=64, help='Type of bacteria reduction treatment after processing & lbs to go'),
        'voided' : fields.boolean('Voided Job', help=''),
        'job_time_ids' : fields.one2many(
                'inhouse.job_time', 'process_number_id',
                string='Job Time',
                help='',
                oldname='job_time_process_number_ids',
                ),
        'product_out_ids' : fields.one2many(
                'inhouse.product_out', 'process_number_id',
                string='Finished Product',
                help='',
                oldname='product_out_process_number_ids',
                ),
        'create_date': fields.datetime('Date record created'),
        }
    #
    _sql_constraints = [
            ('number_unique', 'unique(process_number)', 'Process # already exists.'),
            ]
    #
    def create(self, cr, uid, values, context=None):
        if 'process_number' not in values or not values['process_number']:
            values['process_number'] = int(self.pool.get('ir.sequence').next_by_code(cr, uid, 'inhouse.product_in', context=context))
        process_in_id = super(Product_In_Info, self).create(cr, uid, values, context)
        # now create matching job time and product out entries
        self.pool.get('inhouse.job_time').create(cr, uid, {'process_number_id':process_in_id, 'product_id':values['product_id']}, context=context)
        self.pool.get('inhouse.product_out').create(cr, uid, {'process_number_id':process_in_id, 'product_id':values['product_id']}, context=context)
        return process_in_id


class Job_Time(osv.Model):
    _name = 'inhouse.job_time'
    _description = 'Job Time'
    _rec_name = 'name'
    _order = 'name desc'
    #
    def _calc_name(self, cr, uid, ids, field_name, args, context=None):
        # name from multiple (fk) fields
        res = {}.fromkeys(ids, False)
        if not ids:
            return res
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = '%s: %s' % (rec.process_number_id.process_number, rec.product_id.xml_id)
        return res
    #
    def _calc_time(self, cr, uid, ids, field_name, args, context=None):
        res = {}.fromkeys(ids, 0)
        for rec in self.browse(cr, uid, ids, context=context):
            hours = 0
            for time in (
                    'equipment_prep_time', 'stage_product_time', 'packaging_time', 'wt_check_time', 'qc_check_time',
                    'equip_disassembly_time', 'equip_clean_time', 'area_clean_time', 'other_time', 'machine_run_time',
                ):
                hours += rec[time]
            res[rec.id] = hours
        return res

    #
    def _convert_product_in_ids(product_in, cr, uid, ids, context=None):
        self = product_in.pool.get('inhouse.job_time')
        self_ids = self.search(cr, uid, [('process_number_id','in',ids)], context=context)
        return self_ids
    #
    def _convert_product_product_ids(product_product, cr, uid, ids, context=None):
        self = product_product.pool.get('inhouse.job_time')
        self_ids = self.search(cr, uid, [('product_id','in',ids)], context=context)
        return self_ids
    #
    _columns = {
        'name': fields.function(
                _calc_name,
                string='Name', type='char', size=128,
                store={
                    'inhouse.job_time': (self_ids, ['process_number_id','product_id'], 10),
                    'inhouse.product_in': (_convert_product_in_ids, ['process_number'], 10),
                    'product.product': (_convert_product_product_ids, ['name'], 10),
                    },
                ),
        'process_number_id' : fields.many2one(
                'inhouse.product_in',
                string='Process Number',
                required=True,
                help='',
                ),
        'product_id' : fields.many2one(
                'product.product',
                string='Finished Product',
                required=True,
                help='',
                ),
        'lot_in_ids' : fields.related(
                'process_number_id','raw_lot_ids',
                relation='wholeherb_integration.product_lot',
                rel='inhouse_job_time_lot_in_rel',
                id1='product_in_id',
                id2='lot_id',
                string='Lot# Raw',
                type='many2many',
                help='Preprocess lot#',
                domain=[('lot_no_valid','=',True)],
                ),
        'lot_out_ids' : fields.related(
                'process_number_id', 'finished_lot_ids',
                relation='wholeherb_integration.product_lot',
                rel='inhouse_job_time_lot_out_rel',
                id1='job_id',
                id2='lot_id',
                string='Lot# Finished',
                type='many2many',
                domain=[('lot_no_valid','=',True)],
                help='Finished lot#',
                ),
        'equipment_prep_time' : fields.float('Equipment Prep Time', digits=(10,2), help=''),
        'stage_product_time' : fields.float('Stage Product Time', digits=(10,2), help=''),
        'packaging_time' : fields.float('Packaging Time', digits=(10,2), help='Man hours to assemble packaging'),
        'wt_check_time' : fields.float('Wt Check Time', digits=(10,2), help='Man hours to check weights'),
        'qc_check_time' : fields.float('QC Check Time', digits=(10,2), help='Man hours to obtain QA approval of initial run'),
        'equip_disassembly_time' : fields.float('Equip Disassembly Time', digits=(10,2), help=''),
        'equip_clean_time' : fields.float('Equip Clean Time', digits=(10,2), help=''),
        'area_clean_time' : fields.float('Area Clean Time', digits=(10,2), help=''),
        'other_time' : fields.float('Other Time', digits=(10,2), help='Misc. time associated with the job'),
        'machine_run_time' : fields.float('Machine Run Time', digits=(10,2), help='Time machine actually ran'),
        'total_hours' : fields.function(
                _calc_time,
                type='float',
                string='Total Man Hours',
                digits=(10,2),
                help='Total hours billed to job',
                oldname='total_man_hours',
                ),
        'voided' : fields.related(
                'process_number_id','voided',
                string='Voided Job',
                type='boolean',
                help='',
                ),
        }


class Finished_Product_Info(osv.Model):
    _name = 'inhouse.product_out'
    _description = 'Finished Product Info'
    _rec_name = 'name'
    _order = 'name desc'
    #
    def _calc_name(self, cr, uid, ids, field_name, args, context=None):
        # name from multiple (fk) fields
        res = {}.fromkeys(ids, False)
        if not ids:
            return res
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = '%s: %s' % (rec.process_number_id.process_number, rec.product_id.xml_id)
        return res
    #
    def _convert_product_in_ids(product_in, cr, uid, ids, context=None):
        self = product_in.pool.get('inhouse.product_out')
        self_ids = self.search(cr, uid, [('process_number_id','in',ids)], context=context)
        return self_ids
    #
    def _convert_product_product_ids(product_product, cr, uid, ids, context=None):
        self = product_product.pool.get('inhouse.product_out')
        self_ids = self.search(cr, uid, [('product_id','in',ids)], context=context)
        return self_ids
    #
    _columns = {
        'name': fields.function(
                _calc_name,
                string='Name', type='char', size=128,
                store={
                    'inhouse.product_out': (self_ids, ['process_number_id','product_id'], 10),
                    'inhouse.product_in': (_convert_product_in_ids, ['process_number'], 10),
                    'product.product': (_convert_product_product_ids, ['name'], 10),
                    },
                ),
        'process_number_id' : fields.many2one(
                'inhouse.product_in',
                string='Process Number',
                required=True,
                help='',
                ),
        'date_in': fields.date('Date In'),
        'date_finished' : fields.date('Date Finished', help='Date job was completed'),
        'released_for_sale' : fields.boolean('Released For Sale', help='Has the product been released for shipment to customers?'),
        'product_id' : fields.many2one(
                'product.product',
                string='Finished Product',
                required=True,
                help='Item Code & Description of primary finished product',
                ),
        'finished_lot_ids' : fields.related(
                'process_number_id', 'finished_lot_ids',
                relation='wholeherb_integration.product_lot',
                rel='inhouse_product_out_rel',
                id1='product_out_id',
                id2='lot_id',
                string='Finished Lot#',
                type='many2many',
                domain=[('lot_no_valid','=',True)],
                help='Lot# of primary finished product',
                ),
        'finished_lbs' : fields.char('Finished LBS', size=64, help='Pounds of primary finished product produced'),
        'finished_pack' : fields.char('Finished Pack', size=128, help='Pack size & type of primary finished product'),
        'overs' : fields.char('Overs', size=64, help='Item Code & Description of overs'),
        'over_lot_ids' : fields.many2many(
                'wholeherb_integration.product_lot',
                'inhouse_product_out_over_id', 'product_out_id', 'lot_id',
                string='Lot# Overs',
                domain=[('lot_no_valid','=',True)],
                help='Lot# of overs',
                ),
        'overs_lbs' : fields.char('Overs LBS', size=64, help='Pounds of overs produced'),
        'overs_pack' : fields.char('Overs Pack', size=64, help='Pack size & type of overs'),
        'unders' : fields.char('Unders', size=64, help='Item Code & Description of unders'),
        'under_lot_ids' : fields.many2many(
                'wholeherb_integration.product_lot',
                'inhouse_product_out_under_id', 'product_out_id', 'lot_id',
                string='Lot# Unders',
                domain=[('lot_no_valid','=',True)],
                help='Lot# of unders',
                ),
        'unders_lbs' : fields.char('Unders LBS', size=64, help='Pounds of unders produced'),
        'unders_pack' : fields.char('Unders Pack', size=64, help='Pack size & type of unders'),
        'magnetic_lbs' : fields.char('Magnetic LBS', size=64, help='Pounds of magnetic waste produced'),
        'waste_lbs' : fields.char('Waste LBS', size=64, help='Pounds of other waste produced (hopper, floor, ect.)'),
        'treatment' : fields.char('Treatment', size=64, help='Post process treatment required and pounds to go'),
        'comments' : fields.text('Comments', help=''),
        'total_liners_used' : fields.char('Total Liners Used', size=64, help='Total number of poly liners used for job'),
        'voided' : fields.related(
                'process_number_id','voided',
                string='Voided Job',
                type='boolean',
                help='',
                ),
        }


class OutsideProcessing(osv.Model):
    _name = 'outside.process'
    _description = 'Outside process record'
    _order = 'process_number desc'
    #
    def _calc_name(self, cr, uid, ids, field_name, args, context=None):
        # name from own non-string field
        res = {}.fromkeys(ids, False)
        if not ids:
            return res
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = '%s' % (rec.process_number, )
        return res
    #
    def _generate_order_by(self, order_spec, query):
        order_spec = super(OutsideProcessing, self)._generate_order_by(order_spec, query)
        if order_spec and '"outside_process"."name"' in order_spec:
            order_spec = order_spec.replace('"outside_process"."name"', 'cast("outside_process"."name" as int)')
        return order_spec
    #
    _columns = {
        'name': fields.function(
                _calc_name,
                string='ID', type='char', size=128,
                store={
                    'outside.process': (self_ids, ['process_number'], 10),
                    },
                ),
        'process_number' : fields.integer('Process number', help=''),
        'finished_lot_ids' : fields.many2many(
                'wholeherb_integration.product_lot',
                'outside_process_lot_out_rel', 'process_id', 'lot_id',
                string='Finished Lot#',
                domain=[('lot_no_maybe','=',True)],
                help='Lot# of finished product',
                ),
        'product_out_id' : fields.many2one(
                'product.product',
                string='Finished Product',
                required=False,
                help='',
                ),
        'date_sent' : fields.date('Date sent', help=''),
        'status': fields.char('Status', size=30),
        'date_qa_release': fields.date('QA release'),
        'comments': fields.text('Comments'),
        'raw_lot_ids' : fields.many2many(
                'wholeherb_integration.product_lot',
                'outside_process_lot_in_rel', 'process_id', 'lot_id',
                string='Raw Lot#',
                domain=[('lot_no_maybe','=',True)],
                help='Preprocess lot#',
                ),
        'product_in_ids' : fields.many2many(
                'product.product',
                'outside_process_product_in_rel', 'process_id', 'product_id',
                string='Raw product',
                required=False,
                help='Item Code & Description of product going into process',
                ),
        'sent_lbs': fields.float('Lbs sent to processor'),
        'customer': fields.char('Customer', size=112),
        'tests_req': fields.char('Tests required', size=112),
        'sales_rep': fields.char('Sales rep', size=62),
        'raw_supplier': fields.char('Raw material supplier', size=112),
        'returned_lbs': fields.float('Lbs returned'),
        'percent_loss': fields.float('Percent loss'),
        'date_eta': fields.date('ETA'),
        'date_revised_eta': fields.date('Revised ETA'),
        'date_order_ship': fields.date('Order shipped'),
        'processor_id': fields.many2one('outside.processor', string='Outside company'),
        'process_id' : fields.many2one('outside.selection.process', string='Process', help='Process to be done'),
        'create_date': fields.datetime('Date record created'),
        }
    #
    _sql_constraints = [
            ('number_unique', 'unique(process_number)', 'Record # already exists.'),
            ]
    #
    def create(self, cr, uid, values, context=None):
        if 'process_number' not in values or not values['process_number']:
            values['process_number'] = self.pool.get('ir.sequence').next_by_code(cr, uid, 'outside.process', context=context)
        return super(OutsideProcessing, self).create(cr, uid, values, context=context)


class OutsideProcessor(osv.Model):
    _name = 'outside.processor'
    _description = 'Outside process company'
    _order = 'code'
    
    _columns = {
            'code': fields.char('Code', size=16),
            'name': fields.char('Name', size=128),
            }

class OutsideProcess(osv.Model):
    _name = 'outside.selection.process'
    _description = 'Outside process'

    _columns = {
            'name': fields.char('Process', size=64),
            }

class BlendingLotLog(osv.Model):
    _name = 'inhouse.blend.lot'
    _rec_name = 'lot_no'
    _order = 'lot_no desc'

    def _duplicate_check(self, cr, uid, ids, field_name, args, context=None):
        res = {}.fromkeys(ids, False)
        if not ids:
            return res
        # get lot numbers from ids
        lots = [r['lot_no'] for r in self.read(cr, uid, ids, fields=['lot_no'], context=context)]
        # get all records for matching lot numbers
        lot_ids = [(r['id'], r['lot_no']) for r in self.read(cr, uid, [('lot_no','in',lots)], fields=['id','lot_no'], context=context)]
        dupes = defaultdict(list)
        for lot_id, lot_no in lot_ids:
            dupes[lot_no].append(lot_id)
        # find any duplicates
        for lot_no, lot_ids in dupes.items():
            if len(lot_ids) > 1:
                for lot_id in lot_ids:
                    if lot_id in ids:
                        res[lot_id] = True
        return res

    def _duplicate_search(self, cr, uid, obj, name, args, context=None):
        res = []
        field, op, arg = args[0]
        if (op, arg) in (('=', True),('!=',False)):
            duplicate = True
        elif (op, arg) in (('=',False),('!=',True)):
            duplicate = False
        else:
            raise ValueError('unknown search term: %r' % (args, ))
        # get all records
        lot_ids = [(r['id'], r['lot_no']) for r in self.read(cr, uid, [(1,'=',1)], fields=['id','lot_no'], context=context)]
        grouped = defaultdict(list)
        for lot_id, lot_no in lot_ids:
            grouped[lot_no].append(lot_id)
        # find any duplicates
        for lot_no, lot_ids in grouped.items():
            if len(lot_ids) > 1 and duplicate:
                res.extend(lot_ids)
            elif len(lot_ids) == 1 and not duplicate:
                res.extend(lot_ids)
        return [('id','in',res)]

    def _get_text(self, cr, uid, ids, field_name, args, context=None):
        res = {}
        if not ids:
            return res
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = {}
            value = False
            if rec.product_id:
                value = ': '.join(f for f in [rec.product_id.xml_id, rec.product_id.name] if f)
            elif rec.product_code or rec.product_desc:
                value = ': '.join(f for f in [rec.product_code, rec.product_desc] if f)
            res[rec.id]['product'] = value
            value = False
            if rec.customer_id:
                value = ': '.join(f for f in [rec.customer_id.xml_id, rec.customer_id.name] if f)
            elif rec.customer_desc:
                value = rec.customer_desc
            res[rec.id]['customer'] = value
        return res


    _columns = {
			'lot_no': fields.char(string='Lot #', size=6),
			'product_id': fields.many2one('product.product', string='Product'),
            'product_code': fields.char(string='Item Code', size=6, help='use if product not in system'),
			'product_desc': fields.char(string='Item Name/Description', size=60, help='use if product not in system'),
            'product': fields.function(
                    _get_text,
                    type='char',
                    size=60,
                    string='Product',
                    multi='tree_text',
                    ),
            'customer_id': fields.many2one('res.partner', string='Customer'),
			'customer_desc': fields.char(string='Customer Description', size=60, help='use if customer not in system'),
            'customer': fields.function(
                    _get_text,
                    type='char',
                    size=60,
                    string='Customer Name',
                    multi='tree_text',
                    ),
            'salesrep_id': fields.many2one('res.users', string='Sales Rep'),
			'salesrep_desc': fields.char(string='Rep', size=10, help='use if sales rep not in system'),
			'date_entered': fields.date(string='Date Entered'),
			'lbs': fields.float(string='Lbs to Produce'),
			'comment': fields.text(string='Comments'),
			'order_no': fields.char(string='Order #', size=6),
            'is_duplicate': fields.function(
                    _duplicate_check,
                    fnct_search=_duplicate_search,
                    type='boolean',
                    string='Duplicate?',
                    ),
            'is_deleted': fields.boolean('Deleted?'),
            'is_sample': fields.boolean('Sample?'),
            }

    def onchange_lot_no(self, cr, uid, ids, lot_no, context=None):
        print('ids:', ids)
        print('lot_no:', lot_no)
        res = {'value': {}, 'domain': {}}
        # get all records for matching lot numbers
        lot_ids = [(r['id'], r['lot_no']) for r in self.read(cr, uid, [('lot_no','=',lot_no)], fields=['id','lot_no'], context=context)]
        duplicate = False
        for lot_id, lot_no in lot_ids:
            if lot_id not in ids:
                duplicate = True
        res['value']['is_duplicate'] = duplicate
        return res
                
