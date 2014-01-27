from openerp.osv import fields, osv

class res_company(osv.Model):
    _inherit = "res.company"
    _columns = {
            'product_integration': fields.char('Product Module', size=64, help="Module name used for product external ids."),
            'product_category_integration': fields.char('Product Category', size=64, help="Module name used for product category external ids."),
            'employee_integration': fields.char('Employee Module', size=64, help='Module name used for employee external ids.'),
            'customer_integration': fields.char('Customer Module', size=64, help='Module name used for customer external ids.'),
            'supplier_integration': fields.char('Supplier/Vendor Module', size=64, help='Module name used for supplier/vendor external ids.'),
            }
res_company()
