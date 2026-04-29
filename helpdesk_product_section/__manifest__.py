# -*- coding: utf-8 -*-
{
    'name': 'Helpdesk Product Section',
    'version': '17.0.1.0.0',
    'category': 'Helpdesk',
    'summary': 'Adds product lines tab to helpdesk tickets',
    'depends': ['helpdesk', 'product', 'uom', 'sale_management', 'stock', 'ticket_update'],
    'data': [
        'security/ir.model.access.csv',
        'views/helpdesk_ticket_form_view.xml',
        # Uncomment the line below ONLY on the production database
        # where Studio added the x_is_order_fully_returned field.
        # 'views/helpdesk_ticket_form_view_studio.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
