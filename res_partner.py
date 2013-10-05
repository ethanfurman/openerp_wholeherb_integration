import enum
import logging
from fnx import xid, check_company_settings
from fnx.BBxXlate.fisData import fisData
from fnx import cszk, fix_phone, fix_date, Rise, Sift, AddrCase, NameCase, BsnsCase, normalize_address
from osv import osv, fields

_logger = logging.getLogger(__name__)

CONFIG_ERROR = "Cannot sync products until  Settings --> Configuration --> FIS Integration --> %s  has been specified." 

class FISenum(str, enum.Enum):
    pass

class C(FISenum):
    'Customers from CSMS'
    code =       'An$(3,6)'
    name =       'Bn$'
    addr1 =      'Cn$'
    addr2 =      'Dn$'
    addr3 =      'En$'
    postal =     'Ln$'
    phone =      'Gn$(20,10)'
    fax =        'Gn$(31,15)'
    addl_phone = 'Gn$(46,15)'
    sales_mgr =  'Jn$(10,3)'

class V(FISenum):
    'Vendors from VNMS'
    code =        'An$(3,6)'
    name =        'Bn$'
    addr1 =       'Cn$'
    addr2 =       'Dn$'
    addr3 =       'En$'
    phone =       'Gn$(1,15)'
    fax =         'Gn$(16,15)'
    telex =       'Gn$(31,15)'
    is_broker =   'In$(5,1)'
    broker_code = 'In$(6,3)'
    contact =     'Nn$'

class S(FISenum):
    'Suppliers from POSM'
    code =  'An$(3,6)'
    name =  'Bn$'
    addr1 = 'Cn$'
    addr2 = 'Dn$'
    addr3 = 'En$'
    phone = 'Gn$(1,15)'
    fax =   'Gn$(16,15)'
    telex = 'Gn$(31,15)'


