from antipathy import Path as _Path
from xaml import Xaml as _Xaml

# report_name = (_Path(__file__).dirname or _Path('.'))/'product-traffic.xaml'
base_dir = (_Path(__file__).dirname or _Path('.'))

for report in ('product-traffic.xaml', 'inhouse-costing.xaml', 'inhouse-job_time.xaml', 'inhouse-work_order.xaml'):
    report_name = base_dir / report
    if not report_name.exists():
        print('skipping', report_name)
        continue
    with open(report_name) as src:
        xaml_doc = _Xaml(src.read()).document
    #
    if len(xaml_doc.pages) != 2:
        raise ValueError('%s should have an xml and an xsl component' % report_name)
    #
    for page in xaml_doc.pages:
        with open(report_name.strip_ext() + '.' + page.ml.type, 'wb') as dst:
            dst.write(page.bytes())
