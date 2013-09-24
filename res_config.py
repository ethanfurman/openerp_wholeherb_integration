from openerp.osv import fields, osv

class fis_integration_config_settings(osv.osv_memory):
    _name = 'fis_integration.config.settings'
    _inherit = "res.config.settings"
    _columns = {
            'company_id': fields.many2one('res.company', 'Company', required=True),
            'product_integration': fields.related('company_id', 'product_integration', type='char', string='Product Module', size=64, help="Module name used for product external ids."),
            'product_category_integration': fields.related('company_id', 'product_category_integration', type='char', string='Product Category', size=64, help="Module name used for product category external ids."),
            'employee_integration': fields.related('company_id', 'employee_integration', type='char', string='Employee Module', size=64, help='Module name used for employee external ids.'),
            'customer_integration': fields.related('company_id', 'customer_integration', type='char', string='Customer Module', size=64, help='Module name used for customer external ids.'),
            'supplier_integration': fields.related('company_id', 'supplier_integration', type='char', string='Supplier/Vendor Module', size=64, help='Module name used for supplier/vendor external ids.'),
    }

    def create(self, cr, uid, values, context=None):
        id = super(fis_integration_config_settings, self).create(cr, uid, values, context)
        # Hack: to avoid some nasty bug, related fields are not written upon record creation.
        # Hence we write on those fields here.
        vals = {}
        for fname, field in self._columns.iteritems():
            if isinstance(field, fields.related) and fname in values:
                vals[fname] = values[fname]
        self.write(cr, uid, [id], vals, context)
        return id

    def _default_company(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.company_id.id

    _defaults = {
        'company_id': _default_company,
        }

    def onchange_company_id(self, cr, uid, ids, company_id, context=None):
        # update related fields
        values = {}
        if company_id:
            company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
            values = {
                'product_integration': company.product_integration,
                'product_category_integration': company.product_category_integration,
                'customer_integration': company.customer_integration,
                'supplier_integration': company.supplier_integration,
                'employee_integration': company.employee_integration,
            }
        return {'value': values}
    