class res_partner(osv.Model):
    "Inherits partner and makes the external_id visible and modifiable"
    _name = 'res.partner'
    _inherit = 'res.partner'

    _columns = {
        'xml_id': fields.function(
            xid.get_xml_ids,
            arg=(
                ('supplier_integration', 'Supplier/Vendor Module', CONFIG_ERROR),
                ('customer_integration', 'Customer Module', CONFIG_ERROR)
                ),
            fnct_inv=xid.update_xml_id,
            string="FIS ID",
            type='char',
            method=False,
            fnct_search=xid.search_xml_id,
            multi='external',
            ),
        'module': fields.function(
            xid.get_xml_ids,
            arg=(
                ('supplier_integration', 'Supplier/Vendor Module', CONFIG_ERROR),
                ('customer_integration', 'Customer Module', CONFIG_ERROR)
                ),
            fnct_inv=xid.update_xml_id,
            string="FIS Module",
            type='char',
            method=False,
            fnct_search=xid.search_xml_id,
            multi='external',
            ),
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
        }

    def fis_updates(self, cr, uid, *args):
        _logger.info("res_partner.fis_updates starting...")
        settings = check_company_settings(self, cr, uid,
                ('supplier_integration', 'Supplier/Vendor Module', CONFIG_ERROR),
                ('customer_integration', 'Customer Module', CONFIG_ERROR),
                )
        state_table = self.pool.get('res.country.state')
        state_recs = state_table.browse(cr, uid, state_table.search(cr, uid, [(1,'=',1)]))
        state_recs = dict([(r.name, (r.id, r.code, r.country_id.id)) for r in state_recs])
        #state_recs = dict([(r['name'], (r['id'], r['code'], r['country_id.id'])) for r in state_recs])
        country_table = self.pool.get('res.country')
        country_recs = country_table.browse(cr, uid, country_table.search(cr, uid, [(1,'=',1)]))
        country_recs_code = dict([(r['code'], r['id']) for r in country_recs])
        country_recs_name = dict([(r['name'], r['id']) for r in country_recs])

        seen_addresses = {}

        vendor_recs = self.browse(cr, uid, self.search(cr, uid, [('module','=',settings['supplier_integration'])]))
        vendor_codes = dict([(r['xml_id'], r['id']) for r in vendor_recs])
        vnms = fisData('VNMS', keymatch='10%s')
        for ven_rec in vnms:
            result = {}
            result['is_company'] = True
            result['supplier'] = True
            result['customer'] = False
            result['use_parent_address'] = False
            result['xml_id'] = key = 'v_' + ven_rec[V.code]
            result['module'] = settings['supplier_integration']
            result['name'] = BsnsCase(ven_rec[V.name])
            if not result['name']:
                _logger.critical("Vendor %s has no name -- skipping" % (key, ))
                continue
            addr1, addr2, addr3 = Sift(ven_rec[V.addr1], ven_rec[V.addr2], ven_rec[V.addr3])
            addr2, city, state, postal, country = cszk(addr2, addr3)
            addr3 = ''
            if city and not (addr2 or state or postal or country):
                addr2, city = city, addr2
            addr1 = normalize_address(addr1)
            addr2 = normalize_address(addr2)
            addr1, addr2 = Rise(AddrCase(addr1, addr2))
            city = NameCase(city)
            state, country = NameCase(state), NameCase(country)
            result['street'] = addr1
            result['street2'] = addr2
            result['city'] = city
            result['zip'] = postal
            if state:
                result['state_id'] = state_recs[state][0]
                result['country_id'] = state_recs[state][2]
            elif country:
                result['country_id'] = country_id = country_recs_name.get(country, None)
                if country_id is None:
                    _logger.critical("Vendor %s has invalid country <%r> -- skipping" % (key, country))
                    continue
            result['vn_tele'] = fix_phone(ven_rec[V.phone])
            result['vn_fax'] = fix_phone(ven_rec[V.fax])
            result['vn_telex'] = fix_phone(ven_rec[V.telex])
            if key in vendor_codes:
                id = vendor_codes[key]
                self.write(cr, uid, id, result)
            else:
                id = self.create(cr, uid, result)
            seen_addresses[addr1] = id
            contact = ven_rec[V.contact]
            if contact:
                result = {}
                result['name'] = NameCase(contact)
                result['is_company'] = False
                result['customer'] = False
                result['supplier'] = True
                result['use_parent_address'] = True
                result['parent_id'] = id
                result['xml_id'] = key = 'vc_' + key[2:]
                result['module'] = settings['supplier_integration']
                if key in vendor_codes:
                    id = vendor_codes[key]
                    self.write(cr, uid, id, result)
                else:
                    contact_id = self.create(cr, uid, result)

        _logger.info('vendors done...')

        supplier_recs = self.browse(cr, uid, self.search(cr, uid, [('module','=',settings['supplier_integration'])]))
        supplier_codes = dict([(r['xml_id'], r['id']) for r in supplier_recs])
        posm = fisData('POSM', keymatch='10%s')
        for sup_rec in posm:
            result = {}
            result['is_company'] = True
            result['supplier'] = True
            result['customer'] = False
            result['use_parent_address'] = False
            result['xml_id'] = key = 's_' + sup_rec[S.code]
            result['module'] = settings['supplier_integration']
            result['name'] = BsnsCase(sup_rec[S.name])
            if not result['name']:
                _logger.critical("Supplier %s has no name -- skipping" % (key, ))
                continue
            addr1, addr2, addr3 = Sift(sup_rec[S.addr1], sup_rec[S.addr2], sup_rec[S.addr3])
            addr2, city, state, postal, country = cszk(addr2, addr3)
            addr3 = ''
            if city and not (addr2 or state or postal or country):
                addr2, city = city, addr2
            addr1 = normalize_address(addr1)
            addr2 = normalize_address(addr2)
            addr1, addr2 = Rise(AddrCase(addr1, addr2))
            city = NameCase(city)
            state, country = NameCase(state), NameCase(country)
            result['street'] = addr1
            result['street2'] = addr2
            result['city'] = city
            result['zip'] = postal
            if state:
                try:
                    result['state_id'] = state_recs[state][0]
                except KeyError:
                    print key, state
                    raise
                result['country_id'] = state_recs[state][2]
            elif country:
                country_id = country_recs_name.get(country, None)
                if country_id is None:
                    _logger.critical("Supplier %s has invalid country <%r> -- skipping" % (key, country))
                    continue
                result['country_id'] = country_id
            result['sp_tele'] = fix_phone(sup_rec[S.phone])
            result['sp_fax'] = fix_phone(sup_rec[S.fax])
            result['sp_telex'] = fix_phone(sup_rec[S.telex])
            if addr1 in seen_addresses:
                id = seen_addresses[addr1]
                new_result = {}
                new_result['sp_telex'] = result['sp_telex']
                new_result['sp_fax'] = result['sp_fax']
                new_result['sp_tele'] = result['sp_tele']
                self.write(cr, uid, id, new_result)
            elif key in supplier_codes:
                id = supplier_codes[key]
                self.write(cr, uid, id, result)
            else:
                id = self.create(cr, uid, result)
            seen_addresses[addr1] = id

        _logger.info('suppliers done...')

        customer_recs = self.browse(cr, uid, self.search(cr, uid, [('module','=',settings['customer_integration'])]))
        customer_codes = dict([(r['xml_id'], r['id']) for r in customer_recs])
        csms = fisData('CSMS', keymatch='10%s ')
        for cus_rec in csms:
            result = {}
            result['is_company'] = True
            result['supplier'] = False
            result['customer'] = True
            result['use_parent_address'] = False
            result['xml_id'] = key = 'c_' + cus_rec[C.code]
            result['module'] = settings['customer_integration']
            result['name'] = BsnsCase(cus_rec[C.name])
            if not result['name']:
                _logger.critical("Customer %s has no name -- skipping" % (key, ))
                continue
            addr1, addr2, addr3 = Sift(cus_rec[C.addr1], cus_rec[C.addr2], cus_rec[C.addr3])
            addr2, city, state, postal, country = cszk(addr2, addr3)
            addr3 = ''
            if city and not (addr2 or state or postal or country):
                addr2, city = city, addr2
            addr1 = normalize_address(addr1)
            addr2 = normalize_address(addr2)
            addr1, addr2 = Rise(AddrCase(addr1, addr2))
            city = NameCase(city)
            state, country = NameCase(state), NameCase(country)
            result['street'] = addr1
            result['street2'] = addr2
            result['city'] = city
            result['zip'] = postal
            if state:
                try:
                    result['state_id'] = state_recs[state][0]
                    result['country_id'] = state_recs[state][2]
                except KeyError:
                    _logger.critical("Customer %s has invalid state <%r> -- skipping" % (key, state))
                    continue
            elif country:
                country_id = country_recs_name.get(country, None)
                if country_id is None:
                    _logger.critical("Customer %s has invalid country <%r> -- skipping" % (key, country))
                    continue
            result['phone'] = fix_phone(cus_rec[C.phone])
            result['fax'] = fix_phone(cus_rec[C.fax])
            result['mobile'] = fix_phone(cus_rec[C.addl_phone])
            if addr1 in seen_addresses:
                id = seen_addresses[addr1]
                new_result = {}
                new_result['customer'] = result['customer']
                new_result['phone'] = result['phone']
                new_result['fax'] = result['fax']
                new_result['mobile'] = result['mobile']
                self.write(cr, uid, id, new_result)
            elif key in customer_codes:
                id = customer_codes[key]
                self.write(cr, uid, id, result)
            else:
                id = self.create(cr, uid, result)
            seen_addresses[addr1] = id

        _logger.info('customers done...')

        _logger.info('res_partner.fis_updates done!')
        return True
res_partner()
