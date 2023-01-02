"various OpenERP routines related to exposing fis ids stored in xml_id in ir.model.data"

from openerp.exceptions import ERPError
import logging

_logger = logging.getLogger(__name__)

class xmlid(object):

    def create(self, cr, uid, values, context=None):
        context = context or {}
        xml_id = values.get('xml_id')
        module = values.get('module')
        if xml_id and not module:
            # some FIS records can be created first in OpenERP, so assign
            # the correct module
            if self._name == 'product.product':
                values['module'] = module = 'NVTY'
            elif self._name == 'wholeherb_integration.product_lot':
                values['module'] = module = 'NVBA'
            elif self._name == 'product.category':
                values['module'] = module = 'CNVZc'
        new_id = super(xmlid, self).create(cr, uid, values, context=context)
        if xml_id and module and not context.get('fis_maintenance', False):
            imd = self.pool.get('ir.model.data')
            imd_name = '%s_%s_%s' % (module, xml_id, self._table)
            # check for orphaned xml_ids
            orphan = imd.search(cr, uid, [('module','=','whc'),('name','=ilike',imd_name)], context=context)
            if orphan:
                # this shouldn't happen - log a warning
                _logger.warning('FIS ID orphan found: <%s::%s>', module, xml_id)
                # actually an orphan?
                found = imd.browse(cr, uid, orphan[0], context=context)
                record = self.browse(cr, uid, found.res_id, context=context)
                if record:
                    # not an orphan, and duplicates not allowed!
                    _logger.warning('orphan id: %r' % (record.id, ))
                    raise ERPError('Error', '%s:%s belongs to [%s] %s' % (module, xml_id, record.id, record[self._rec_name]))
                else:
                    # adopt the orphan
                    imd.write(cr, uid, orphan[0], {'res_id':new_id}, context=context)
            else:
                imd.create(cr, uid, {'module':'whc', 'name':imd_name, 'model':self._name, 'res_id':new_id}, context=context)
        return new_id

    def name_search(self, cr, uid, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name:
            if name[0] == ' ':
                ids = self.search(cr, uid, [('xml_id','ilike',name.lstrip())]+ args, limit=limit, context=context)
            else:
                ids = self.search(cr, uid, [('xml_id','=ilike',name+'%')]+ args, limit=limit, context=context)
            if ids:
                return self.name_get(cr, uid, ids, context=context)
        return super(xmlid, self).name_search(cr, uid, name=name, args=args, operator=operator, context=context, limit=limit)

    def write(self, cr, uid, ids, values, context=None):
        context = context or {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        xml_id = values.get('xml_id')
        module = values.get('module')
        if xml_id and not module:
            # some FIS records can be created first in OpenERP, so assign
            # the correct module
            if self._name == 'product.product':
                values['module'] = module = 'NVTY'
            elif self._name == 'wholeherb_integration.product_lot':
                values['module'] = module = 'NVBA'
        if xml_id and len(ids) > 1:
            raise ERPError('Error', 'FIS IDs must be unique')
        res = True
        if not (xml_id or module) or context.get('fis_maintenance', False):
            return super(xmlid, self).write(cr, uid, ids, values, context=context)
        for rec in self.browse(cr, uid, ids, context=context):
            res = super(xmlid, self).write(cr, uid, rec.id, values, context=context)
            if not xml_id:
                values['xml_id'] = xml_id = rec.xml_id
            if not module:
                values['module'] = module = rec.module
            # create new imd name
            if xml_id and module:
                imd_name = '%s_%s_%s' % (module, xml_id, self._table)
            else:
                imd_name = None
            # get any existing imd record
            imd = self.pool.get('ir.model.data')
            try:
                for record in imd.browse(cr, uid, [('model','=',self._name),('res_id','=',rec.id)]):
                    if imd_name and record.module in ('fis','whc'):
                        imd.write(cr, uid, record.id, {'name':imd_name}, context=context)
                    else:
                        imd.unlink(cr, uid, record.id, context=context)
            except ValueError:
                if imd_name:
                    imd.create(cr, uid, {'module':'whc', 'name':imd_name, 'model':self._name, 'res_id':rec.id, }, context=context)
            return res

    def get_xml_id_map(self, cr, uid, module, ids=None, context=None):
        "return {xml_id: id} for all xml_ids in module"
        imd = self.pool.get('ir.model.data')
        model = self._table
        result = {}
        for rec in imd.read(cr, uid, [('module','=','whc'),('name','=ilike','%s_%%_%s' % (module, model))], fields=['name','res_id'], context=context):
            if ids is None or rec.res_id in ids:
                name = rec['name'][len(module):-len(model)][1:-1]
                result[name] = rec['res_id']
        return result

    def unlink(self, cr, uid, ids, context=None):
        context = context or {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = super(xmlid, self).unlink(cr, uid, ids, context=context)
        # delete any matching ir.model.data records
        imd = self.pool.get('ir.model.data')
        imd_ids = imd.search(cr, uid, [('model','=',self._name), ('res_id','in', ids)])
        if imd_ids:
            res = imd.unlink(cr, uid, imd_ids, context=context)
        return res

