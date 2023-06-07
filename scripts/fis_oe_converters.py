from __future__ import print_function

from dbf import Date, Time
from fislib.schema import F122, F33, F34, F135, F250
from openerplib import AttrDict, XidRec, Phone
from tools import Synchronize, SynchronizeAddress, XmlLink, odoo_erp, Odoo13
from VSS.address import NameCase, BsnsCase
from VSS.utils import fix_date
import re
import tools

__all__ = ['CNVZc', 'CSMS', 'CSMSS', 'NVBA', 'NVTY', 'FIS_ID', 'FIS_MODULE']

if odoo_erp is Odoo13:
    FIS_ID = 'fis_id'
    FIS_MODULE = 'fis_module'
else:
    FIS_ID = 'xml_id'
    FIS_MODULE = 'module'
tools.FIS_ID = FIS_ID
tools.FIS_MODULE = FIS_MODULE

SALEABLE_CATEGORY_XML_ID = 'product_category_1'
ALL_CATEGORY_XML_ID = 'product_category_all'
INVALID_CATEGORY_XML_ID = 'fis_invalid_product_category'

TODAY = Date.today()
ONE_YEAR_AGO = TODAY.replace(delta_year=-1)
TWO_YEARS_AGO = TODAY.replace(delta_year=-2)
BUSINESS_HOURS = Time(6) <= Time.now() < Time(23)

# For converters that treat 'quick' and 'full' differently, there are two ways to calculate changes
# in 'quick' mode after using get_changed_fis_records() to isolate the potential changes:
#
# - convert the new records into OpenERP records and retrieve the existing OpenERP
#   records for comparison
#
# - partially convert the records (in case a full conversion is too messy), then complete
#   the conversion later when it is determined the records are actually needed
#

class CNVZc(Synchronize):
    """
    product.category
    """

    TN = 122
    FN = 'CNVZc'
    F = 'F122'
    OE = 'product.category'
    IMD = 'product_category'
    RE = r"c10."
    FIS_KEY = F122.prod_category
    OE_KEY = FIS_ID
    OE_KEY_MODULE = FN
    OE_FIELDS = 'id', FIS_MODULE, FIS_ID, 'name', 'parent_id', 'active',
    FIS_SCHEMA = (
            F122.desc, F122.prod_category,
            )
    #
    ProductCategory = XmlLink

    def __init__(self, *args, **kwds):
        super(CNVZc, self).__init__(*args, **kwds)
        self.SALEABLE_CATEGORY = self.ProductCategory(SALEABLE_CATEGORY_XML_ID)
        _, self.SALEABLE_CATEGORY.id = self.ir_model_data.get_object_reference('product', SALEABLE_CATEGORY_XML_ID)
        self.ALL_CATEGORY = self.ProductCategory(ALL_CATEGORY_XML_ID)
        _, self.ALL_CATEGORY.id = self.ir_model_data.get_object_reference('product', ALL_CATEGORY_XML_ID)
        # make sure the invalid category exists
        ids = self.model.search([('name','=','Invalid/Missing FIS ID')])
        if ids:
            [invalid_cat_id] = ids
        else:
            invalid_cat_id = self.model.create({
                'name': 'Invalid/Missing FIS ID',
                'categ_id': self.ALL_CATEGORY,
                })
        self.INVALID_CATEGORY = self.ProductCategory(INVALID_CATEGORY_XML_ID)
        try:
            _, self.INVALID_CATEGORY.id = self.ir_model_data.get_object_reference('fis', INVALID_CATEGORY_XML_ID)
        except ValueError:
            self.INVALID_CATEGORY.id = self.ir_model_data.create({
                    'module': 'fis',
                    'name': INVALID_CATEGORY_XML_ID,
                    'model': 'product.category',
                    'res_id': invalid_cat_id,
                    })

    def convert_fis_rec(self, fis_rec, use_ignore=False):
        if use_ignore and self.fis_ignore_record(fis_rec):
            return ()
        key = fis_rec[F122.prod_category].strip()
        imd = AttrDict(
                id=0,
                model=self.OE,
                res_id=0,
                module='fis',
                name=self.calc_xid(key),
                )
        category = AttrDict.fromkeys(self.OE_FIELDS, None)
        category.active = True
        category[FIS_ID] = key
        category[FIS_MODULE] = self.OE_KEY_MODULE
        category.parent_id = self.SALEABLE_CATEGORY
        name = fis_rec[F122.desc].title()
        category.name = name or None
        return (XidRec.fromdict(category, imd), )


