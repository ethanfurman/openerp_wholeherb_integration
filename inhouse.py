from osv import osv, fields
from openerp.tools import self_ids


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
        'process' : fields.selection(_select_process, string='Process', oldname='process_id', help='Process to be done', size=-1),
        'equip_to_use' : fields.selection(_select_equip_to_use, string='Equip To Use', oldname='equip_to_use_id', help='Machine to use for job', size=-1),
        'product_id' : fields.many2one(
                'product.product',
                string='Product Description',
                help='Item Code & Description of product going into process',
                ),
        'lot_ids' : fields.many2many(
                'wholeherb_integration.product_lot',
                'inhouse_product_in_rel', 'product_in_id', 'lot_id',
                string='Raw Lot#',
                help='Lot# of product going into process',
                ),
        'net_weight_in' : fields.char('Net Weight In', size=64, help='Net weight and pack of product going into process'),
        'reason' : fields.char('Reason', size=128, help='Reason for process'),
        'partner_id': fields.many2one(
                'res.partner',
                string='Customer',
                domain=[('customer','=',1)],
                help='Customer(s) that finished product is commited to',
                ),
        'description' : fields.char('Description', size=128),
        'screen_size' : fields.char('Screen Size', size=64, help='Mesh size to use on sifter'),
        'designated_pack' : fields.char('Designated Pack', size=64, help='Designated pack size & type of finished product'),
        'alcohol_wash' : fields.boolean('Alcohol Wash', help='Alcohol wash equipment before process?'),
        'comment' : fields.text('Comment', help=''),
        'treatment' : fields.char('Treatment', size=64, help='Type of bacteria reduction treatment after processing & lbs to go'),
        'voided' : fields.boolean('Voided Job', help=''),
        'job_time_process_number_ids' : fields.one2many(
                'inhouse.job_time', 'process_number_id',
                string='Job Time',
                help='',
                ),
        'product_out_process_number_ids' : fields.one2many(
                'inhouse.product_out', 'process_number_id',
                string='Finished Product Info',
                help='',
                ),
        }


class Job_Time(osv.Model):
    _name = 'inhouse.job_time'
    _description = 'Job Time'
    _rec_name = 'name'
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
                    'machine_run_time', 'equip_disassembly_time', 'equip_clean_time', 'area_clean_time', 'other_time',
                ):
                hours += rec[time]
            # hours, minutes = divmod(hours, 1)
            # minutes = minutes * 60
            # if minutes < 5:
            #     minutes = 0.0
            # elif minutes < 10:
            #     minutes = 0.15
            # elif minutes < 16:
            #     minutes = 0.25
            # elif minutes < 25:
            #     minutes = 0.40
            # elif minutes <= 31:
            #     minutes = 0.50
            # elif minutes < 37:
            #     minutes = 0.60
            # elif minutes < 46:
            #     minutes = 0.75
            # elif minutes < 52:
            #     minutes = 0.85
            # else:
            #     minutes = 1
            # res[rec.id] = hours + minutes
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
                    'inhouse.product_in': (_convert_product_in_ids, ['process_number'], 10),
                    'product.product': (_convert_product_product_ids, ['product'], 10),
                    },
                ),
        'lot_in_ids' : fields.many2many(
                'wholeherb_integration.product_lot',
                'inhouse_job_time_lot_in_rel', 'job_id', 'lot_id',
                string='Lot# Raw',
                help='Preprocess lot#',
                ),
        'lot_out_ids' : fields.many2many(
                'wholeherb_integration.product_lot',
                'inhouse_job_time_lot_out_rel', 'job_id', 'lot_id',
                string='Lot# Finished',
                help='Finished lot#',
                ),
        'process_number_id' : fields.many2one(
                'inhouse.product_in',
                string='Process Number',
                help='',
                ),
        'product_id' : fields.many2one(
                'product.product',
                string='Finished Product Desc',
                help='',
                ),
        'equipment_prep_time' : fields.float('Equipment Prep Time', digits=(10,2), help=''),
        'stage_product_time' : fields.float('Stage Product Time', digits=(10,2), help=''),
        'packaging_time' : fields.float('Packaging Time', digits=(10,2), help='Man hours to assemble packaging'),
        'wt_check_time' : fields.float('Wt Check Time', digits=(10,2), help='Man hours to check weights'),
        'qc_check_time' : fields.float('QC Check Time', digits=(10,2), help='Man hours to obtain QA approval of initial run'),
        'machine_run_time' : fields.float('Machine Run Time', digits=(10,2), help='Time machine actually ran'),
        'equip_disassembly_time' : fields.float('Equip Disassembly Time', digits=(10,2), help=''),
        'equip_clean_time' : fields.float('Equip Clean Time', digits=(10,2), help=''),
        'area_clean_time' : fields.float('Area Clean Time', digits=(10,2), help=''),
        'other_time' : fields.float('Other Time', digits=(10,2), help='Misc. time associated with the job'),
        'total_hours' : fields.function(
                _calc_time,
                type='float',
                string='Total Hours',
                digits=(10,2),
                help='Total hours billed to job',
                oldname='total_man_hours',
                ),
        }


