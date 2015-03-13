from openerp.osv import fields, osv

class res_company(osv.Model):
    _inherit = "res.company"
    _columns = {
            'traffic_followers_ids': fields.many2many('res.users', 'who_rescompany_rel', 'who_tf_cid', 'who_tf_uid', 'Auto-Followers'),
            }