class CSMS(SynchronizeAddress):
    """
    customers, 33  (CNVZ_Z_K, CNVZd0)
    """
    TN = 33
    FN = 'CSMS'
    F = 'F033'
    RE = r"10...... "
    OE = 'res.partner'
    IMD = 'res_partner'
    FIS_KEY = F33.cust_id
    OE_KEY = FIS_ID
    OE_KEY_MODULE = FN
    OE_FIELDS = (
            'id', FIS_MODULE, FIS_ID, 'email', 'fis_record',
            'name', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id',
            'phone', 'is_company', 'customer', 'active', 'use_parent_address',
            )
    FIS_SCHEMA = (
            F33.name, F33.tele, F33.contact, F33.date_opened,
            F33.ytd_sales, F33.prev_year_sales,
            )
    FIELDS_CHECK_IGNORE = ('active', 'name')

    Partner = XmlLink

    def __init__(self, oe, config, *args, **kwds):
        super(CSMS, self).__init__(oe, config, *args, **kwds)
        import requests
        result = set()
        if config.network.active_customer_url:
            try:
                web_data = requests.get(config.network.active_customer_url)
            except requests.exceptions.ConnectionError:
                pass
            else:
                companies = re.findall(r'<th.*?>(.*?)</th>', web_data.text)
                for line in companies:
                    fis_id = line.split()[0]
                    if fis_id.isdigit():
                        result.add(fis_id)
        self.active_salesinq = result

    def convert_fis_rec(self, fis_rec, use_ignore=False):
        #
        # creates an AttrDict with the following fields
        # - '(fis_)module', '(fis|xml)_id',
        # - 'name', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id',
        # - 'phone', 'is_company', 'customer',
        # - 'use_parent_address', 'active',
        #
        # fields coming from OpenERP that are missing/invalid on the FIS side
        # - 'id',
        # - address fields (for contact)
        #
        # fis records use the following fields to detect changes
        #
        # enum_schema=[
        #     F33.name, F33.catalog_category, F33.this_year_sales,
        #     F33.last_year_sales, F33.tele, F33.contact,
        #     ],
        # address_fields=[
        #     F33.addr1, F33.addr2, F33.addr3,
        #     ],
        #
        if use_ignore and self.fis_ignore_record(fis_rec):
            return ()
        key = fis_rec[F33.cust_id]
        imd = AttrDict(
                id=0,
                model=self.OE,
                res_id=0,
                module='fis',
                name=self.calc_xid(key),
                )
        names, address, do_not_use = self.process_name_address(F33, fis_rec)
        pname = names and names[0] or ''
        pname = BsnsCase(pname) or ''
        names[0:1] = [pname]
        name = ', '.join(names)
        dnu = ', '.join(do_not_use)
        name = ' / '.join([l for l in (name, dnu) if l])
        if not name:
            return ()
        company = AttrDict.fromkeys(self.OE_FIELDS, None)
        company.name = name
        company.update(address)
        company[FIS_MODULE] = self.OE_KEY_MODULE
        company[FIS_ID] = key
        company.is_company = True
        company.customer = True
        company.use_parent_address = False
        # valid customer code? active account?
        company.active = not bool(do_not_use)
        added = fix_date(fis_rec[F33.date_opened]) or Date()
        if (
                key in self.active_salesinq
             or fis_rec[F33.ytd_sales]
             or fis_rec[F33.prev_year_sales]
             or added >= TWO_YEARS_AGO
            ):
            company.active = True
        else:
            # TODO check for open orders
            pass
        company.phone = Phone(fis_rec[F33.tele])
        company = XidRec.fromdict(company, imd)
        assert set(company._keys) == set(company._values.keys())
        contact = None
        if fis_rec[F33.contact] and fis_rec[F33.contact] != fis_rec[F33.name]:
            key = 'cntct_' + key
            imd = AttrDict(
                    id=0,
                    model=self.OE,
                    res_id=0,
                    module='fis',
                    name='F033_%s_res_partner' % (key),
                    )
            contact = AttrDict.fromkeys(self.OE_FIELDS, None)
            name = fis_rec[F33.contact]
            # is it only an email?
            names = name.split()
            email = ''
            if len(names) == 1 and '@' in names:
                name = name.lower()
            else:
                if '@' in names[-1]:
                    email = names.pop().lower()
                name = NameCase(' '.join(names[:-1]))
            contact.name = name
            contact.email = email
            contact[FIS_MODULE] = 'F33'
            contact[FIS_ID] = key
            contact.is_company = False
            contact.customer = True
            contact.use_parent_address = False
            contact.street = company.street
            contact.street2 = company.street2
            contact.city = company.city
            contact.state_id = company.state_id
            contact.zip = company.zip
            contact.country_id = company.country_id
            contact.active = company.active
            contact = XidRec.fromdict(contact, imd)
            assert set(contact._keys) == set(contact._values.keys())
            return company, contact
        return (company, )


    def keep_oe_only_record(self, oe_rec):
        return not oe_rec.fis_record