class Finished_Product_Info(osv.Model):
    _name = 'inhouse.product_out'
    _description = 'Finished Product Info'
    _rec_name = 'name'
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
                    'inhouse.product_in': (_convert_product_in_ids, ['process_number'], 10),
                    'product.product': (_convert_product_product_ids, ['product'], 10),
                    },
                ),
        'process_number_id' : fields.many2one(
                'inhouse.product_in',
                string='Process Number',
                help='',
                ),
        'date_finished' : fields.date('Date Finished', help='Date job was completed'),
        'released_for_sale' : fields.boolean('Released For Sale', help='Has the product been released for shipment to customers?'),
        'product_id' : fields.many2one(
                'product.product',
                string='Finished Product',
                help='Item Code & Description of primary finished product',
                ),
        'finished_lot_ids' : fields.many2many(
                'wholeherb_integration.product_lot',
                'inhouse_product_out_finished_id', 'product_out_id', 'lot_id',
                string='Lot# Finished1',
                help='Lot# of primary finished product',
                ),
        'finished_lbs' : fields.char('Finished LBS', size=64, help='Pounds of primary finished product produced'),
        'finished_pack' : fields.char('Finished Pack', size=128, help='Pack size & type of primary finished product'),
        'overs' : fields.char('Overs', size=64, help='Item Code & Description of overs'),
        'over_lot_ids' : fields.many2many(
                'wholeherb_integration.product_lot',
                'inhouse_product_out_over_id', 'product_out_id', 'lot_id',
                string='Lot# Overs',
                help='Lot# of overs',
                ),
        'overs_lbs' : fields.char('Overs LBS', size=64, help='Pounds of overs produced'),
        'overs_pack' : fields.char('Overs Pack', size=64, help='Pack size & type of overs'),
        'unders' : fields.char('Unders', size=64, help='Item Code & Description of unders'),
        'under_lot_ids' : fields.many2many(
                'wholeherb_integration.product_lot',
                'inhouse_product_out_under_id', 'product_out_id', 'lot_id',
                string='Lot# Unders',
                help='Lot# of unders',
                ),
        'unders_lbs' : fields.char('Unders LBS', size=64, help='Pounds of unders produced'),
        'unders_pack' : fields.char('Unders Pack', size=64, help='Pack size & type of unders'),
        'magnetic_lbs' : fields.char('Magnetic LBS', size=64, help='Pounds of magnetic waste produced'),
        'waste_lbs' : fields.char('Waste LBS', size=64, help='Pounds of other waste produced (hopper, floor, ect.)'),
        'treatment' : fields.char('Treatment', size=64, help='Post process treatment required and pounds to go'),
        'comments' : fields.text('Comment', help=''),
        'total_liners_used' : fields.char('Total Liners Used', size=64, help='Total number of poly liners used for job'),
        'voided' : fields.boolean('Voided Job', help=''),
        }


