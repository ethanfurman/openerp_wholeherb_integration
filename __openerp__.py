{
   'name': 'Whole Herb FIS Integration',
    'version': '0.9',
    'category': 'Generic Modules',
    'description': """\
            """,
    'author': 'Emile van Sebille',
    'maintainer': 'Emile van Sebille',
    'website': 'www.openerp.com',
    'depends': [
            "base",
            "crm",
            "product",
            "fnx",
            "fnx_fs",
            "resource",
            "sample",
            ],
    #'init_xml': [
    #        'security/ir.model.access.csv',
    #    ],
    'data': [
            'res_config_view.xaml',
            'res_partner_view.xaml',
            'product_view.xaml',
            'blends_view.xaml',
            'purchasing_view.xaml',
            'sample_view.xaml',
            'sample_request_view.xaml',
            'inhouse_view.xaml',                # must go after product_view as it depends on those views
            'inhouse_sequence.xaml',
            'security/ir.model.access.csv',
        ],
    'test': [],
    'installable': True,
    'application': True,
    'active': False,
}