class CSMSS(SynchronizeAddress):
    """
    ship-to addresses, 34  (CSMS)

    key field is the customer number plus a ship-to designation
    key field only has a ship-to if one is in FIS
    """
    TN = 34
    FN = 'CSMSS'
    F = 'F034'
    RE = r"10......1...."
    OE = 'res.partner'
    IMD = 'res_partner'
    FIS_KEY = F34.cust_no
    OE_KEY = FIS_ID
    OE_KEY_MODULE = FN
    OE_FIELDS = (
            'id', FIS_MODULE, FIS_ID, 'phone',
            'name', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id',
            'customer', 'fis_ship_to_parent_id', 'use_parent_address', 'is_company',
            'active',
            )
    FIS_SCHEMA = (
            F34.name, F34.addr1, F34.addr2, F34.addr3,
            F34.tele,
            )

    ShipTo = XmlLink

    def fis_ignore_record(self, rec):
        if super(CSMSS, self).fis_ignore_record(rec):
            return True
        elif (
                not rec[F34.name]
                or re.search('email', rec[F34.name], re.I)
                or re.search('email', rec[F34.addr1], re.I)
                or re.search('email', rec[F34.addr2], re.I)
                or re.search('email', rec[F34.addr3], re.I)
            ):
            return True
        else:
            return False

    def convert_fis_rec(self, fis_rec, use_ignore=False):
        "additional ship-to addresses"
        #
        # creates an XidRec with the following fields
        # - '(fis_)module', '(fis|xml)_id', 'active',
        # - 'name', 'street', 'street2', 'city', 'state_id', 'zip', 'country_id',
        # - 'phone', 'is_company', 'customer','use_parent_address',
        # - 'fis_ship_to_code', 'fis_ship_to_parent_id', 'fis_transmitter_id',
        #
        # fields coming from OpenERP that are missing/invalid on the FIS side
        # - 'id',
        #
        # fis records use the following fields to detect changes
        #
        # enum_schema=[
        #     F34.name, F34.addr1, F34.addr2, F34.addr3, F34.postal, F34.tele, F34.sales_contact,
        #     ],
        # address_fields=[
        #     F34.addr1, F34.addr2, F34.addr3,
        #     ],
        #
        if use_ignore and self.fis_ignore_record(fis_rec):
            return ()
        parent_xml_id = fis_rec[F34.cust_no]
        names, address, do_not_use = self.process_name_address(F34, fis_rec)
        ship_to_code = fis_rec[F34.ship_to_no].strip() or 'dflt'
        key = ('%s-%s' % (parent_xml_id, ship_to_code)).strip('-')
        pname = names and names[0] or ''
        pname = BsnsCase(pname) or ''
        names[0:1] = [pname]
        name = ', '.join(names)
        dnu = ', '.join(do_not_use)
        name = ' / '.join([l for l in (name, dnu) if l])
        imd = AttrDict(
                id=0,
                model=self.OE,
                res_id=0,
                module='fis',
                name=self.calc_xid(key),
                )
        ship_to = AttrDict.fromkeys(self.OE_FIELDS, None)
        ship_to.name = name
        ship_to.update(address)
        ship_to[FIS_MODULE] = self.OE_KEY_MODULE
        ship_to[FIS_ID] = key
        ship_to.active = True
        ship_to.is_company = False
        ship_to.customer = False
        ship_to.use_parent_address = False
        ship_to.phone = Phone(fis_rec[F34.tele])
        ship_to.fis_ship_to_parent_id = CSMS.Partner(parent_xml_id)
        return (XidRec.fromdict(ship_to, imd), )


