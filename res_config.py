from openerp.osv import fields, osv

class fis_integration_config_settings(osv.osv_memory):
    _name = 'fis_integration.config.settings'
    _inherit = "res.config.settings"
    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'traffic_followers': fields.related(
            'company_id', 'traffic_followers_ids',
            type='many2many',
            string='Auto-Followers',
            relation='res.users',
            ),
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
                'traffic_followers': [r.id for r in company.traffic_followers_ids],
            }
        return {'value': values}
    
