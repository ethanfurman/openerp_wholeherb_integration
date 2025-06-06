import logging
from . import xid
from dbf import Date
from fnx_fs.fields import files
from osv import osv, fields
from openerplib.dates import DEFAULT_SERVER_DATE_FORMAT as D_FORMAT


_logger = logging.getLogger(__name__)

CONFIG_ERROR = "Cannot sync products until  Settings --> Configuration --> FIS Integration --> %s  has been specified."


class res_partner(xid.xmlid, osv.Model):
    """Inherits partner and makes the external_id visible
    
    if 'active' is False, do not update last write date
    """
    _name = 'res.partner'
    _inherit = ['res.partner', 'fnx_fs.fs']

    _fnxfs_path = 'res_partner'
    _fnxfs_path_fields = ['xml_id', 'name']

    _columns = {
        'xml_id': fields.char('FIS ID', size=16, readonly=True),
        'module': fields.char('FIS Module', size=16, readonly=True),
        'adb_no': fields.integer('Access DB ID'),
        'sp_non_gmo': fields.boolean(
            'Non-GMO vendor?',
            ),
        'sp_gmo_exp': fields.date(
            'GMO expiration',
            ),
        'sp_kosher': fields.boolean(
            'Kosher?',
            ),
        'sp_kosher_exp': fields.date(
            'Kosher expiration',
            ),
        'sp_tele': fields.char(
            'Telephone',
            size=20,
            ),
        'sp_fax': fields.char(
            'Fax',
            size=20,
            ),
        'sp_telex': fields.char(
            'Telex',
            size=20,
            ),
        'vn_tele': fields.char(
            'Telephone',
            size=20,
            ),
        'vn_fax': fields.char(
            'Fax',
            size=20,
            ),
        'vn_telex': fields.char(
            'Telex',
            size=20,
            ),
        'vn_org_cert': fields.boolean(
            'Organic Cert?',
            ),
        'vn_org_cert_file': fields.boolean(
            'Organic Cert on file?',
            ),
        'vn_org_exp': fields.date(
            'Cert expiration',
            ),
        'ship_to_parent_id': fields.many2one('res.partner', 'Related Ship-To'),
        'ship_to_ids': fields.one2many('res.partner', 'ship_to_parent_id', 'Ship-To Addresses'),
        'create_date': fields.datetime('Created', readonly=True),
        'create_uid': fields.many2one('res.users', string='Created by', readonly=True),
        'write_date': fields.datetime('Last changed', readonly=True),
        'write_uid': fields.many2one('res.users', string='Last changed by', readonly=True),
        'order_confirmations': files('order_confs', string='Order Confirmations', style='static_list', sort='alpha desc'),
        'past_confirmations': files('past_order_confs', string='Past Order Confirmations', style='static_list', sort='alpha desc'),
        'open_invoices': files('invoices', string='Open Invoices', style='static_list', sort='alpha desc'),
        'past_invoices': files('past_invoices', string='Past Invoices', style='static_list', sort='alpha desc'),
        'fis_record': fields.boolean('Record is in FIS'),
        }

    _defaults = {
            'fis_record': False,
            }

    def fnxfs_folder_name(self, records):
        "return name of folder to hold related files"
        res = {}
        for record in records:
            res[record['id']] = record['xml_id'] or ("%s-%d" % (record['name'], record['id']))
        return res


    def write(self, cr, uid, ids, vals, context=None):
        context = (context or {}).copy()
        if 'active' in vals and not vals['active']:
            context['log_write_date'] = False
        return super(res_partner, self).write(cr, uid, ids, vals, context=context)

    def fis_updates(self, cr, uid, *args):
        _logger.info("searching for customers to deactivate...")
        ids = self.search(cr, uid, [('customer','=',True)])
        records = self.read(cr, uid, ids, fields=['id', 'write_date'])
        two_year_cutoff = Date.today().replace(delta_year=-2).strftime(D_FORMAT)
        inactive_ids = []
        for rec in records:
            if rec['write_date'] <= two_year_cutoff:
                inactive_ids.append(rec['id'])
        if inactive_ids:
            self.write(cr, uid, inactive_ids, {'active': False})
        _logger.info('%d records deactivated' % len(inactive_ids))
        return True

    def name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(res_partner, self).name_get(cr, uid, ids, context=context)
        show_fis = (context or {}).get('show_fis')
        if not show_fis:
            return res
        res = dict(res)
        new_res = []
        for data in self.read(cr, uid, ids, fields=['id', 'xml_id', 'module', 'user_ids'], context=context):
            id = data['id']
            xml_id = data['xml_id']
            user_ids = data['user_ids']
            name = res[id]
            if xml_id:
                if not user_ids or show_fis:
                    name = '[%s] %s' % (xml_id, name)
            new_res.append((id, name))
        return new_res