class NVBA(Synchronize):
    """
    product.lot
    """

    TN = 250
    FN = 'NVBA'
    F = 'F250'
    OE = (
            'wholeherb_integration.product_lot',
            'fis.product_lot',
            )[odoo_erp]
    IMD = 'product_lot'
    RE = r"10............0SON........"
    FIS_KEY = F250.lot_no
    OE_KEY = 'lot_no'
    OE_KEY_MODULE = FN
    OE_FIELDS = 'id', 'product_id', 'lot_no', 'active', 'preship_lot', 'fis_record',
    FIS_SCHEMA = (
            F250.lot_no, F250.item_id, F250.warehouse_id,
            )
    #
    invalid_lot = re.compile('^new|po', re.I)
    potential_lot = re.compile(r'^[a-z]+\d{4,6}[a-z]*$', re.IGNORECASE)
    #
    ProductCategory = XmlLink

    def oe_ignore_record(self, oe_rec):
        if super(NVBA, self).oe_ignore_record(oe_rec):
            return True
        if oe_rec.preship_lot:
            return True
        if not self.valid_lot.match(oe_rec[self.OE_KEY]):
            return True
        return False

    def fis_ignore_record(self, fis_rec):
        if super(NVBA, self).fis_ignore_record(fis_rec):
            return True
        if fis_rec[F250.warehouse_id] != '0SON':
            return True
        if self.invalid_lot.match(fis_rec[F250.lot_no]):
            return True
        if not self.valid_lot.match(fis_rec[F250.lot_no]):
            return True
        return False

    def __init__(self, *args, **kwds):
        super(NVBA, self).__init__(*args, **kwds)
        valid_lot_regex = (
                self.get_records(
                    self.erp,
                    'res.users',
                    domain=[('login','=',self.erp.login)],
                    fields=['company_id'],
                    )[0]
                .company_id.get_record(
                    self.erp,
                    fields=['valid_lot_regex'],
                    )
                .valid_lot_regex
                )
        self.valid_lot = re.compile(valid_lot_regex)

    def convert_fis_rec(self, fis_rec, use_ignore=False):
        if use_ignore and self.fis_ignore_record(fis_rec):
            return ()
        key = fis_rec[F250.lot_no].strip()
        imd = AttrDict(
                id=0,
                model=self.OE,
                res_id=0,
                module='fis',
                name=self.calc_xid(key),
                )
        product_lot = AttrDict.fromkeys(self.OE_FIELDS, None)
        product_lot.lot_no = key
        product_lot.product_id = NVTY.Product(fis_rec[F250.item_id])
        product_lot.active = True
        product_lot.preship_lot = False
        return (XidRec.fromdict(product_lot, imd), )


    def keep_oe_only_record(self, oe_rec):
        return not oe_rec.fis_record

class NVTY(Synchronize):
    """
    products, 135  (CNVZc)
    """
    TN = 135
    FN = 'NVTY'
    F = 'F135'
    RE = r'10................1\*\*'
    OE = 'product.product'
    IMD = 'product_product'
    FIS_KEY = F135.item_id
    OE_KEY = FIS_ID
    OE_KEY_MODULE = FN
    OE_FIELDS = (
            'id', FIS_MODULE, FIS_ID, 'name', 'categ_id', 'active', 'fis_record', 'default_code',
            )
    FIS_SCHEMA = (
            F135.item_id, F135.desc, F135.selling_units, F135.available,
            F135.prod_category, F135.warehouse_no,
            )
    FIELDS_CHECK_IGNORE = ('name', )
    #
    Product = XmlLink

    def __init__(self, oe, config, *args, **kwds):
        super(NVTY, self).__init__(oe, config, *args, **kwds)
        CNVZc(oe, config).reify()

    def fis_ignore_record(self, rec):
        if super(NVTY, self).fis_ignore_record(rec):
            return True
        elif rec[F135.warehouse_no] != '0SON':
            return True
        else:
            return False

    def convert_fis_rec(self, fis_rec, use_ignore=False):
        # some fields come from non-FIS locations or are only updated once per
        # day -- those fields will not be evaluated here:
        # - name -> get_product_descriptions()
        # - fis_qty: _produced, _consumed, _purchased, _sold, _available
        # - fis_10_day: _produced, _consumed, _purchased, _sold, _available
        # - fis_21_day: _produced, _cosnumed, _purchased, _sold, _available
        if use_ignore and self.fis_ignore_record(fis_rec):
            return ()
        key = fis_rec[F135.item_id]
        imd = AttrDict(
                id=0,
                model=self.OE,
                res_id=0,
                module='fis',
                name=self.calc_xid(key),
                )
        item = AttrDict.fromkeys(self.OE_FIELDS, None)
        item[FIS_MODULE] = self.OE_KEY_MODULE
        item[FIS_ID] = key
        item.default_code = key
        item.name = NameCase(' - '.join(fis_rec[F135.desc].split('\x10'))) or None
        item.active = True
        item.categ_id = (
                CNVZc.ProductCategory(fis_rec[F135.prod_category])
             or CNVZc.ProductCategory(INVALID_CATEGORY_XML_ID)
                )
        item.fis_record = True
        #
        return (XidRec.fromdict(item, imd), )

    def keep_oe_only_record(self, oe_rec):
        return not oe_rec.fis_record

    def normalize_records(self, fis_rec, oe_rec):
        super(NVTY, self).normalize_records(fis_rec, oe_rec)
        if fis_rec.name is None:
            fis_rec.name = oe_rec.name or '-- missing --'


def is_contact(obj):
    "obj must be either a string or have an xml_id key"
    if not isinstance(obj, basestring):
        obj = obj.get(FIS_ID)
    return obj.startswith('cntct_')

def numeric(number):
    if isinstance(number, (int, long, float)):
        return number
    try:
        return int(number)
    except ValueError:
        try:
            return float(number)
        except ValueError:
            pass
    return False

def get_updated_values(old_record, new_record):
    changes = AttrDict()
    for key in old_record:
        old_value = old_record[key]
        new_value = new_record[key]
        if (old_value or new_value) and old_value != new_value:
            changes[key] = new_value
    return changes

