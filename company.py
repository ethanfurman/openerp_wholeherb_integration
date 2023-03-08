from openerp.osv import fields, osv

class res_company(osv.Model):
    _inherit = "res.company"
    _columns = {
            'traffic_followers_ids': fields.many2many('res.users', 'who_rescompany_rel', 'who_tf_cid', 'who_tf_uid', string='Auto-Followers'),
            'valid_lot_regex': fields.char('Lot No Regex', size=128),
            }
